"""
ClawBot AI — Binance REST API Wrapper (Self-Written)
HMAC-SHA256 signed requests for Binance Futures API.
No external Binance libraries — pure aiohttp + hmac.
"""
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from src.utils.config import settings
from src.utils.logger import log


class BinanceREST:
    """
    Self-written Binance Futures REST API client.
    All requests signed with HMAC-SHA256.
    """

    def __init__(self):
        self.base_url = settings.binance_base_url
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self.api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _sign(self, params: dict) -> dict:
        """Add timestamp and HMAC-SHA256 signature."""
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _request(self, method: str, path: str, params: dict = None, signed: bool = False) -> Any:
        """Make HTTP request to Binance API."""
        session = await self._get_session()
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{self.base_url}{path}"

        try:
            if method == "GET":
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        log.error(f"Binance API error {resp.status}: {data}")
                    return data
            elif method == "POST":
                async with session.post(url, params=params) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        log.error(f"Binance API error {resp.status}: {data}")
                    return data
            elif method == "DELETE":
                async with session.delete(url, params=params) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        log.error(f"Binance API error {resp.status}: {data}")
                    return data
        except Exception as e:
            log.error(f"Binance request failed: {path} - {e}")
            return None

    # ============================================================
    # PUBLIC ENDPOINTS (no signature needed)
    # ============================================================

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[list]:
        """Get candlestick/kline data."""
        data = await self._request("GET", "/fapi/v1/klines", {
            "symbol": symbol, "interval": interval, "limit": limit,
        })
        return data or []

    async def get_ticker_price(self, symbol: str = None) -> Any:
        """Get current price(s)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/fapi/v1/ticker/price", params)

    async def get_ticker_24h(self, symbol: str = None) -> Any:
        """Get 24h ticker stats."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/fapi/v1/ticker/24hr", params)

    async def get_funding_rate(self, symbol: str) -> Any:
        """Get latest funding rate."""
        return await self._request("GET", "/fapi/v1/fundingRate", {
            "symbol": symbol, "limit": 1,
        })

    async def get_long_short_ratio(self, symbol: str, period: str = "5m") -> Any:
        """Get long/short account ratio."""
        return await self._request("GET", "/futures/data/globalLongShortAccountRatio", {
            "symbol": symbol, "period": period, "limit": 1,
        })

    async def get_open_interest(self, symbol: str) -> Any:
        """Get open interest."""
        return await self._request("GET", "/fapi/v1/openInterest", {
            "symbol": symbol,
        })

    async def get_top_movers(self) -> List[dict]:
        """Get all tickers sorted by absolute price change % (for dynamic discovery)."""
        data = await self.get_ticker_24h()
        if not data or not isinstance(data, list):
            return []
        usdt_pairs = [t for t in data if t.get("symbol", "").endswith("USDT")]
        usdt_pairs.sort(key=lambda x: abs(float(x.get("priceChangePercent", 0))), reverse=True)
        return usdt_pairs[:20]

    # ============================================================
    # SIGNED ENDPOINTS (account operations)
    # ============================================================

    async def get_account(self) -> Optional[dict]:
        """Get futures account info (balance, positions)."""
        return await self._request("GET", "/fapi/v2/account", {}, signed=True)

    async def get_balance(self) -> Optional[List[dict]]:
        """Get futures balance."""
        return await self._request("GET", "/fapi/v2/balance", {}, signed=True)

    async def get_positions(self) -> Optional[List[dict]]:
        """Get open positions."""
        data = await self._request("GET", "/fapi/v2/positionRisk", {}, signed=True)
        if not data:
            return []
        # Filter only positions with non-zero quantity
        return [p for p in data if float(p.get("positionAmt", 0)) != 0]

    async def get_open_orders(self, symbol: str = None) -> Optional[List[dict]]:
        """Get open orders."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/fapi/v1/openOrders", params, signed=True)

    async def get_order(self, symbol: str, order_id: int) -> Optional[dict]:
        """Get specific order by ID."""
        return await self._request("GET", "/fapi/v1/order", {
            "symbol": symbol, "orderId": order_id,
        }, signed=True)

    async def get_all_orders(self, symbol: str, limit: int = 10) -> Optional[List[dict]]:
        """Get recent orders for a symbol."""
        return await self._request("GET", "/fapi/v1/allOrders", {
            "symbol": symbol, "limit": limit,
        }, signed=True)

    async def get_trades(self, symbol: str, limit: int = 10) -> Optional[List[dict]]:
        """Get recent trades (fills)."""
        return await self._request("GET", "/fapi/v1/userTrades", {
            "symbol": symbol, "limit": limit,
        }, signed=True)

    async def set_leverage(self, symbol: str, leverage: int) -> Optional[dict]:
        """Set leverage for a symbol."""
        return await self._request("POST", "/fapi/v1/leverage", {
            "symbol": symbol, "leverage": leverage,
        }, signed=True)

    async def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> Optional[dict]:
        """Set margin type (ISOLATED or CROSSED)."""
        try:
            return await self._request("POST", "/fapi/v1/marginType", {
                "symbol": symbol, "marginType": margin_type,
            }, signed=True)
        except Exception:
            pass  # Already set — Binance throws error if already set

    async def place_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        quantity: float,
        order_type: str = "MARKET",
        price: float = None,
        stop_price: float = None,
        close_position: bool = False,
        reduce_only: bool = False,
        position_side: str = "BOTH",
    ) -> Optional[dict]:
        """Place a new order."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "positionSide": position_side,
        }
        if quantity > 0:
            params["quantity"] = f"{quantity}"
        if close_position:
            params["closePosition"] = "true"
        if reduce_only:
            params["reduceOnly"] = "true"
        if price and order_type in ("LIMIT", "STOP"):
            params["price"] = f"{price}"
            params["timeInForce"] = "GTC"
        if stop_price:
            params["stopPrice"] = f"{stop_price}"

        result = await self._request("POST", "/fapi/v1/order", params, signed=True)
        if result:
            log.info(f"Order placed: {symbol} {side} qty={quantity} type={order_type}")
        return result

    async def cancel_order(self, symbol: str, order_id: int) -> Optional[dict]:
        """Cancel an order."""
        return await self._request("DELETE", "/fapi/v1/order", {
            "symbol": symbol, "orderId": order_id,
        }, signed=True)

    async def cancel_all_orders(self, symbol: str) -> Optional[dict]:
        """Cancel all open orders for a symbol."""
        return await self._request("DELETE", "/fapi/v1/allOpenOrders", {
            "symbol": symbol,
        }, signed=True)

    async def get_exchange_info(self) -> Optional[dict]:
        """Get exchange info (symbol precision, filters)."""
        return await self._request("GET", "/fapi/v1/exchangeInfo")

    async def get_symbol_precision(self, symbol: str) -> dict:
        """Get quantity and price precision for a symbol."""
        info = await self.get_exchange_info()
        if not info:
            return {"quantity_precision": 3, "price_precision": 2}
        for s in info.get("symbols", []):
            if s["symbol"] == symbol:
                return {
                    "quantity_precision": s.get("quantityPrecision", 3),
                    "price_precision": s.get("pricePrecision", 2),
                    "min_qty": next(
                        (f["minQty"] for f in s.get("filters", []) if f["filterType"] == "LOT_SIZE"),
                        "0.001",
                    ),
                }
        return {"quantity_precision": 3, "price_precision": 2}
