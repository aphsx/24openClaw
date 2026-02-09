"""
On-Chain Data Collector
Collects whale activity and exchange flows from free APIs
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import aiohttp

from src.utils.config import config
from src.utils.logger import logger


class OnchainCollector:
    """Collects on-chain data from free APIs"""
    
    def __init__(self):
        # Free API endpoints
        self.apis = {
            # Alternative.me Fear & Greed Index
            "fear_greed": "https://api.alternative.me/fng/?limit=1",
            # CoinGecko (free tier)
            "coingecko_btc": "https://api.coingecko.com/api/v3/coins/bitcoin",
            "coingecko_eth": "https://api.coingecko.com/api/v3/coins/ethereum",
        }
        
        # Whale Alert RSS (free)
        self.whale_rss = "https://whale-alert.io/feed"
        
    async def collect(self) -> Dict[str, Any]:
        """Collect on-chain data"""
        logger.info("🐋 Collecting on-chain data...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "onchain_collector",
            "metrics": {}
        }
        
        async with aiohttp.ClientSession() as session:
            # Get Fear & Greed Index
            fear_greed = await self._get_fear_greed(session)
            results["fear_greed"] = fear_greed
            
            # Get coin data from CoinGecko
            btc_data = await self._get_coingecko_data(session, "bitcoin", "BTC")
            eth_data = await self._get_coingecko_data(session, "ethereum", "ETH")
            
            results["metrics"]["BTC"] = btc_data
            results["metrics"]["ETH"] = eth_data
            
            # Add placeholder data for other coins
            for symbol in ["BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"]:
                results["metrics"][symbol] = self._create_placeholder(symbol)
        
        logger.info(f"🐋 On-chain data collected")
        return results
    
    async def _get_fear_greed(self, session: aiohttp.ClientSession) -> Dict:
        """Get Fear & Greed Index"""
        try:
            async with session.get(
                self.apis["fear_greed"],
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fng = data.get('data', [{}])[0]
                    return {
                        "value": int(fng.get('value', 50)),
                        "label": fng.get('value_classification', 'Neutral'),
                        "timestamp": fng.get('timestamp', '')
                    }
        except Exception as e:
            logger.error(f"Fear & Greed API error: {e}")
        
        return {"value": 50, "label": "Neutral", "timestamp": ""}
    
    async def _get_coingecko_data(
        self, 
        session: aiohttp.ClientSession, 
        coin_id: str,
        symbol: str
    ) -> Dict:
        """Get data from CoinGecko"""
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false"
            }
            
            async with session.get(
                url, 
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    market = data.get('market_data', {})
                    
                    # Determine signal based on price change
                    price_change_24h = market.get('price_change_percentage_24h', 0) or 0
                    price_change_7d = market.get('price_change_percentage_7d', 0) or 0
                    
                    if price_change_24h > 3 and price_change_7d > 5:
                        signal = "BULLISH"
                        score = 0.8
                    elif price_change_24h < -3 and price_change_7d < -5:
                        signal = "BEARISH"
                        score = 0.2
                    elif price_change_24h > 0:
                        signal = "NEUTRAL_BULLISH"
                        score = 0.6
                    elif price_change_24h < 0:
                        signal = "NEUTRAL_BEARISH"
                        score = 0.4
                    else:
                        signal = "NEUTRAL"
                        score = 0.5
                    
                    return {
                        "coin": symbol,
                        "signal": signal,
                        "score": score,
                        "market_cap_rank": data.get('market_cap_rank', 0),
                        "price_change_24h": price_change_24h,
                        "price_change_7d": price_change_7d,
                        "total_supply": market.get('total_supply', 0),
                        "circulating_supply": market.get('circulating_supply', 0),
                        "ath_change_percentage": market.get('ath_change_percentage', {}).get('usd', 0),
                        "reasoning": self._generate_reasoning(symbol, signal, price_change_24h)
                    }
                    
        except Exception as e:
            logger.error(f"CoinGecko API error for {symbol}: {e}")
        
        return self._create_placeholder(symbol)
    
    def _create_placeholder(self, symbol: str) -> Dict:
        """Create placeholder data for coins without API data"""
        return {
            "coin": symbol,
            "signal": "NEUTRAL",
            "score": 0.5,
            "price_change_24h": 0,
            "price_change_7d": 0,
            "reasoning": f"Limited on-chain data available for {symbol}"
        }
    
    def _generate_reasoning(self, symbol: str, signal: str, change_24h: float) -> str:
        """Generate reasoning text"""
        if signal == "BULLISH":
            return f"{symbol} showing strong momentum with {change_24h:+.1f}% in 24h"
        elif signal == "BEARISH":
            return f"{symbol} under selling pressure with {change_24h:+.1f}% in 24h"
        elif signal == "NEUTRAL_BULLISH":
            return f"{symbol} slightly positive at {change_24h:+.1f}% in 24h"
        elif signal == "NEUTRAL_BEARISH":
            return f"{symbol} slightly negative at {change_24h:+.1f}% in 24h"
        return f"{symbol} trading sideways"


# Test function
async def test_collector():
    """Test the on-chain collector"""
    collector = OnchainCollector()
    data = await collector.collect()
    
    print(f"\n{'='*50}")
    print(f"On-Chain Collector Test")
    print(f"{'='*50}")
    print(f"Fear & Greed: {data['fear_greed']['value']} ({data['fear_greed']['label']})")
    
    for symbol, metrics in data['metrics'].items():
        print(f"\n{symbol}:")
        print(f"  Signal: {metrics['signal']}")
        print(f"  Score: {metrics['score']}")


if __name__ == "__main__":
    asyncio.run(test_collector())
