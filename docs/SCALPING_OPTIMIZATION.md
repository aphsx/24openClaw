# ⚡ Short-Term Futures Trading Optimization

## Overview

ปรับระบบให้เหมาะกับ **Scalping/Short-term** บน Binance Futures
- Timeframe: 5 นาที
- Leverage: 20x
- ระยะถือ: นาที - ชั่วโมง

---

## 🔧 การปรับปรุงที่ต้องทำ

### 1. Speed Improvements

| Current | Recommended | Reason |
|---------|-------------|--------|
| REST API every 5 min | **WebSocket real-time** | ราคาไวขึ้น |
| OHLCV 5m + 1h | **OHLCV 1m + 5m** | เห็น micro-trend |
| 20 news articles | **10 articles** | ลดเวลา processing |

### 2. Technical Indicators for Scalping

| Current | Recommended | Reason |
|---------|-------------|--------|
| EMA 20, 50, 200 | **EMA 9, 21, 55** | ไวต่อ trend เร็วขึ้น |
| RSI 14 | **RSI 7 + RSI 14** | จับ overbought เร็วขึ้น |
| BB 20, 2 | **BB 20, 2** | เหมือนเดิม OK |
| MACD 12,26,9 | **MACD 8,17,9** | Faster crossover |

### 3. Risk Parameters for 20x

| Parameter | Current | Recommended 20x |
|-----------|---------|-----------------|
| Stop Loss | -15% | **-5%** (ที่ 20x = -100% ถ้าไม่ตัด) |
| Take Profit | +10% | **+3-5%** |
| Max Drawdown | - | **-3% per trade** |
| Max Positions | 3 | **2** (ลดความเสี่ยง) |

### 4. Entry/Exit Logic

**Current (Swing):**
```
Entry: Score >= 70, 2+ signals aligned
Exit: Trend reverse OR TP/SL hit
```

**Scalping:**
```
Entry: Score >= 65, momentum + volume spike
Exit: Quick TP (3-5%) OR tight SL (-3%)
```

---

## 📈 Short-Term Strategies ที่แนะนำ

### Strategy 1: EMA Crossover + Volume

```
BUY when:
  - EMA9 crosses above EMA21
  - Volume > 1.5x average
  - RSI < 70 (not overbought)

SELL when:
  - +3% profit OR -2% loss
  - OR EMA9 crosses below EMA21
```

**Win Rate:** ~55-60%
**Risk/Reward:** 1:1.5

---

### Strategy 2: RSI Divergence + Bollinger

```
BUY when:
  - Price touches lower BB
  - RSI < 30 (oversold)
  - Volume confirms

SELL when:
  - Price touches upper BB
  - OR RSI > 70
```

**Win Rate:** ~50-55%
**Risk/Reward:** 1:2

---

### Strategy 3: Momentum Breakout

```
BUY when:
  - Price breaks 15-min high
  - Volume > 2x average
  - MACD histogram increasing

SELL when:
  - +5% profit
  - OR momentum weakens (MACD crosses down)
```

**Win Rate:** ~45-50%
**Risk/Reward:** 1:2.5

---

## ⚠️ ข้อควรระวัง Futures 20x

### 1. Liquidation Price

```
LONG at $100, 20x leverage:
Liquidation ≈ $95 (-5%)  ❌ ระวัง!

แนะนำ: Stop Loss ที่ -3% เสมอ
```

### 2. Funding Rate

```
Binance Futures คิด Funding ทุก 8 ชม.
- Funding > 0.1% = ต้นทุน Long สูง
- Funding < -0.1% = ต้นทุน Short สูง

แนะนำ: เช็ค Funding Rate ก่อนเปิด position
```

### 3. Slippage

```
Market Order at 20x:
- Slippage 0.1% = กินกำไรไป 2%

แนะนำ: ใช้ Limit Order ถ้าเป็นไปได้
```

---

## 🔄 Code Changes Required

### 1. config.py - ปรับค่า

```python
# Risk parameters for 20x Scalping
DEFAULT_LEVERAGE = 20
DEFAULT_MARGIN = 10
MAX_POSITIONS = 2

# Tighter stops
STOP_LOSS_PERCENT = 3      # -3% max loss
TAKE_PROFIT_PERCENT = 5    # +5% target
TRAILING_STOP = True       # Enable trailing

# Faster cycle
CYCLE_INTERVAL_SECONDS = 60  # 1 นาที (optional)
```

### 2. technical_processor.py - ปรับ Indicators

```python
# Faster EMAs for scalping
"ema_9": self._calc_ema(df, 9),
"ema_21": self._calc_ema(df, 21),
"ema_55": self._calc_ema(df, 55),

# Faster RSI
"rsi_7": self._calc_rsi(df, 7),
"rsi_14": self._calc_rsi(df, 14),

# Faster MACD
"macd": self._calc_macd(df, fast=8, slow=17, signal=9),
```

### 3. binance_collector.py - เพิ่ม Funding Rate

```python
async def get_funding_rate(self, symbol: str) -> dict:
    url = f"{self.base_url}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": 1}
    # Returns current funding rate
```

### 4. position_analyzer.py - Tighter exits

```python
# Scalping exit rules
if pnl_pct >= 5:  # +5% = Take profit
    return "CLOSE", "Target reached"
    
if pnl_pct <= -3:  # -3% = Stop loss
    return "CLOSE", "Stop loss"
    
if momentum_weakening and pnl_pct > 2:  # +2% with weak momentum
    return "CLOSE", "Secure profit"
```

---

## 📊 Recommended Settings Summary

| Setting | Swing Trading | **Scalping (แนะนำ)** |
|---------|---------------|---------------------|
| Timeframe | 5m + 1h | **1m + 5m** |
| EMA | 20, 50, 200 | **9, 21, 55** |
| RSI | 14 | **7 + 14** |
| Leverage | 10-20x | **20x** |
| Stop Loss | -15% | **-3%** |
| Take Profit | +10% | **+5%** |
| Cycle | 5 min | **1-2 min** |
| Max Positions | 3 | **2** |
| Entry Score | >= 70 | **>= 65** |

---

## ⚡ Quick Implementation

ถ้าต้องการปรับเป็น Scalping:

```bash
# 1. แก้ไข .env
CYCLE_INTERVAL_SECONDS=120
DEFAULT_LEVERAGE=20
MAX_POSITIONS=2

# 2. ระบบจะปรับ:
# - Stop loss tighter (-3%)
# - Take profit faster (+5%)
# - Faster indicators
```

---

## 🎯 สรุป

**สำหรับ 5-min Scalping 20x:**

1. ✅ ระบบปัจจุบันใช้ได้
2. 🔧 ปรับ config (ค่าข้างบน)
3. ⚠️ ระวัง Stop Loss (-3% max)
4. 🎯 Target: +3-5% per trade

**ต้องการให้ปรับ code ให้เลยไหม?**
