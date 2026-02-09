# 🔄 Trading Bot Workflow

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    5-MINUTE CYCLE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PHASE 1: COLLECT          PHASE 2: PROCESS                │
│   ┌─────────────┐          ┌─────────────┐                  │
│   │ Binance API │──────────│ Technical   │                  │
│   │ (Price/OHLCV)│          │ Processor   │                  │
│   └─────────────┘          └──────┬──────┘                  │
│                                   │                          │
│   ┌─────────────┐          ┌──────▼──────┐                  │
│   │ News (RSS)  │──────────│ Sentiment   │                  │
│   │             │          │ Processor   │                  │
│   └─────────────┘          └──────┬──────┘                  │
│                                   │                          │
│   ┌─────────────┐          ┌──────▼──────┐                  │
│   │ On-Chain    │──────────│ Aggregator  │                  │
│   │ (CoinGecko) │          │             │                  │
│   └─────────────┘          └──────┬──────┘                  │
│                                   │                          │
│              PHASE 3: DECIDE      │      PHASE 4: EXECUTE   │
│              ┌────────────────────▼────┐  ┌───────────────┐ │
│              │      AI BRAIN           ├──│ Binance Trade │ │
│              │  (Claude / Kimi)        │  │   Executor    │ │
│              └────────────────────┬────┘  └───────┬───────┘ │
│                                   │               │         │
│              PHASE 5: STORE       │               │         │
│              ┌────────────────────▼───────────────▼───────┐ │
│              │              SUPABASE DATABASE              │ │
│              │  (cycles, decisions, trades, logs)          │ │
│              └─────────────────────────────────────────────┘ │
│                                                              │
│              PHASE 6: NOTIFY                                 │
│              ┌─────────────────────────────────────────────┐ │
│              │              TELEGRAM BOT                    │ │
│              │  (trade alerts, cycle summary)               │ │
│              └─────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase Details

### PHASE 1: Data Collection (Parallel)

```python
# All collectors run in parallel
binance_data, news_data, onchain_data = await asyncio.gather(
    binance_collector.collect(),
    news_collector.collect(),
    onchain_collector.collect()
)
```

| Collector | Source | Data |
|-----------|--------|------|
| Binance | Binance REST API | Price, OHLCV (5m/1h), Order Book |
| News | RSS Feeds | Headlines, Summaries |
| On-Chain | CoinGecko, Alternative.me | Fear/Greed, Market Cap |

---

### PHASE 2: Data Processing

```python
# Sequential processing
technical_data = technical_processor.process(binance_data)
sentiment_data = await sentiment_processor.process(news_data)
aggregated = aggregator.aggregate(technical, sentiment, onchain)
```

| Processor | Input | Output |
|-----------|-------|--------|
| Technical | OHLCV | EMA, RSI, MACD, ATR, BB, Score (0-100) |
| Sentiment | News Headlines | Sentiment Score (0-100), Label |
| Aggregator | All Data | Unified format for AI |

---

### PHASE 3: AI Decision

```
INPUT: Aggregated market data + Current positions + Account balance

AI ANALYZES:
1. Existing positions → HOLD / CLOSE decision
2. Market opportunities → OPEN_LONG / OPEN_SHORT signals

OUTPUT: JSON with decisions array
```

**Decision Logic (Trend-Conviction):**
```
IF position.pnl < 0 AND trend ALIGNED → HOLD (ถูกทาง รอกลับ)
IF position.pnl < 0 AND trend AGAINST → CLOSE (ตัดขาดทุน)
IF position.pnl > 10% AND momentum WEAK → CLOSE (เก็บกำไร)
IF no position AND score >= 70 → OPEN (เปิด position ใหม่)
```

---

### PHASE 4: Trade Execution

```python
for decision in decisions:
    if decision.action in ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE']:
        result = await trader.execute_decision(decision)
```

---

### PHASE 5: Database Storage

All data is stored in Supabase for:
- Historical analysis
- Performance tracking
- Debugging

---

### PHASE 6: Notifications

Telegram notifications for:
- Trade executions (OPEN/CLOSE)
- Cycle summaries
- Errors

---

## Timing

```
00:00  ─┬─ Cycle Start
        │   └── Phase 1: Collect (3-5s)
00:05  ─┤   └── Phase 2: Process (1-2s)
        │   └── Phase 3: AI Decision (2-5s)
00:12  ─┤   └── Phase 4: Execute (1-2s)
        │   └── Phase 5: Store (0.5s)
00:15  ─┴─ Cycle End
        │
04:45  ─── Wait for next cycle
        │
05:00  ─── Next Cycle Start
```

Total cycle time: ~15-20 seconds
Wait time: ~280 seconds
