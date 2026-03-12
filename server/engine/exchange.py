import os
import time
import asyncio
import ccxt.async_support as ccxt
from typing import List, Dict, Any, Optional

class BinanceClient:
    def __init__(self):
        api_key = os.getenv('BINANCE_API_KEY', '')
        secret  = os.getenv('BINANCE_SECRET_KEY', '')
        self.dry_run = not bool(api_key)

        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',   # USDT-M Perpetual Futures
                'adjustForTimeDifference': True,
            },
        })

    async def close(self):
        await self.exchange.close()

    # ─────────────────────────────────────────────────────
    # Universe
    # ─────────────────────────────────────────────────────

    async def get_trading_symbols(self, min_volume: float = 20_000_000) -> List[Dict[str, Any]]:
        """Return top-25 USDT-M perpetuals by 24h volume above min_volume."""
        markets = await self.exchange.load_markets()
        # Linear USDT-M swaps only
        symbols = [
            s for s, m in markets.items()
            if m.get('swap') and m.get('linear') and m['quote'] == 'USDT' and m['active']
        ]

        tickers = await self.exchange.fetch_tickers(symbols)
        qualified = []
        for sym, t in tickers.items():
            vol = float(t.get('quoteVolume') or 0)
            price = float(t.get('last') or 0)
            if vol > min_volume and price > 0:
                qualified.append({
                    'symbol': sym.split('/')[0],  # 'BTC' from 'BTC/USDT:USDT'
                    'price':  price,
                    'vol':    vol,
                })

        qualified.sort(key=lambda x: x['vol'], reverse=True)
        return qualified[:25]

    # ─────────────────────────────────────────────────────
    # Market Data
    # ─────────────────────────────────────────────────────

    async def fetch_ohlcv(self, coin: str, days: int = 180) -> List[List[Any]]:
        since = int((time.time() - days * 86400) * 1000)
        return await self.exchange.fetch_ohlcv(f"{coin}/USDT:USDT", '1d', since, days)

    async def get_mark_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = await self.exchange.fetch_ticker(f"{symbol}/USDT:USDT")
            return float(ticker.get('last') or ticker.get('mark') or 0) or None
        except Exception:
            return None

    async def get_funding_rate(self, symbol: str) -> float:
        """Return absolute current funding rate (e.g. 0.0001 = 0.01%)."""
        try:
            fr = await self.exchange.fetch_funding_rate(f"{symbol}/USDT:USDT")
            return abs(float(fr.get('fundingRate') or 0))
        except Exception:
            return 0.0

    # ─────────────────────────────────────────────────────
    # Account
    # ─────────────────────────────────────────────────────

    async def get_balance(self) -> Dict[str, Any]:
        if self.dry_run:
            return {'total_usdt': 10_000.0, 'free_usdt': 9_500.0, 'used_usdt': 500.0}
        bal = await self.exchange.fetch_balance()
        total = float(bal['total'].get('USDT') or 0)
        free  = float(bal['free'].get('USDT') or 0)
        return {'total_usdt': total, 'free_usdt': free, 'used_usdt': total - free}

    # ─────────────────────────────────────────────────────
    # Orders
    # ─────────────────────────────────────────────────────

    async def place_order(self, symbol: str, side: str, size_usd: float) -> Dict[str, Any]:
        """
        Place a market order.
        side: 'buy' (long) or 'sell' (short)
        size_usd: notional USD value of the leg
        Returns order dict with 'id', 'average' (fill price).
        """
        if self.dry_run:
            mock_price = await self.get_mark_price(symbol) or 1.0
            print(f"[DRY RUN] {side.upper()} {symbol} notional=${size_usd:.2f} ~{size_usd/mock_price:.4f} contracts @ {mock_price:.4f}")
            return {
                'id':      f'mock_{int(time.time() * 1000)}',
                'symbol':  symbol,
                'side':    side,
                'average': mock_price,
                'filled':  size_usd / mock_price,
                'cost':    size_usd,
            }

        sym    = f"{symbol}/USDT:USDT"
        ticker = await self.exchange.fetch_ticker(sym)
        price  = float(ticker['last'])
        markets = await self.exchange.load_markets()
        qty    = size_usd / price
        qty    = float(self.exchange.amount_to_precision(sym, qty))

        order = await self.exchange.create_market_order(sym, side, qty)
        return order

    async def close_position(self, symbol: str, open_side: str) -> Dict[str, Any]:
        """
        Close an open position via reduce-only market order.
        open_side: the side used to OPEN ('buy' or 'sell').
        Close side is the opposite.
        """
        close_side = 'sell' if open_side == 'buy' else 'buy'

        if self.dry_run:
            print(f"[DRY RUN] Close {symbol} via {close_side.upper()} reduce-only")
            return {'id': f'close_mock_{int(time.time() * 1000)}', 'symbol': symbol}

        sym       = f"{symbol}/USDT:USDT"
        positions = await self.exchange.fetch_positions([sym])
        pos = next((p for p in positions if abs(float(p.get('contracts') or 0)) > 0), None)
        if not pos:
            return {}  # Already closed

        contracts = abs(float(pos['contracts']))
        order = await self.exchange.create_market_order(
            sym, close_side, contracts,
            params={'reduceOnly': True},
        )
        return order

    # ─────────────────────────────────────────────────────
    # Positions
    # ─────────────────────────────────────────────────────

    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Return position dict if open, else None."""
        if self.dry_run:
            return None
        try:
            positions = await self.exchange.fetch_positions([f"{symbol}/USDT:USDT"])
            return next((p for p in positions if abs(float(p.get('contracts') or 0)) > 0), None)
        except Exception:
            return None

    async def get_all_positions(self) -> List[Dict]:
        """Return all open positions."""
        if self.dry_run:
            return []
        try:
            positions = await self.exchange.fetch_positions()
            return [p for p in positions if abs(float(p.get('contracts') or 0)) > 0]
        except Exception:
            return []
