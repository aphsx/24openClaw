import os
import ccxt.async_support as ccxt
import time
from typing import List, Dict, Any, Optional

class OKXClient:
    def __init__(self):
        self.exchange = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY', ''),
            'secret': os.getenv('OKX_SECRET_KEY', ''),
            'password': os.getenv('OKX_PASSWORD', ''),
            'enableRateLimit': True,
        })

    async def close(self):
        await self.exchange.close()

    async def get_trading_symbols(self, min_volume: float = 20_000_000) -> List[Dict[str, Any]]:
        markets = await self.exchange.load_markets()
        symbols = [s for s in markets if markets[s]['swap'] and markets[s]['quote'] == 'USDT' and markets[s]['active']]
        
        tickers = await self.exchange.fetch_tickers(symbols)
        qualified = []
        for sym, t in tickers.items():
            vol = t.get('quoteVolume') or (float(t['info'].get('volCcy24h', 0)) * t['last']) or 0
            if vol > min_volume:
                qualified.append({
                    'symbol': sym.split('/')[0],
                    'price': t['last'],
                    'vol': vol
                })
        
        # Sort by volume and limit to top 25 (like TS code)
        qualified.sort(key=lambda x: x['vol'], reverse=True)
        return qualified[:25]

    async def fetch_ohlcv(self, coin: str, days: int = 180) -> List[List[Any]]:
        # OKX format: [timestamp, open, high, low, close, volume]
        since = int((time.time() - days * 86400) * 1000)
        return await self.exchange.fetch_ohlcv(f"{coin}/USDT:USDT", '1d', since, days)

    async def place_order(self, symbol: str, side: str, amount: float):
        if not os.getenv('OKX_API_KEY'):
            print(f"[DRY RUN] Would place {side} order for {symbol} amount {amount}")
            return {'id': f'mock_{int(time.time() * 1000)}'}
        
        return await self.exchange.create_market_order(f"{symbol}/USDT:USDT", side, amount)

    async def has_position(self, symbol: str) -> bool:
        if not os.getenv('OKX_API_KEY'): return False
        positions = await self.exchange.fetch_positions([f"{symbol}/USDT:USDT"])
        return len(positions) > 0

    async def close_position(self, symbol: str):
        if not os.getenv('OKX_API_KEY'):
            print(f"[DRY RUN] Closing position for {symbol}")
            return
        
        positions = await self.exchange.fetch_positions([f"{symbol}/USDT:USDT"])
        if not positions: return
        
        pos = positions[0]
        side = 'sell' if pos['side'] == 'long' else 'buy'
        amount = abs(float(pos['contracts'] or 0))
        return await self.exchange.create_market_order(f"{symbol}/USDT:USDT", side, amount, params={'reduceOnly': True})
