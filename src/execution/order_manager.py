"""
ClawBot AI — Order Manager
Executes AI decisions via Binance Futures API.
Handles: opening positions (with safety SL/TP), closing positions, leverage setup.
"""
from typing import Any, Dict, List, Optional

from src.data.binance_rest import BinanceREST
from src.utils.config import settings
from src.utils.logger import log


class OrderManager:
    """
    Translates AI decisions into Binance Futures orders.
    - Sets leverage before opening
    - Places market orders
    - Attaches safety SL/TP orders
    - Tracks executed trades
    """

    def __init__(self, client: BinanceREST):
        self.client = client
        self._precisions: Dict[str, dict] = {}  # Cache symbol precisions

    async def execute_actions(self, actions: List[dict], balance: float) -> List[dict]:
        """
        Execute a list of AI actions.
        Returns list of executed trade records.
        """
        executed = []
        for action in actions:
            symbol = action.get("symbol", "")
            act = action.get("action", "SKIP")
            confidence = action.get("confidence", 0)

            if act in ("SKIP", "HOLD"):
                continue

            try:
                if act in ("OPEN_LONG", "OPEN_SHORT"):
                    result = await self._open_position(
                        symbol=symbol,
                        side="LONG" if act == "OPEN_LONG" else "SHORT",
                        margin_usdt=float(action.get("margin_usdt", settings.MIN_ORDER_USDT)),
                        confidence=confidence,
                        reason=action.get("reason", ""),
                    )
                    if result:
                        executed.append(result)

                elif act == "CLOSE":
                    result = await self._close_position(
                        symbol=symbol,
                        reason=action.get("reason", ""),
                    )
                    if result:
                        executed.append(result)

            except Exception as e:
                log.error(f"Failed to execute {act} on {symbol}: {e}")

        return executed

    async def _open_position(
        self, symbol: str, side: str, margin_usdt: float,
        confidence: int = 0, reason: str = "",
    ) -> Optional[dict]:
        """Open a new position with safety SL/TP."""
        # Ensure leverage is set
        await self.client.set_leverage(symbol, settings.LEVERAGE)
        try:
            await self.client.set_margin_type(symbol, "ISOLATED")
        except Exception:
            pass  # Already set

        # Get precision
        precision = await self._get_precision(symbol)

        # Calculate quantity
        price_data = await self.client.get_ticker_price(symbol)
        if not price_data:
            log.error(f"Cannot get price for {symbol}")
            return None
        current_price = float(price_data.get("price", 0))
        if current_price <= 0:
            return None

        # quantity = (margin * leverage) / price
        notional = margin_usdt * settings.LEVERAGE
        quantity = notional / current_price
        qty_precision = precision.get("quantity_precision", 3)
        quantity = round(quantity, qty_precision)

        min_qty = float(precision.get("min_qty", "0.001"))
        if quantity < min_qty:
            log.warning(f"Quantity {quantity} below min {min_qty} for {symbol}")
            return None

        # Place market order
        order_side = "BUY" if side == "LONG" else "SELL"
        result = await self.client.place_order(
            symbol=symbol,
            side=order_side,
            quantity=quantity,
            order_type="MARKET",
        )

        if not result or "orderId" not in result:
            log.error(f"Order failed for {symbol}: {result}")
            return None

        order_id = result["orderId"]
        fill_price = float(result.get("avgPrice", current_price))

        log.info(f"Opened {side} {symbol}: qty={quantity} price={fill_price} margin={margin_usdt}")

        # Place safety SL/TP
        await self._place_safety_orders(symbol, side, fill_price, quantity)

        # Build trade record
        trade = {
            "binance_order_id": str(order_id),
            "symbol": symbol,
            "side": side,
            "action": "OPEN",
            "entry_price": fill_price,
            "quantity": quantity,
            "margin_usdt": margin_usdt,
            "leverage": settings.LEVERAGE,
            "commission": float(result.get("commission", 0)),
            "commission_asset": result.get("commissionAsset", "USDT"),
            "ai_confidence": confidence,
            "ai_reason": reason,
            "closed_by": None,
        }
        return trade

    async def _close_position(self, symbol: str, reason: str = "") -> Optional[dict]:
        """Close an existing position."""
        # Get current position
        positions = await self.client.get_positions()
        target = None
        for p in (positions or []):
            if p.get("symbol") == symbol and float(p.get("positionAmt", 0)) != 0:
                target = p
                break

        if not target:
            log.warning(f"No position to close for {symbol}")
            return None

        amt = float(target.get("positionAmt", 0))
        side = "LONG" if amt > 0 else "SHORT"
        close_side = "SELL" if amt > 0 else "BUY"
        quantity = abs(amt)

        # Cancel existing SL/TP orders first
        await self.client.cancel_all_orders(symbol)

        # Place close order
        result = await self.client.place_order(
            symbol=symbol,
            side=close_side,
            quantity=quantity,
            order_type="MARKET",
            reduce_only=True,
        )

        if not result or "orderId" not in result:
            log.error(f"Close order failed for {symbol}: {result}")
            return None

        order_id = result["orderId"]
        exit_price = float(result.get("avgPrice", 0))
        entry_price = float(target.get("entryPrice", 0))

        # Calculate PnL
        if side == "LONG":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        margin = float(target.get("isolatedMargin", 0)) or float(target.get("initialMargin", 0))
        pnl_pct = (pnl / margin * 100) if margin > 0 else 0

        log.info(f"Closed {side} {symbol}: PnL={pnl:+.4f} USDT ({pnl_pct:+.1f}%)")

        trade = {
            "binance_order_id": str(order_id),
            "symbol": symbol,
            "side": side,
            "action": "CLOSE",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "margin_usdt": margin,
            "leverage": settings.LEVERAGE,
            "realized_pnl": round(pnl, 4),
            "realized_pnl_pct": round(pnl_pct, 2),
            "commission": float(result.get("commission", 0)),
            "ai_confidence": 0,
            "ai_reason": reason,
            "closed_by": "AI",
        }
        return trade

    async def _place_safety_orders(self, symbol: str, side: str, entry_price: float, quantity: float):
        """Place safety SL and TP orders (fallback for between cycles)."""
        try:
            price_precision = (await self._get_precision(symbol)).get("price_precision", 2)

            if side == "LONG":
                sl_price = round(entry_price * (1 - settings.SAFETY_SL_PCT / 100), price_precision)
                tp_price = round(entry_price * (1 + settings.SAFETY_TP_PCT / 100), price_precision)
                sl_side = "SELL"
            else:
                sl_price = round(entry_price * (1 + settings.SAFETY_SL_PCT / 100), price_precision)
                tp_price = round(entry_price * (1 - settings.SAFETY_TP_PCT / 100), price_precision)
                sl_side = "BUY"

            # Stop Loss
            await self.client.place_order(
                symbol=symbol, side=sl_side, quantity=quantity,
                order_type="STOP_MARKET", stop_price=sl_price,
                reduce_only=True,
            )
            log.info(f"Safety SL set for {symbol}: {sl_price}")

            # Take Profit
            await self.client.place_order(
                symbol=symbol, side=sl_side, quantity=quantity,
                order_type="TAKE_PROFIT_MARKET", stop_price=tp_price,
                reduce_only=True,
            )
            log.info(f"Safety TP set for {symbol}: {tp_price}")

        except Exception as e:
            log.error(f"Failed to set safety SL/TP for {symbol}: {e}")

    async def _get_precision(self, symbol: str) -> dict:
        """Get and cache symbol precision."""
        if symbol not in self._precisions:
            self._precisions[symbol] = await self.client.get_symbol_precision(symbol)
        return self._precisions[symbol]
