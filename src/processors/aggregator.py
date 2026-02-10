"""
Data Aggregator
Combines all processed data into unified format for AI Brain.
Passes all scalping-relevant fields (fast EMAs, RSI-7, funding rate, L/S ratio).
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
        binance_raw: Dict[str, Any],  # NEW: raw binance data for funding rate
        positions: List[Dict],
        balance: Dict[str, Any],
        cycle_id: str
    ) -> Dict[str, Any]:
        """Aggregate all data into unified format"""
        logger.info("📊 Aggregating all data sources...")

        # Build funding rate lookup from raw binance data
        funding_lookup = {}
        ls_ratio_lookup = {}
        for coin in binance_raw.get('coins', []):
            symbol = coin.get('symbol', '')
            funding_lookup[symbol] = coin.get('funding_rate', 0.0)
            ls_ratio_lookup[symbol] = coin.get('long_short_ratio', {
                "long_ratio": 0.5, "short_ratio": 0.5, "long_short_ratio": 1.0
            })

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

            indicators = coin_tech.get('indicators', {})

            result['market_data'][symbol] = {
                "price": coin_tech['price'],
                "technical": {
                    "trend": coin_tech['signals']['trend'],
                    "momentum": coin_tech['signals']['momentum'],
                    "volatility": coin_tech['signals'].get('volatility', 'MEDIUM'),
                    "score": coin_tech['score'],
                    # Standard EMAs
                    "ema_20": indicators.get('ema_20', 0),
                    "ema_50": indicators.get('ema_50', 0),
                    "ema_200": indicators.get('ema_200', 0),
                    # Scalping EMAs (fast)
                    "ema_9": indicators.get('ema_9', 0),
                    "ema_21": indicators.get('ema_21', 0),
                    "ema_55": indicators.get('ema_55', 0),
                    # RSI - both fast and standard
                    "rsi_7": indicators.get('rsi_7', 50),
                    "rsi_14": indicators.get('rsi_14', 50),
                    "macd_histogram": indicators.get('macd', {}).get('histogram', 0),
                    "volume_ratio": indicators.get('volume_ratio', 1.0),
                    "atr_14": indicators.get('atr_14', 0),
                    "bollinger": indicators.get('bollinger', {}),
                },
                "sentiment": {
                    "score": coin_sentiment.get('score', 50),
                    "label": coin_sentiment.get('label', 'NEUTRAL'),
                    "key_news": sentiment.get('narrative', '')[:100]
                },
                "onchain": coin_onchain,
                # Futures-specific data
                "funding_rate": funding_lookup.get(symbol, 0.0),
                "long_short_ratio": ls_ratio_lookup.get(symbol, {}),
                # Combined scores
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

        # Calculate combined score (tech weighted heaviest for scalping)
        combined_score = (tech_score * 0.55 + sent_score * 0.25 + onch_score * 0.20)

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

        avg_funding = 0.0
        funding_count = 0

        for symbol, data in market_data.items():
            if data['combined_signal'] == 'BULLISH':
                bullish_count += 1
            elif data['combined_signal'] == 'BEARISH':
                bearish_count += 1

            # Track best opportunity (require 2/3+ alignment)
            if data['combined_score'] > best_score and data['signal_agreement'] != 'MIXED':
                best_score = data['combined_score']
                best_opportunity = symbol

            # Average funding rate
            fr = data.get('funding_rate', 0)
            if fr != 0:
                avg_funding += fr
                funding_count += 1

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
            "risk_level": risk_level,
            "avg_funding_rate": round(avg_funding / max(funding_count, 1), 6),
        }
