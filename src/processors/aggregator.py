"""
Data Aggregator
Combines all processed data into unified format for AI Brain
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from src.utils.logger import logger


class DataAggregator:
    """Aggregates all data sources for AI analysis"""
    
    def aggregate(
        self,
        technical: Dict[str, Any],
        sentiment: Dict[str, Any],
        onchain: Dict[str, Any],
        positions: List[Dict],
        balance: Dict[str, Any],
        cycle_id: str
    ) -> Dict[str, Any]:
        """Aggregate all data into unified format"""
        logger.info("📊 Aggregating all data sources...")
        
        result = {
            "cycle_id": cycle_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "aggregator",
            
            # Account info
            "account": self._format_account(balance),
            
            # Current positions
            "current_positions": self._format_positions(positions),
            
            # Market data by coin
            "market_data": {},
            
            # Summary
            "summary": {}
        }
        
        # Build market data per coin
        for coin_tech in technical.get('coins', []):
            symbol = coin_tech['symbol']
            base_symbol = symbol.replace('USDT', '')
            
            # Get matching data from other sources
            coin_sentiment = sentiment.get('overall_sentiment', {})
            coin_onchain = self._find_onchain(onchain, base_symbol)
            
            # Combine signals
            combined = self._combine_signals(coin_tech, coin_sentiment, coin_onchain)
            
            result['market_data'][symbol] = {
                "price": coin_tech['price'],
                "technical": {
                    "trend": coin_tech['signals']['trend'],
                    "momentum": coin_tech['signals']['momentum'],
                    "score": coin_tech['score'],
                    "ema_20": coin_tech['indicators']['ema_20'],
                    "ema_50": coin_tech['indicators']['ema_50'],
                    "ema_200": coin_tech['indicators']['ema_200'],
                    "rsi_14": coin_tech['indicators']['rsi_14'],
                    "macd_histogram": coin_tech['indicators']['macd']['histogram'],
                    "volume_ratio": coin_tech['indicators']['volume_ratio']
                },
                "sentiment": {
                    "score": coin_sentiment.get('score', 50),
                    "label": coin_sentiment.get('label', 'NEUTRAL'),
                    "key_news": sentiment.get('narrative', '')[:100]
                },
                "onchain": coin_onchain,
                "combined_score": combined['score'],
                "combined_signal": combined['signal'],
                "signal_agreement": combined['agreement']
            }
        
        # Generate summary
        result['summary'] = self._generate_summary(result['market_data'], positions)
        
        logger.info(f"📊 Aggregated {len(result['market_data'])} coins")
        return result
    
    def _format_account(self, balance: Dict) -> Dict:
        """Format account balance info"""
        return {
            "balance_usdt": balance.get('total', 0),
            "available_margin": balance.get('free', 0),
            "used_margin": balance.get('used', 0),
            "total_pnl_today": balance.get('pnl_today', 0)
        }
    
    def _format_positions(self, positions: List[Dict]) -> List[Dict]:
        """Format current positions"""
        formatted = []
        for pos in positions:
            formatted.append({
                "symbol": pos.get('symbol', ''),
                "side": pos.get('side', ''),
                "entry_price": pos.get('entryPrice', 0),
                "current_price": pos.get('markPrice', 0),
                "pnl_percent": pos.get('percentage', 0),
                "pnl_usdt": pos.get('unrealizedPnl', 0),
                "leverage": pos.get('leverage', 20),
                "margin": pos.get('initialMargin', 0),
                "opened_at": pos.get('datetime', '')
            })
        return formatted
    
    def _find_onchain(self, onchain: Dict, symbol: str) -> Dict:
        """Find on-chain data for symbol"""
        metrics = onchain.get('metrics', {})
        coin_data = metrics.get(symbol, {})
        
        if coin_data:
            return {
                "score": int(coin_data.get('score', 0.5) * 100),
                "signal": coin_data.get('signal', 'NEUTRAL'),
                "exchange_flow": f"24h: {coin_data.get('price_change_24h', 0):+.1f}%",
                "reasoning": coin_data.get('reasoning', '')
            }
        
        return {
            "score": 50,
            "signal": "NEUTRAL",
            "exchange_flow": "N/A",
            "reasoning": "No on-chain data"
        }
    
    def _combine_signals(
        self, 
        tech: Dict, 
        sentiment: Dict, 
        onchain: Dict
    ) -> Dict:
        """Combine signals from all sources"""
        # Get scores
        tech_score = tech.get('score', 50)
        sent_score = sentiment.get('score', 50)
        onch_score = onchain.get('score', 50)
        
        # Calculate combined score
        combined_score = (tech_score * 0.5 + sent_score * 0.3 + onch_score * 0.2)
        
        # Get signals
        tech_signal = "BULLISH" if tech_score >= 60 else "BEARISH" if tech_score < 40 else "NEUTRAL"
        sent_signal = sentiment.get('label', 'NEUTRAL')
        if 'BULLISH' in sent_signal.upper():
            sent_signal = 'BULLISH'
        elif 'BEARISH' in sent_signal.upper():
            sent_signal = 'BEARISH'
        else:
            sent_signal = 'NEUTRAL'
        onch_signal = onchain.get('signal', 'NEUTRAL')
        if 'BULLISH' in onch_signal.upper():
            onch_signal = 'BULLISH'
        elif 'BEARISH' in onch_signal.upper():
            onch_signal = 'BEARISH'
        else:
            onch_signal = 'NEUTRAL'
        
        # Count alignment
        signals = [tech_signal, sent_signal, onch_signal]
        bullish_count = signals.count('BULLISH')
        bearish_count = signals.count('BEARISH')
        
        if bullish_count >= 2:
            combined_signal = "BULLISH"
            agreement = f"{bullish_count}/3 ALIGNED"
        elif bearish_count >= 2:
            combined_signal = "BEARISH"
            agreement = f"{bearish_count}/3 ALIGNED"
        else:
            combined_signal = "NEUTRAL"
            agreement = "MIXED"
        
        return {
            "score": round(combined_score, 1),
            "signal": combined_signal,
            "agreement": agreement
        }
    
    def _generate_summary(self, market_data: Dict, positions: List) -> Dict:
        """Generate market summary"""
        # Count bullish/bearish coins
        bullish_count = 0
        bearish_count = 0
        best_opportunity = None
        best_score = 0
        
        for symbol, data in market_data.items():
            if data['combined_signal'] == 'BULLISH':
                bullish_count += 1
            elif data['combined_signal'] == 'BEARISH':
                bearish_count += 1
            
            # Track best opportunity
            if data['combined_score'] > best_score and '3/3' in data['signal_agreement']:
                best_score = data['combined_score']
                best_opportunity = symbol
        
        # Determine market outlook
        if bullish_count > bearish_count:
            market_outlook = "BULLISH"
        elif bearish_count > bullish_count:
            market_outlook = "BEARISH"
        else:
            market_outlook = "NEUTRAL"
        
        # Risk level based on positions
        if len(positions) >= 3:
            risk_level = "HIGH"
        elif len(positions) >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "market_outlook": market_outlook,
            "bullish_coins": bullish_count,
            "bearish_coins": bearish_count,
            "best_opportunity": best_opportunity,
            "best_score": best_score,
            "open_positions": len(positions),
            "risk_level": risk_level
        }


# Test
def test_aggregator():
    """Test the aggregator"""
    aggregator = DataAggregator()
    
    # Sample data
    tech = {"coins": [{"symbol": "BTCUSDT", "price": 70000, "score": 75, 
                       "signals": {"trend": "BULLISH", "momentum": "NEUTRAL"},
                       "indicators": {"ema_20": 69500, "ema_50": 68000, "ema_200": 65000,
                                     "rsi_14": 55, "macd": {"histogram": 100}, "volume_ratio": 1.2}}]}
    sentiment = {"overall_sentiment": {"score": 72, "label": "BULLISH"}, "narrative": "Positive market"}
    onchain = {"metrics": {"BTC": {"score": 0.8, "signal": "BULLISH", "reasoning": "Accumulation"}}}
    
    result = aggregator.aggregate(tech, sentiment, onchain, [], {"total": 1000, "free": 900}, "test_001")
    print(f"\n{'='*50}")
    print("Aggregator Test")
    print(f"{'='*50}")
    print(f"Market outlook: {result['summary']['market_outlook']}")
    print(f"Best opportunity: {result['summary']['best_opportunity']}")


if __name__ == "__main__":
    test_aggregator()
