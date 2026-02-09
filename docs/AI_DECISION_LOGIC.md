# 🧠 AI Decision Logic

## Core Principle: TREND CONVICTION > PnL%

ไม่ตัดสินใจจากกำไร/ขาดทุน แต่ตัดสินจาก **Trend Alignment**

---

## Position Analysis Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│                   EXISTING POSITION                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────┐
            │   PnL <= -15% ?         │
            │   (Hard Stop Loss)      │
            └─────────────────────────┘
                   │YES        │NO
                   ▼           ▼
              ┌────────┐  ┌─────────────────────────┐
              │ CLOSE  │  │ Trend ALIGNED with      │
              │        │  │ position direction?     │
              └────────┘  └─────────────────────────┘
                              │YES           │NO
                              ▼              ▼
                    ┌──────────────┐  ┌──────────────┐
                    │ Is momentum  │  │    CLOSE     │
                    │  weakening?  │  │ (Cut loss)   │
                    └──────────────┘  └──────────────┘
                      │YES    │NO
                      ▼       ▼
               ┌──────────┐ ┌──────────┐
               │ PnL>10%? │ │  HOLD    │
               └──────────┘ │(มั่นใจ)  │
                 │YES  │NO  └──────────┘
                 ▼     ▼
           ┌────────┐ ┌────────┐
           │ CLOSE  │ │ HOLD   │
           │(เก็บ)  │ │(รอ)    │
           └────────┘ └────────┘
```

---

## Trend Alignment Check

```python
# LONG position
trend_aligned = (side == 'long' and 'BULLISH' in trend)
trend_against = (side == 'long' and 'BEARISH' in trend)

# SHORT position  
trend_aligned = (side == 'short' and 'BEARISH' in trend)
trend_against = (side == 'short' and 'BULLISH' in trend)
```

---

## Momentum Weakening Signals

```python
momentum_weakening = (
    (side == 'long' and rsi > 70) or   # Overbought
    (side == 'short' and rsi < 30) or  # Oversold
    volume_ratio < 0.5 or              # Volume dying
    score < 50                         # Losing conviction
)
```

---

## New Opportunity Criteria

```
┌─────────────────────────────────────────────────────────────┐
│              NEW OPPORTUNITY CHECK                           │
└─────────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
    ┌─────────────┐              ┌─────────────┐
    │ positions   │   AND        │ combined    │
    │ < max (3)   │              │ score >= 70 │
    └─────────────┘              └─────────────┘
           │                             │
           └──────────────┬──────────────┘
                          ▼
            ┌─────────────────────────┐
            │ 2+ signals ALIGNED?     │
            │ (tech + sent + onchain) │
            └─────────────────────────┘
                   │YES        │NO
                   ▼           ▼
    ┌─────────────────────┐  ┌────────────┐
    │ Check RSI extremes  │  │   SKIP     │
    └─────────────────────┘  └────────────┘
         │OK       │BAD
         ▼         ▼
    ┌─────────┐ ┌────────────┐
    │  OPEN   │ │   SKIP     │
    │ LONG or │ │(overbought/│
    │ SHORT   │ │ oversold)  │
    └─────────┘ └────────────┘
```

---

## Score Calculation

### Technical Score (0-100)

| Component | Weight | Bullish | Bearish |
|-----------|--------|---------|---------|
| Trend (EMA alignment) | ±20 | +20 | -20 |
| Momentum (RSI + MACD) | ±15 | +15 | -15 |
| Volume Ratio | ±10 | +10 if >1.5x | -5 if <0.5x |
| MACD Histogram | ±5 | +5 if >0 | -5 if <0 |

Base score: 50

### Combined Score

```python
combined = (
    technical_score * 0.5 +  # 50% weight
    sentiment_score * 0.3 +  # 30% weight
    onchain_score * 0.2      # 20% weight
)
```

---

## Decision Confidence

| Confidence | Meaning |
|------------|---------|
| 0.9+ | Very confident, strong signals |
| 0.7-0.9 | Confident, take action |
| 0.5-0.7 | Moderate, proceed with caution |
| <0.5 | Low confidence, may use fallback |
