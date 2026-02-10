"""
Binance Data Collector
Collects price, OHLCV, order book, funding rate, and long/short ratio
from Binance Futures API (all FREE)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from binance.client import Client
from binance.enums import KLINE_INTERVAL_1MINUTE, KLINE_INTERVAL_5MINUTE, KLINE_INTERVAL_1HOUR

from src.utils.config import config
from src.utils.logger import logger


class BinanceCollector:
    """Collects market data from Binance Futures"""

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
                logger.debug(f"  ✓ {symbol}: ${data['price']:,.2f} | FR: {data.get('funding_rate', 0):.4f}")
            except Exception as e:
                logger.error(f"  ✗ {symbol}: {e}")

        logger.info(f"📊 Collected {len(results['coins'])}/{len(self.symbols)} coins")
        return results

    async def _collect_symbol(self, symbol: str) -> Dict[str, Any]:
        """Collect comprehensive data for single symbol"""
        loop = asyncio.get_event_loop()

        # ── Parallel data fetch ──
        ticker_task = loop.run_in_executor(
            None, lambda: self.client.get_symbol_ticker(symbol=symbol)
        )
        stats_task = loop.run_in_executor(
            None, lambda: self.client.get_ticker(symbol=symbol)
        )
        klines_1m_task = loop.run_in_executor(
            None, lambda: self.client.get_klines(
                symbol=symbol,
                interval=KLINE_INTERVAL_1MINUTE,
                limit=60  # Last hour of 1m candles
            )
        )
        klines_5m_task = loop.run_in_executor(
            None, lambda: self.client.get_klines(
                symbol=symbol,
                interval=KLINE_INTERVAL_5MINUTE,
                limit=200
            )
        )
        klines_1h_task = loop.run_in_executor(
            None, lambda: self.client.get_klines(
                symbol=symbol,
                interval=KLINE_INTERVAL_1HOUR,
                limit=48
            )
        )
        orderbook_task = loop.run_in_executor(
            None, lambda: self.client.get_order_book(symbol=symbol, limit=5)
        )

        # Wait for all
        ticker, stats, klines_1m, klines_5m, klines_1h, order_book = await asyncio.gather(
            ticker_task, stats_task, klines_1m_task, klines_5m_task, klines_1h_task, orderbook_task
        )

        price = float(ticker['price'])

        # ── Futures-specific data (funding rate + long/short) ──
        funding_rate = await self._get_funding_rate(symbol)
        long_short_ratio = await self._get_long_short_ratio(symbol)

        # Parse OHLCV
        ohlcv_1m = self._parse_klines(klines_1m)
        ohlcv_5m = self._parse_klines(klines_5m)
        ohlcv_1h = self._parse_klines(klines_1h)

        return {
            "symbol": symbol,
            "price": price,
            "ohlcv_1m": ohlcv_1m,
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
            # ── Futures data ──
            "funding_rate": funding_rate,
            "long_short_ratio": long_short_ratio,
            "collected_at": datetime.utcnow().isoformat() + "Z"
        }

    async def _get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate for perpetual futures"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.futures_funding_rate(symbol=symbol, limit=1)
            )
            if result:
                return float(result[-1].get('fundingRate', 0))
        except Exception as e:
            logger.debug(f"Funding rate error {symbol}: {e}")
        return 0.0

    async def _get_long_short_ratio(self, symbol: str) -> Dict[str, float]:
        """Get global long/short account ratio"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.futures_global_longshort_ratio(
                    symbol=symbol, period="5m", limit=1
                )
            )
            if result:
                latest = result[-1]
                return {
                    "long_ratio": float(latest.get('longAccount', 0.5)),
                    "short_ratio": float(latest.get('shortAccount', 0.5)),
                    "long_short_ratio": float(latest.get('longShortRatio', 1.0)),
                }
        except Exception as e:
            logger.debug(f"Long/short ratio error {symbol}: {e}")
        return {"long_ratio": 0.5, "short_ratio": 0.5, "long_short_ratio": 1.0}

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

    print(f"\n{'='*60}")
    print(f"Binance Collector Test")
    print(f"{'='*60}")
    print(f"Coins collected: {len(data['coins'])}")

    for coin in data['coins'][:3]:
        print(f"\n{coin['symbol']}:")
        print(f"  Price: ${coin['price']:,.2f}")
        print(f"  24h Change: {coin['price_change_24h']:+.2f}%")
        print(f"  Funding Rate: {coin['funding_rate']:.6f}")
        lr = coin['long_short_ratio']
        print(f"  L/S Ratio: {lr['long_short_ratio']:.2f} (L:{lr['long_ratio']:.1%} S:{lr['short_ratio']:.1%})")
        print(f"  1m candles: {len(coin['ohlcv_1m'])} | 5m: {len(coin['ohlcv_5m'])} | 1h: {len(coin['ohlcv_1h'])}")


if __name__ == "__main__":
    asyncio.run(test_collector())
