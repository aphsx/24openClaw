import asyncio
import uuid
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from .exchange import BinanceClient
from .models import DBManager


class TradeExecutor:
    """
    Full atomic trade executor with:
    - 5-layer dedup guard
    - Atomic two-leg execution with rollback
    - Post-close verification (retry x3)
    - Grace period persistence
    - Full DB persistence
    """

    def __init__(self, exchange: BinanceClient):
        self.exchange = exchange
        self.db = DBManager()

    # ─────────────────────────────────────────────────────
    # Open
    # ─────────────────────────────────────────────────────

    async def open_pair(self, signal: dict) -> dict:
        sym_a = signal['symbol_a']
        sym_b = signal['symbol_b']
        z     = float(signal.get('zscore', 0))
        beta  = float(signal.get('hedge_ratio', 1.0))
        corr  = float(signal.get('correlation', 0))
        hl    = float(signal.get('half_life', 0) or 0)
        zone  = signal.get('zone', 'safe')
        size_pct = float(signal.get('validation_json', {}).get('sizePct', 1.0))

        # ── Dedup Layer 1: validate inputs ──
        if not sym_a or not sym_b or sym_a == sym_b:
            return self._fail("invalid_symbols")
        if beta <= 0 or math.isnan(beta) or math.isinf(beta):
            return self._fail("invalid_beta")
        if z is None or math.isnan(z):
            return self._fail("invalid_zscore")

        config = await self.db.get_all_config()
        zscore_entry = float(config.get('zscore_entry', 2.0))
        cooldown_sec = float(config.get('cooldown_sec', 3600))
        max_same_coin = int(config.get('max_same_coin', 2))
        max_open_pairs = int(config.get('max_open_pairs', 5))
        base_size = float(config.get('position_size_usd', 500))
        grace_sec = float(config.get('grace_period_sec', 300))

        if abs(z) < zscore_entry:
            return self._fail("zscore_below_entry")

        # ── Dedup Layer 2: DB open check ──
        if await self.db.is_pair_open(sym_a, sym_b):
            return self._fail("pair_already_open")

        # ── Dedup Layer 3: Exchange position check ──
        pos_a = await self.exchange.get_position(sym_a)
        pos_b = await self.exchange.get_position(sym_b)
        if pos_a or pos_b:
            return self._fail("exchange_position_exists")

        # ── Dedup Layer 4: Cooldown ──
        if await self.db.is_in_cooldown(sym_a, sym_b, cooldown_sec):
            return self._fail("in_cooldown")

        # ── Dedup Layer 5: Concentration limit ──
        if await self.db.get_coin_open_count(sym_a) >= max_same_coin:
            return self._fail(f"concentration_limit_{sym_a}")
        if await self.db.get_coin_open_count(sym_b) >= max_same_coin:
            return self._fail(f"concentration_limit_{sym_b}")

        # Check total open pairs limit
        open_trades = await self.db.get_open_trades()
        if len(open_trades) >= max_open_pairs:
            return self._fail("max_open_pairs_reached")

        # ── Sizing ──
        size_a = base_size * size_pct
        size_b = base_size * beta * size_pct

        # Direction: z > 0 → A expensive → SHORT A, LONG B
        if z > 0:
            side_a, side_b = 'sell', 'buy'
        else:
            side_a, side_b = 'buy', 'sell'

        group_id = str(uuid.uuid4())
        print(f"[Executor] Opening {sym_a}({side_a}/${size_a:.0f}) / {sym_b}({side_b}/${size_b:.0f}) | Z={z:.3f} β={beta:.3f}")

        # ── Atomic Execution: Leg A ──
        try:
            order_a = await self.exchange.place_order(sym_a, side_a, size_a)
        except Exception as e:
            return self._fail(f"leg_a_failed: {e}")

        # ── Atomic Execution: Leg B ──
        try:
            order_b = await self.exchange.place_order(sym_b, side_b, size_b)
        except Exception as e:
            print(f"[Executor] Leg B failed: {e}. Rolling back Leg A...")
            await self._rollback_leg(sym_a, side_a, size_a)
            return self._fail(f"leg_b_failed_rollback: {e}")

        # ── DB Persistence (immediately after both legs confirm) ──
        price_a = float(order_a.get('average') or order_a.get('price') or 0)
        price_b = float(order_b.get('average') or order_b.get('price') or 0)
        grace_until = datetime.now(timezone.utc) + timedelta(seconds=grace_sec)

        await self.db.open_trade({
            'group_id':          group_id,
            'symbol_a':          sym_a,
            'symbol_b':          sym_b,
            'leg_a_side':        side_a,
            'leg_a_size_usd':    size_a,
            'leg_a_order_id':    str(order_a.get('id', '')),
            'leg_a_entry_price': price_a if price_a > 0 else None,
            'leg_b_side':        side_b,
            'leg_b_size_usd':    size_b,
            'leg_b_order_id':    str(order_b.get('id', '')),
            'leg_b_entry_price': price_b if price_b > 0 else None,
            'entry_zscore':      z,
            'entry_corr':        corr,
            'entry_beta':        beta,
            'entry_half_life':   hl if hl > 0 else None,
            'entry_zone':        zone,
            'validation_json':   signal.get('validation_json', {}),
            'grace_until':       grace_until,
        })

        print(f"[Executor] Pair opened. GroupID={group_id}")
        return {'success': True, 'groupId': group_id, 'side_a': side_a, 'side_b': side_b}

    # ─────────────────────────────────────────────────────
    # Close
    # ─────────────────────────────────────────────────────

    async def close_pair(self, group_id: str, exit_reason: str = 'manual') -> dict:
        trade = await self.db.get_trade_by_group(group_id)
        if not trade:
            return self._fail("trade_not_found")
        if trade['status'] != 'open':
            return self._fail("trade_not_open")

        sym_a   = trade['symbol_a']
        sym_b   = trade['symbol_b']
        side_a  = trade['leg_a_side']
        side_b  = trade['leg_b_side']

        print(f"[Executor] Closing {sym_a}/{sym_b} | reason={exit_reason}")

        # Close both legs
        err_a = err_b = None
        try:
            await self.exchange.close_position(sym_a, side_a)
        except Exception as e:
            err_a = str(e)
            print(f"[Executor] Close Leg A error: {e}")

        try:
            await self.exchange.close_position(sym_b, side_b)
        except Exception as e:
            err_b = str(e)
            print(f"[Executor] Close Leg B error: {e}")

        # Post-close verification: retry up to 3 times
        for attempt in range(3):
            await asyncio.sleep(2)
            still_a = await self.exchange.get_position(sym_a)
            still_b = await self.exchange.get_position(sym_b)
            if not still_a and not still_b:
                break
            print(f"[Executor] Post-close verify attempt {attempt+1}: positions still open, retrying...")
            if still_a:
                try:
                    await self.exchange.close_position(sym_a, side_a)
                except Exception:
                    pass
            if still_b:
                try:
                    await self.exchange.close_position(sym_b, side_b)
                except Exception:
                    pass
        else:
            print(f"[Executor] WARNING: Could not fully close {sym_a}/{sym_b} after 3 attempts. Manual intervention may be required.")

        # Calculate PnL
        pnl = await self._compute_pnl(trade)

        # Get current z-score from pairs table
        pair_stats = await self.db.get_pair_stats(sym_a, sym_b)
        exit_z = float(pair_stats['zscore']) if pair_stats and pair_stats.get('zscore') else 0.0

        await self.db.close_trade(group_id, exit_z, exit_reason, pnl)
        print(f"[Executor] Closed {sym_a}/{sym_b}. PnL=${pnl:.2f} Z_exit={exit_z:.3f}")
        return {'success': True, 'groupId': group_id, 'pnl': pnl, 'reason': exit_reason}

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    async def _rollback_leg(self, symbol: str, open_side: str, size_usd: float):
        """Try to close a single leg that was opened. Retry 3 times."""
        for attempt in range(3):
            try:
                await self.exchange.close_position(symbol, open_side)
                # Verify
                await asyncio.sleep(1)
                pos = await self.exchange.get_position(symbol)
                if not pos:
                    print(f"[Executor] Rollback {symbol} succeeded on attempt {attempt+1}")
                    return
            except Exception as e:
                print(f"[Executor] Rollback {symbol} attempt {attempt+1} failed: {e}")
            await asyncio.sleep(1)
        print(f"[Executor] CRITICAL: Rollback {symbol} failed after 3 attempts. Manual intervention required!")

    async def _compute_pnl(self, trade: dict) -> float:
        """Compute estimated PnL from entry/exit prices."""
        try:
            price_a_exit = await self.exchange.get_mark_price(trade['symbol_a']) or 0
            price_b_exit = await self.exchange.get_mark_price(trade['symbol_b']) or 0
            entry_a = float(trade.get('leg_a_entry_price') or 0)
            entry_b = float(trade.get('leg_b_entry_price') or 0)
            size_a  = float(trade.get('leg_a_size_usd') or 0)
            size_b  = float(trade.get('leg_b_size_usd') or 0)

            if not all([price_a_exit, price_b_exit, entry_a, entry_b]):
                return 0.0

            if trade['leg_a_side'] == 'sell':  # Short A
                pnl_a = (entry_a - price_a_exit) / entry_a * size_a
            else:                              # Long A
                pnl_a = (price_a_exit - entry_a) / entry_a * size_a

            if trade['leg_b_side'] == 'buy':   # Long B
                pnl_b = (price_b_exit - entry_b) / entry_b * size_b
            else:                              # Short B
                pnl_b = (entry_b - price_b_exit) / entry_b * size_b

            fee_est = (size_a + size_b) * 2 * 0.0004  # 0.04% per side x 4 orders
            return round(pnl_a + pnl_b - fee_est, 4)
        except Exception:
            return 0.0

    @staticmethod
    def _fail(reason: str) -> dict:
        print(f"[Executor] Blocked: {reason}")
        return {'success': False, 'reason': reason}
