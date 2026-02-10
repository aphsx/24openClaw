"""
ClawBot AI — Position Tracker
Tracks open positions and detects SL/TP triggers between cycles.
"""
from typing import Any, Dict, List, Optional

from src.data.binance_rest import BinanceREST
from src.utils.config import settings
from src.utils.logger import log


class PositionTracker:
    """
    Tracks open positions and detects changes between cycles.
    - Stores last known positions
    - Detects SL/TP triggered between cycles
    - Provides position data for AI input
    """

    def __init__(self, client: BinanceREST):
        self.client = client
        self._last_positions: Dict[str, dict] = {}  # {symbol: position_data}
        self._last_order_ids: Dict[str, List[int]] = {}  # {symbol: [order_ids]}

    async def update(self) -> tuple:
        """
        Fetch current positions and detect changes.
        Returns: (current_positions, closed_between_cycles)
        """
        current_raw = await self.client.get_positions()
        account = await self.client.get_account()

        # Parse balance
        balance = 0.0
        available = 0.0
        if account:
            for asset in account.get("assets", []):
                if asset.get("asset") == "USDT":
                    balance = float(asset.get("walletBalance", 0))
                    available = float(asset.get("availableBalance", 0))
                    break

        # Parse current positions
        current_positions = []
        current_symbols = set()
        for p in (current_raw or []):
            symbol = p.get("symbol", "")
            amt = float(p.get("positionAmt", 0))
            if amt == 0:
                continue

            current_symbols.add(symbol)
            entry_price = float(p.get("entryPrice", 0))
            mark_price = float(p.get("markPrice", 0))
            unrealized_pnl = float(p.get("unRealizedProfit", 0))
            leverage = int(p.get("leverage", 20))
            margin = float(p.get("isolatedMargin", 0)) or float(p.get("initialMargin", 0))

            side = "LONG" if amt > 0 else "SHORT"
            pnl_pct = 0
            if margin > 0:
                pnl_pct = (unrealized_pnl / margin) * 100

            pos_data = {
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "current_price": mark_price,
                "quantity": abs(amt),
                "margin_usdt": round(margin, 4),
                "leverage": leverage,
                "unrealized_pnl": round(unrealized_pnl, 4),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "hold_duration_min": 0,  # Will be calculated if we track entry time
            }

            # Check for safety SL/TP
            if entry_price > 0:
                if side == "LONG":
                    pos_data["safety_sl_price"] = round(entry_price * (1 - settings.SAFETY_SL_PCT / 100), 4)
                    pos_data["safety_tp_price"] = round(entry_price * (1 + settings.SAFETY_TP_PCT / 100), 4)
                else:
                    pos_data["safety_sl_price"] = round(entry_price * (1 + settings.SAFETY_SL_PCT / 100), 4)
                    pos_data["safety_tp_price"] = round(entry_price * (1 - settings.SAFETY_TP_PCT / 100), 4)

            current_positions.append(pos_data)

        # Detect closed between cycles (was in last_positions, now gone)
        closed_between = []
        for symbol, old_pos in self._last_positions.items():
            if symbol not in current_symbols:
                # Position was closed — try to get details
                closed_info = await self._get_close_details(symbol, old_pos)
                closed_between.append(closed_info)
                log.info(f"Position closed between cycles: {symbol} {old_pos.get('side')} → {closed_info.get('closed_by')}")

        # Update last known positions
        self._last_positions = {p["symbol"]: p for p in current_positions}

        return current_positions, closed_between, balance, available

    async def _get_close_details(self, symbol: str, old_pos: dict) -> dict:
        """
        Figure out how a position was closed (SL/TP/manual).
        Query recent trades from Binance.
        """
        result = {
            "symbol": symbol,
            "side": old_pos.get("side", "UNKNOWN"),
            "closed_by": "UNKNOWN",
            "realized_pnl": 0,
            "commission": 0,
        }

        try:
            # Check recent trades for this symbol
            trades = await self.client.get_trades(symbol, limit=5)
            if trades:
                # Sum up PnL and commission from recent trades
                total_pnl = 0
                total_commission = 0
                for t in trades:
                    total_pnl += float(t.get("realizedPnl", 0))
                    total_commission += float(t.get("commission", 0))

                result["realized_pnl"] = round(total_pnl, 4)
                result["commission"] = round(total_commission, 4)

            # Check recent orders to determine close type
            orders = await self.client.get_all_orders(symbol, limit=5)
            if orders:
                for order in reversed(orders):
                    if order.get("status") == "FILLED":
                        order_type = order.get("type", "")
                        if order_type == "STOP_MARKET":
                            result["closed_by"] = "STOP_LOSS"
                        elif order_type == "TAKE_PROFIT_MARKET":
                            result["closed_by"] = "TAKE_PROFIT"
                        else:
                            result["closed_by"] = "MARKET"
                        result["binance_order_id"] = order.get("orderId")
                        break

        except Exception as e:
            log.warning(f"Failed to get close details for {symbol}: {e}")

        return result

    def store_order_ids(self, symbol: str, order_ids: List[int]):
        """Store order IDs for tracking between cycles."""
        self._last_order_ids[symbol] = order_ids
