"""
ClawBot AI — Market Regime Detection
Classifies market as: trending_up, trending_down, ranging, volatile
"""
from typing import Dict
from src.utils.logger import log


def detect_regime(indicators: Dict) -> str:
    """
    Detect market regime from calculated indicators.
    
    Returns one of:
      - "trending_up"   : ADX > 25 + price above EMAs + Supertrend up
      - "trending_down" : ADX > 25 + price below EMAs + Supertrend down
      - "ranging"       : ADX < 20 + BB width narrow
      - "volatile"      : ATR spike > 2x normal (high volatility)
      - "unknown"       : insufficient data
    
    This tells AI which strategy is appropriate:
      - trending → follow the trend (momentum)
      - ranging → mean reversion (buy low, sell high within range)
      - volatile → reduce position size or skip
    """
    if not indicators:
        return "unknown"

    try:
        adx = indicators.get("adx", 0)
        atr_pct = indicators.get("atr14_pct", 0)
        bb = indicators.get("bb", {})
        bb_width = bb.get("width", 0)
        ema9 = indicators.get("ema9", 0)
        ema21 = indicators.get("ema21", 0)
        ema55 = indicators.get("ema55", 0)
        supertrend = indicators.get("supertrend", {})
        st_dir = supertrend.get("direction", "up")

        # Volatile: ATR% > 1.5% (high volatility for crypto)
        if atr_pct > 1.5:
            return "volatile"

        # Trending Up: ADX > 25 + EMAs stacked bullish + Supertrend up
        if adx > 25:
            if ema9 > ema21 > ema55 and st_dir == "up":
                return "trending_up"
            elif ema9 < ema21 < ema55 and st_dir == "down":
                return "trending_down"
            else:
                # Strong directional movement but EMAs not aligned
                return "trending_up" if st_dir == "up" else "trending_down"

        # Ranging: ADX < 20 + narrow BB
        if adx < 20 and bb_width < 0.03:
            return "ranging"

        # Default: mild ranging
        if adx < 20:
            return "ranging"

        # Between 20-25 ADX — weak trend, treat as ranging
        return "ranging"

    except Exception as e:
        log.error(f"Regime detection error: {e}")
        return "unknown"


def regime_description(regime: str) -> str:
    """Human-readable description for logging."""
    descriptions = {
        "trending_up": "📈 Trending Up (follow the trend, long bias)",
        "trending_down": "📉 Trending Down (follow the trend, short bias)",
        "ranging": "↔️ Ranging (mean reversion, buy low sell high)",
        "volatile": "⚡ Volatile (reduce size or skip)",
        "unknown": "❓ Unknown (insufficient data)",
    }
    return descriptions.get(regime, regime)
