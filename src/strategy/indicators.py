"""
ClawBot AI — Technical Indicators Engine (Self-Written)
All 12 indicators calculated using pandas/numpy only.
No external TA libraries.
"""
import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

from src.utils.logger import log


def calculate_all(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate all 12 indicators on a candle DataFrame.
    Returns dict of indicator values (latest values).
    """
    if df is None or len(df) < 55:
        log.warning("Not enough candles for indicators")
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    result = {}

    # 1-3. EMA 9, 21, 55
    result["ema9"] = round(float(_ema(close, 9).iloc[-1]), 4)
    result["ema21"] = round(float(_ema(close, 21).iloc[-1]), 4)
    result["ema55"] = round(float(_ema(close, 55).iloc[-1]), 4)

    # EMA 200 (for 1h TF — calculated if enough data)
    if len(df) >= 200:
        result["ema200"] = round(float(_ema(close, 200).iloc[-1]), 4)

    # 4. RSI 14
    result["rsi14"] = round(float(_rsi(close, 14).iloc[-1]), 2)

    # 5. MACD (12, 26, 9)
    macd_line, signal_line, histogram = _macd(close)
    result["macd"] = {
        "line": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
    }

    # 6. Bollinger Bands (20, 2)
    bb_upper, bb_mid, bb_lower = _bollinger_bands(close)
    bb_width = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_mid.iloc[-1] if bb_mid.iloc[-1] != 0 else 0
    result["bb"] = {
        "upper": round(float(bb_upper.iloc[-1]), 4),
        "mid": round(float(bb_mid.iloc[-1]), 4),
        "lower": round(float(bb_lower.iloc[-1]), 4),
        "width": round(float(bb_width), 4),
    }

    # 7. ATR 14
    atr = _atr(high, low, close, 14)
    atr_val = float(atr.iloc[-1])
    atr_pct = (atr_val / float(close.iloc[-1]) * 100) if float(close.iloc[-1]) != 0 else 0
    result["atr14"] = round(atr_val, 4)
    result["atr14_pct"] = round(atr_pct, 4)

    # 8. VWAP
    result["vwap"] = round(float(_vwap(df).iloc[-1]), 4)

    # 9. ADX
    result["adx"] = round(float(_adx(high, low, close, 14).iloc[-1]), 2)

    # 10. Stochastic RSI (14, 14, 3, 3)
    stoch_k, stoch_d = _stochastic_rsi(close)
    result["stoch_rsi_k"] = round(float(stoch_k.iloc[-1]) * 100, 2)
    result["stoch_rsi_d"] = round(float(stoch_d.iloc[-1]) * 100, 2)

    # 11. OBV
    obv = _obv(close, volume)
    result["obv"] = round(float(obv.iloc[-1]), 0)
    # OBV trend: compare last 5 values
    if len(obv) >= 5:
        result["obv_trend"] = "rising" if obv.iloc[-1] > obv.iloc[-5] else "falling"
    else:
        result["obv_trend"] = "neutral"

    # 12. Supertrend (ATR period=10, multiplier=3)
    st_val, st_dir = _supertrend(high, low, close)
    result["supertrend"] = {
        "value": round(float(st_val.iloc[-1]), 4),
        "direction": "up" if st_dir.iloc[-1] == 1 else "down",
    }

    # Volume ratio (current vs avg)
    avg_vol = volume.rolling(20).mean().iloc[-1]
    result["volume_ratio"] = round(float(volume.iloc[-1] / avg_vol), 2) if avg_vol > 0 else 1.0

    return result


# ==============================================================
# INDICATOR IMPLEMENTATIONS
# ==============================================================

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD (Moving Average Convergence Divergence)."""
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands."""
    mid = _sma(series, period)
    std = series.rolling(window=period).std()
    upper = mid + (std * std_dev)
    lower = mid - (std * std_dev)
    return upper, mid, lower


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    hl = high - low
    hc = (high - close.shift(1)).abs()
    lc = (low - close.shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol = (typical_price * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    atr = _atr(high, low, close, period)

    plus_di = 100 * _ema(plus_dm, period) / atr.replace(0, np.nan)
    minus_di = 100 * _ema(minus_dm, period) / atr.replace(0, np.nan)

    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = _ema(dx.fillna(0), period)
    return adx.fillna(0)


def _stochastic_rsi(
    series: pd.Series, rsi_period: int = 14, stoch_period: int = 14,
    smooth_k: int = 3, smooth_d: int = 3,
):
    """Stochastic RSI."""
    rsi = _rsi(series, rsi_period)
    stoch_rsi = (rsi - rsi.rolling(stoch_period).min()) / (
        rsi.rolling(stoch_period).max() - rsi.rolling(stoch_period).min()
    ).replace(0, np.nan)
    k = stoch_rsi.rolling(smooth_k).mean().fillna(0.5)
    d = k.rolling(smooth_d).mean().fillna(0.5)
    return k, d


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume."""
    direction = np.sign(close.diff()).fillna(0)
    obv = (direction * volume).cumsum()
    return obv


def _supertrend(
    high: pd.Series, low: pd.Series, close: pd.Series,
    period: int = 10, multiplier: float = 3.0,
):
    """
    Supertrend indicator.
    Returns (supertrend_value, direction) where direction=1 means up (bullish).
    """
    atr = _atr(high, low, close, period)
    hl2 = (high + low) / 2

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i - 1]) if direction.iloc[i - 1] == 1 else lower_band.iloc[i]
        else:
            supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i - 1]) if direction.iloc[i - 1] == -1 else upper_band.iloc[i]

    return supertrend, direction
