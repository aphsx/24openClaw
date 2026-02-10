# 🧠 AI Decision Logic — Scalping Mode

## Core Principle: TREND CONVICTION + FAST EXITS

ไม่ตัดสินใจจากกำไร/ขาดทุนอย่างเดียว แต่ใช้ Trend Alignment + Momentum (RSI-7) + EMA-9

---

## Position Decision Tree (20x Leverage)

```
┌─────────────────────────────────────────────────────────┐
│                   EXISTING POSITION                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. PnL ≤ -3%?                                          │
│     → CLOSE (Hard stop — 20x ห้ามเกินนี้)               │
│                                                          │
│  2. PnL < -1% + Trend AGAINST?                          │
│     → CLOSE (ตัดก่อนเสียเยอะ)                            │
│                                                          │
│  3. PnL < 0 + Price < EMA-9 (for long)?                 │
│     → CLOSE (ราคาหลุด fast EMA)                          │
│                                                          │
│  4. PnL ≥ +5%?                                          │
│     → CLOSE (เป้าหมายถึง)                                │
│                                                          │
│  5. PnL ≥ +2% + RSI-7 > 75 (long) or < 25 (short)?     │
│     → CLOSE (กำไร + momentum อ่อน)                       │
│                                                          │
│  6. PnL ≥ +1.5% + Trend AGAINST?                        │
│     → CLOSE (กำไรน้อยแต่ trend เปลี่ยน)                  │
│                                                          │
│  7. PnL > -2% + Trend ALIGNED + EMA-9 OK?               │
│     → HOLD (ขาดทุนเล็กน้อย แต่ทิศทางถูก)                │
│                                                          │
│  8. Default                                              │
│     → HOLD (รอสัญญาณชัด)                                 │
└─────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│                  NEW ENTRY CRITERIA                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Combined Score ≥ 65 (55% tech + 25% sent + 20% OC) │
│  2. Signal Alignment: 2/3 sources agree (BULLISH/BEARISH)│
│  3. RSI-7 between 25-75 (don't chase extremes)          │
│  4. Volume Ratio > 1.0 (volume confirmation)            │
│  5. Funding Rate check:                                  │
│     - FR > 0.05% = crowded longs (careful with LONG)    │
│     - FR < -0.05% = crowded shorts (careful with SHORT) │
│  6. Market outlook matches trade direction               │
│  7. Available positions < MAX_POSITIONS                   │
│                                                          │
│  PREFER: Pullback entries near EMA-9/EMA-21              │
│  AVOID: RSI-7 extreme + low volume + mixed signals       │
└─────────────────────────────────────────────────────────┘
```

## AI Authority

AI มีอำนาจเต็มที่ในการ:
- **เปิดหลาย positions** พร้อมกัน (ถ้ามั่นใจ)
- **ปิด positions** เมื่อเห็น exit signal
- **ตัดสินใจเอง** — ลด/เพิ่ม margin, เลือก leverage
- **ปฏิเสธ entry** แม้ score สูง ถ้า risk ไม่ดี

## Data Available to AI

| Data | Source | Usage |
|------|--------|-------|
| Price + OHLCV (1m/5m/1h) | Binance | Trend, Support/Resistance |
| EMA-9, EMA-21, EMA-55 | Technical | Fast trend for scalping |
| RSI-7, RSI-14 | Technical | Momentum/Overbought |
| MACD + Histogram | Technical | Trend confirmation |
| Bollinger Bands | Technical | Volatility |
| ATR-14 | Technical | Stop loss sizing |
| Volume Ratio | Technical | Confirmation strength |
| Funding Rate | Binance Futures | Position cost / crowding |
| Long/Short Ratio | Binance Futures | Market sentiment |
| News Headlines | RSS + Scraping | Market narrative |
| Fear & Greed Index | Alternative.me | Market mood |
| CoinGecko metrics | CoinGecko | Market cap, volume |

## Fallback Rules (When AI Unavailable)

ถ้า AI ทั้ง primary + backup ล้มเหลว — ใช้ rule-based:
1. Stop loss at config `-STOP_LOSS_PERCENT` → CLOSE
2. Take profit at config `+TAKE_PROFIT_PERCENT` → CLOSE
3. Profit + RSI-7 extreme → CLOSE
4. Loss + trend against → CLOSE
5. Loss + price below EMA-9 → CLOSE
6. Best opportunity with score ≥ `MIN_ENTRY_SCORE` + RSI OK → OPEN
