import asyncio
import math
from datetime import datetime, timezone

from .exchange import BinanceClient
from .models import DBManager
from .stats import compute_pair_stats


class PositionMonitor:
    """
    Monitors all open positions every N seconds and enforces:
      SL1: Z-Score Stop     - |z| >= zscore_sl (after grace period)
      SL2: Time Stop        - held > 2 * half_life days
      SL3: Correlation Break- current corr < corr_break_sl (default 0.50)
      SL4: Max Loss Stop    - unrealized loss > max_loss_pct% of allocated (active in grace too)
    Also monitors:
      - Funding rate > funding_rate_max -> emergency exit
      - Beta drift > beta_drift_max_pct% -> warning log
    """

    def __init__(self, exchange: BinanceClient, executor):
        self.exchange = exchange
        self.executor = executor
        self.db = DBManager()

    async def run_once(self):
        open_trades = await self.db.get_open_trades()
        if not open_trades:
            return

        config = await self.db.get_all_config()
        zscore_sl       = float(config.get('zscore_sl',          3.0))
        corr_break_sl   = float(config.get('corr_break_sl',      0.50))
        max_loss_pct    = float(config.get('max_loss_pct',        5.0))
        funding_max     = float(config.get('funding_rate_max',    0.001))
        beta_drift_max  = float(config.get('beta_drift_max_pct', 20.0))

        now = datetime.now(timezone.utc)

        for trade in open_trades:
            group_id = str(trade['group_id'])
            sym_a    = trade['symbol_a']
            sym_b    = trade['symbol_b']
            entry_hl = float(trade.get('entry_half_life') or 0)
            entry_beta = float(trade.get('entry_beta') or 0)
            opened_at = trade['opened_at']
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)

            grace_until = trade.get('grace_until')
            in_grace = grace_until is not None and (
                grace_until if grace_until.tzinfo else grace_until.replace(tzinfo=timezone.utc)
            ) > now

            # ── Get latest pair stats ──
            pair = await self.db.get_pair_stats(sym_a, sym_b)
            if not pair:
                continue

            current_z    = float(pair.get('zscore') or 0)
            current_corr = float(pair.get('correlation') or 1.0)
            current_beta = float(pair.get('hedge_ratio') or entry_beta)

            # Update current z in DB
            await self.db.update_trade_zscore(group_id, current_z)

            # ── SL4: Max Loss (works even in grace period) ──
            pnl = await self._estimate_pnl(trade)
            size_a = float(trade.get('leg_a_size_usd') or 0)
            size_b = float(trade.get('leg_b_size_usd') or 0)
            allocated = size_a + size_b
            if allocated > 0:
                loss_pct = (-pnl / allocated * 100) if pnl < 0 else 0
                if loss_pct >= max_loss_pct:
                    print(f"[Monitor] SL4 Max Loss on {sym_a}/{sym_b}: -{loss_pct:.1f}% >= {max_loss_pct}%")
                    await self.executor.close_pair(group_id, 'sl_max_loss')
                    continue

            # ── Funding rate check (both legs) ──
            fr_a = await self.exchange.get_funding_rate(sym_a)
            fr_b = await self.exchange.get_funding_rate(sym_b)
            if max(fr_a, fr_b) > funding_max:
                print(f"[Monitor] Funding rate emergency exit {sym_a}/{sym_b}: fr_a={fr_a:.4f} fr_b={fr_b:.4f}")
                await self.executor.close_pair(group_id, 'funding_rate_too_high')
                continue

            # ── Checks that respect grace period ──
            if not in_grace:
                # SL1: Z-Score Stop
                if abs(current_z) >= zscore_sl:
                    print(f"[Monitor] SL1 Z-Stop {sym_a}/{sym_b}: |z|={abs(current_z):.3f} >= {zscore_sl}")
                    await self.executor.close_pair(group_id, 'sl_zscore')
                    continue

                # SL2: Time Stop
                if entry_hl > 0:
                    max_hold_days = 2.0 * entry_hl
                    held_days = (now - opened_at).total_seconds() / 86400
                    if held_days >= max_hold_days:
                        print(f"[Monitor] SL2 Time Stop {sym_a}/{sym_b}: held={held_days:.1f}d >= {max_hold_days:.1f}d")
                        await self.executor.close_pair(group_id, 'sl_time_stop')
                        continue

                # SL3: Correlation Break
                if current_corr < corr_break_sl:
                    print(f"[Monitor] SL3 Corr Break {sym_a}/{sym_b}: corr={current_corr:.3f} < {corr_break_sl}")
                    await self.executor.close_pair(group_id, 'sl_corr_break')
                    continue

            else:
                remaining = (grace_until.replace(tzinfo=timezone.utc) if grace_until.tzinfo is None else grace_until) - now
                print(f"[Monitor] {sym_a}/{sym_b} in grace period ({remaining.seconds}s remaining), skipping SL1-3")

            # ── Take Profit ──
            tp_threshold = float(config.get('zscore_tp', 0.5))
            if abs(current_z) <= tp_threshold:
                print(f"[Monitor] TP {sym_a}/{sym_b}: z={current_z:.3f} reached {tp_threshold}")
                await self.executor.close_pair(group_id, 'take_profit')
                continue

            # ── Beta drift warning ──
            if entry_beta > 0 and current_beta > 0:
                drift_pct = abs(current_beta - entry_beta) / entry_beta * 100
                if drift_pct > beta_drift_max:
                    print(f"[Monitor] WARNING beta drift {sym_a}/{sym_b}: entry={entry_beta:.3f} current={current_beta:.3f} drift={drift_pct:.1f}%")

    async def _estimate_pnl(self, trade: dict) -> float:
        try:
            price_a = await self.exchange.get_mark_price(trade['symbol_a']) or 0
            price_b = await self.exchange.get_mark_price(trade['symbol_b']) or 0
            entry_a = float(trade.get('leg_a_entry_price') or 0)
            entry_b = float(trade.get('leg_b_entry_price') or 0)
            size_a  = float(trade.get('leg_a_size_usd') or 0)
            size_b  = float(trade.get('leg_b_size_usd') or 0)

            if not all([price_a, price_b, entry_a, entry_b]):
                return 0.0

            if trade['leg_a_side'] == 'sell':
                pnl_a = (entry_a - price_a) / entry_a * size_a
            else:
                pnl_a = (price_a - entry_a) / entry_a * size_a

            if trade['leg_b_side'] == 'buy':
                pnl_b = (price_b - entry_b) / entry_b * size_b
            else:
                pnl_b = (entry_b - price_b) / entry_b * size_b

            return pnl_a + pnl_b
        except Exception:
            return 0.0
