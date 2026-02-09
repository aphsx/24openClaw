"""
Binance Data Collector
Collects price and OHLCV data from Binance API
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from binance.client import Client
from binance.enums import KLINE_INTERVAL_5MINUTE, KLINE_INTERVAL_1HOUR

from src.utils.config import config
from src.utils.logger import logger


class BinanceCollector:
    """Collects market data from Binance"""
    
    def __init__(self):
        self.client = Client(
            config.BINANCE_API_KEY,
            config.BINANCE_API_SECRET
        )
        self.symbols = config.TRACKED_COINS
        
    async def collect(self) -> Dict[str, Any]:
        """Collect data for all tracked symbols"""
        logger.info(f"📥 Collecting Binance data for {len(self.symbols)} coins")
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "binance_collector",
            "coins": []
        }
        
        for symbol in self.symbols:
            try:
                data = await self._collect_symbol(symbol)
                results["coins"].append(data)
                logger.debug(f"  ✓ {symbol}: ${data['price']:,.2f}")
            except Exception as e:
                logger.error(f"  ✗ {symbol}: {e}")
        
        logger.info(f"📊 Collected {len(results['coins'])}/{len(self.symbols)} coins")
        return results
    
    async def _collect_symbol(self, symbol: str) -> Dict[str, Any]:
        """Collect data for single symbol"""
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Get current price
        ticker = await loop.run_in_executor(
            None, lambda: self.client.get_symbol_ticker(symbol=symbol)
        )
        price = float(ticker['price'])
        
        # Get 24h stats
        stats = await loop.run_in_executor(
            None, lambda: self.client.get_ticker(symbol=symbol)
        )
        
        # Get OHLCV data (5m timeframe, last 200 candles for indicators)
        klines_5m = await loop.run_in_executor(
            None, lambda: self.client.get_klines(
                symbol=symbol,
                interval=KLINE_INTERVAL_5MINUTE,
                limit=200
            )
        )
        
        # Get 1h data for longer-term view
        klines_1h = await loop.run_in_executor(
            None, lambda: self.client.get_klines(
                symbol=symbol,
                interval=KLINE_INTERVAL_1HOUR,
                limit=48
            )
        )
        
        # Get order book for spread
        order_book = await loop.run_in_executor(
            None, lambda: self.client.get_order_book(symbol=symbol, limit=5)
        )
        
        # Parse OHLCV
        ohlcv_5m = self._parse_klines(klines_5m)
        ohlcv_1h = self._parse_klines(klines_1h)
        
        return {
            "symbol": symbol,
            "price": price,
            "ohlcv_5m": ohlcv_5m,
            "ohlcv_1h": ohlcv_1h,
            "volume_24h": float(stats['volume']),
            "quote_volume_24h": float(stats['quoteVolume']),
            "price_change_24h": float(stats['priceChangePercent']),
            "high_24h": float(stats['highPrice']),
            "low_24h": float(stats['lowPrice']),
            "order_book": {
                "best_bid": float(order_book['bids'][0][0]) if order_book['bids'] else 0,
                "best_ask": float(order_book['asks'][0][0]) if order_book['asks'] else 0,
                "spread": self._calculate_spread(order_book)
            },
            "collected_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def _parse_klines(self, klines: List) -> List[Dict]:
        """Parse Binance klines to OHLCV format"""
        result = []
        for k in klines:
            result.append({
                "t": datetime.fromtimestamp(k[0]/1000).isoformat() + "Z",
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
                "v": float(k[5])
            })
        return result
    
    def _calculate_spread(self, order_book: Dict) -> float:
        """Calculate bid-ask spread"""
        if order_book['bids'] and order_book['asks']:
            bid = float(order_book['bids'][0][0])
            ask = float(order_book['asks'][0][0])
            return abs(ask - bid)
        return 0.0


# Test function
async def test_collector():
    """Test the collector"""
    collector = BinanceCollector()
    data = await collector.collect()
    
    print(f"\n{'='*50}")
    print(f"Binance Collector Test")
    print(f"{'='*50}")
    print(f"Coins collected: {len(data['coins'])}")
    
    for coin in data['coins'][:3]:
        print(f"\n{coin['symbol']}:")
        print(f"  Price: ${coin['price']:,.2f}")
        print(f"  24h Change: {coin['price_change_24h']:+.2f}%")
        print(f"  5m candles: {len(coin['ohlcv_5m'])}")


if __name__ == "__main__":
    asyncio.run(test_collector())
