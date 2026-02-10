"""
Technical Analysis Processor
Calculates technical indicators from OHLCV data
"""

from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np

from src.utils.logger import logger


class TechnicalProcessor:
    """Processes raw price data into technical indicators"""
    
    def process(self, raw_binance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw Binance data into technical analysis"""
        logger.info("⚙️ Processing technical indicators...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "technical_processor",
            "coins": []
        }
        
        for coin_data in raw_binance_data.get('coins', []):
            try:
                processed = self._process_coin(coin_data)
                results['coins'].append(processed)
                logger.debug(f"  ✓ {coin_data['symbol']}: Score {processed['score']}")
            except Exception as e:
                logger.error(f"  ✗ {coin_data['symbol']}: {e}")
        
        logger.info(f"⚙️ Processed {len(results['coins'])} coins")
        return results
    
    def _process_coin(self, coin_data: Dict) -> Dict:
        """Process single coin data — uses 5m candles as primary"""
        symbol = coin_data['symbol']
        price = coin_data['price']
        ohlcv = coin_data['ohlcv_5m']  # ใช้แท่ง 5 นาทีเป็นหลัก
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv)
        df['close'] = df['c'].astype(float)
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['volume'] = df['v'].astype(float)
        
        # Calculate indicators from 5m candles
        indicators = self._calculate_indicators(df, price)
        
        # Add day high/low from Binance 24h stats
        indicators['day_high'] = coin_data.get('high_24h', 0)
        indicators['day_low'] = coin_data.get('low_24h', 0)
        
        # Determine signals
        signals = self._determine_signals(indicators, price)
        
        # Calculate score
        score = self._calculate_score(indicators, signals)
        
        return {
            "symbol": symbol,
            "price": price,
            "indicators": indicators,
            "signals": signals,
            "score": score,
            "interest_level": self._get_interest_level(score),
            "has_signal": score >= 70,
            "narrative": self._generate_narrative(symbol, price, indicators, signals, score)
        }
    
    def _calculate_indicators(self, df: pd.DataFrame, current_price: float = 0) -> Dict:
        """Calculate all technical indicators from 5m candles"""
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Faster EMAs for scalping (9, 21, 55)
        ema_9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema_21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        ema_55 = close.ewm(span=55, adjust=False).mean().iloc[-1]
        
        # Standard EMAs
        ema_20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema_200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(close) >= 200 else close.ewm(span=len(close), adjust=False).mean().iloc[-1]
        
        # RSI — fast (7) + standard (14)
        rsi_7 = self._calculate_rsi(close, 7)
        rsi_14 = self._calculate_rsi(close, 14)
        
        # RSI smoothed by EMA-9 (rsi_ema)
        rsi_series = self._calculate_rsi_series(close, 14)
        rsi_ema = rsi_series.ewm(span=9, adjust=False).mean().iloc[-1]
        rsi_ema = round(rsi_ema, 2) if not pd.isna(rsi_ema) else rsi_14
        
        # MACD
        macd_line, signal_line, histogram = self._calculate_macd(close)
        
        # ATR
        atr = self._calculate_atr(high, low, close, 14)
        price_for_pct = current_price if current_price > 0 else close.iloc[-1]
        atr_percent = round((atr / price_for_pct) * 100, 4) if price_for_pct > 0 else 0
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger(close, 20, 2)
        
        # Volume analysis
        avg_volume = volume.rolling(window=20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Recent high/low (last 20 candles = ~100 minutes of 5m)
        lookback = min(20, len(df))
        recent_high = high.iloc[-lookback:].max()
        recent_low = low.iloc[-lookback:].min()
        
        return {
            # Scalping EMAs (primary for fast signals)
            "ema_9": round(ema_9, 8),
            "ema_21": round(ema_21, 8),
            "ema_55": round(ema_55, 8),
            # Standard EMAs
            "ema_20": round(ema_20, 8),
            "ema_50": round(ema_50, 8),
            "ema_200": round(ema_200, 8),
            # RSI
            "rsi_7": round(rsi_7, 2),
            "rsi_14": round(rsi_14, 2),
            "rsi_ema": rsi_ema,           # RSI smoothed by EMA-9
            # MACD
            "macd": {
                "macd_line": round(macd_line, 8),
                "signal_line": round(signal_line, 8),
                "histogram": round(histogram, 8)
            },
            # ATR & Volatility
            "atr_14": round(atr, 8),
            "atr_percent": atr_percent,   # ATR as % of price
            # Bollinger
            "bollinger": {
                "upper": round(bb_upper, 8),
                "middle": round(bb_middle, 8),
                "lower": round(bb_lower, 8)
            },
            # Volume
            "volume_ratio": round(volume_ratio, 2),
            # Price range (from 5m candles)
            "recent_high": round(recent_high, 8),   # 20-bar high
            "recent_low": round(recent_low, 8),     # 20-bar low
            # Distance from EMAs
            "dist_ema20_pct": round((close.iloc[-1] - ema_20) / ema_20 * 100, 4),
            "dist_ema200_pct": round((close.iloc[-1] - ema_200) / ema_200 * 100, 4)
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI — returns single value"""
        series = self._calculate_rsi_series(prices, period)
        return series.iloc[-1] if not pd.isna(series.iloc[-1]) else 50
    
    def _calculate_rsi_series(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI — returns full series (for rsi_ema smoothing)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD"""
        ema_12 = prices.ewm(span=12, adjust=False).mean()
        ema_26 = prices.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
    
    def _calculate_bollinger(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper.iloc[-1], middle.iloc[-1], lower.iloc[-1]
    
    def _determine_signals(self, indicators: Dict, price: float) -> Dict:
        """Determine trend and momentum signals"""
        ema_20 = indicators['ema_20']
        ema_50 = indicators['ema_50']
        ema_200 = indicators['ema_200']
        rsi = indicators['rsi_14']
        macd_hist = indicators['macd']['histogram']
        
        # Trend based on EMA alignment
        if price > ema_20 > ema_50 > ema_200:
            trend = "STRONG_BULLISH"
        elif price > ema_20 and price > ema_200:
            trend = "BULLISH"
        elif price < ema_20 < ema_50 < ema_200:
            trend = "STRONG_BEARISH"
        elif price < ema_20 and price < ema_200:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        # Momentum based on RSI and MACD
        if rsi > 70:
            momentum = "OVERBOUGHT"
        elif rsi < 30:
            momentum = "OVERSOLD"
        elif rsi > 55 and macd_hist > 0:
            momentum = "BULLISH"
        elif rsi < 45 and macd_hist < 0:
            momentum = "BEARISH"
        else:
            momentum = "NEUTRAL"
        
        # Volatility
        bb_width = (indicators['bollinger']['upper'] - indicators['bollinger']['lower']) / indicators['bollinger']['middle']
        if bb_width > 0.1:
            volatility = "HIGH"
        elif bb_width < 0.03:
            volatility = "LOW"
        else:
            volatility = "MEDIUM"
        
        return {
            "trend": trend,
            "momentum": momentum,
            "volatility": volatility
        }
    
    def _calculate_score(self, indicators: Dict, signals: Dict) -> int:
        """Calculate overall technical score (0-100)"""
        score = 50  # Base score
        
        # Trend contribution (±20)
        trend_scores = {
            "STRONG_BULLISH": 20,
            "BULLISH": 10,
            "NEUTRAL": 0,
            "BEARISH": -10,
            "STRONG_BEARISH": -20
        }
        score += trend_scores.get(signals['trend'], 0)
        
        # Momentum contribution (±15)
        momentum_scores = {
            "BULLISH": 15,
            "OVERBOUGHT": 5,
            "NEUTRAL": 0,
            "OVERSOLD": -5,
            "BEARISH": -15
        }
        score += momentum_scores.get(signals['momentum'], 0)
        
        # Volume contribution (±10)
        volume_ratio = indicators['volume_ratio']
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 1.0:
            score += 5
        elif volume_ratio < 0.5:
            score -= 5
        
        # MACD contribution (±5)
        if indicators['macd']['histogram'] > 0:
            score += 5
        else:
            score -= 5
        
        # Clamp to 0-100
        return max(0, min(100, score))
    
    def _get_interest_level(self, score: int) -> str:
        """Get interest level from score"""
        if score >= 80:
            return "HIGH"
        elif score >= 60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_narrative(self, symbol: str, price: float, indicators: Dict, signals: Dict, score: int) -> str:
        """Generate human-readable narrative"""
        trend = signals['trend'].replace('_', ' ').title()
        momentum = signals['momentum']
        rsi = indicators['rsi_14']
        
        parts = [
            f"Trend: {trend}",
            f"Price ${price:,.2f}",
            f"RSI {rsi:.1f}",
            f"Score: {score}/100"
        ]
        
        prefix = "⭐ SIGNAL" if score >= 70 else "• watch"
        return f"{prefix} | {' | '.join(parts)}"


# Test function
def test_processor():
    """Test the processor"""
    # Sample data
    sample_data = {
        "coins": [{
            "symbol": "BTCUSDT",
            "price": 70000.0,
            "ohlcv_5m": [
                {"t": "2024-01-01T00:00:00Z", "o": 69900, "h": 70100, "l": 69800, "c": 70000, "v": 100}
                for _ in range(200)
            ]
        }]
    }
    
    processor = TechnicalProcessor()
    result = processor.process(sample_data)
    print(f"\n{'='*50}")
    print("Technical Processor Test")
    print(f"{'='*50}")
    for coin in result['coins']:
        print(f"{coin['symbol']}: {coin['narrative']}")


if __name__ == "__main__":
    test_processor()
