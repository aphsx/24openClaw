---
description: Fetch market data (candles, indicators, regime) for all symbols across 3 timeframes
---

# ClawBot Market Data Skill

## Purpose
Fetch candlestick data from Binance Futures for 8 coins x 3 timeframes, calculate 12 technical indicators, and detect market regime.

## Steps

1. **Fetch Candles** (parallel for all symbols x TFs):
   ```python
   from src.data.binance_rest import BinanceREST
   client = BinanceREST()
   klines = await client.get_klines("BTCUSDT", "5m", 200)
   ```

2. **Store in CandleStore**:
   ```python
   from src.data.candle_store import CandleStore
   store = CandleStore()
   store.store("BTCUSDT", "5m", klines)
   ```

3. **Calculate Indicators**:
   ```python
   from src.strategy.indicators import calculate_all
   df = store.get("BTCUSDT", "5m")
   indicators = calculate_all(df)  # Returns dict with all 12 indicators
   ```

4. **Detect Regime**:
   ```python
   from src.strategy.regime import detect_regime
   regime = detect_regime(indicators)  # "trending_up" / "ranging" / "volatile"
   ```

## Timeframe Config
| TF | Candles | Coverage | Purpose |
|----|---------|----------|---------|
| 5m | 200 | ~16h | Entry/exit signals |
| 15m | 100 | ~25h | Medium trend |
| 1h | 48 | 2 days | Major trend |

## Indicators (12)
EMA(9,21,55), RSI(14), MACD(12,26,9), Bollinger Bands(20,2), ATR(14), VWAP, ADX(14), Stochastic RSI, OBV, Supertrend(10,3), Volume Ratio, EMA(200) on 1h
