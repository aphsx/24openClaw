# 🏗️ ClawBot AI — Architecture Documentation

## Overview

ClawBot AI เป็น crypto scalping bot สำหรับ Binance Futures ที่ใช้ **OpenClaw AI เป็นสมองตัดสินใจ**
Python code เป็นเครื่องมือดึงข้อมูล + execute orders | AI วิเคราะห์และสั่งเทรด

```
┌──────────┐
│  Cron    │ ทุก 5 นาที
│  main.py │
└────┬─────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│                  Engine (Orchestrator)            │
│                  src/core/engine.py               │
├──────────────────────────────────────────────────┤
│                                                  │
│  Step 1: Account Check                           │
│  ├── PositionTracker → ดึง balance + positions   │
│  └── ตรวจ SL/TP triggered ระหว่างรอบ            │
│                                                  │
│  Step 2-4: PARALLEL Data Fetch                   │
│  ├── BinanceREST → Candles 3TF x 8 coins        │
│  ├── NewsFetcher → 20 ข่าว (6 sources)           │
│  └── MarketData → Funding, L/S, Fear&Greed       │
│                                                  │
│  Step 5: Calculate                               │
│  ├── Indicators → 12 TA indicators               │
│  └── Regime → trending/ranging/volatile           │
│                                                  │
│  Step 6: AI Decision                             │
│  └── AIBrain → JSON input → AI → JSON output     │
│                                                  │
│  Step 7: Execute                                 │
│  ├── OrderManager → open/close orders             │
│  └── Safety SL/TP → กัน flash crash              │
│                                                  │
│  Step 8: Save + Notify (async)                   │
│  ├── Repository → Supabase insert                 │
│  └── Notifier → Telegram + Discord               │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Project Structure

```
24openClaw/
├── main.py                      # Entry point (cron)
├── requirements.txt             # Minimal dependencies
├── .env.example                 # Environment config template
├── supabase_schema.sql          # Database schema
├── data/                        # Runtime data (cycle state)
├── logs/                        # Log files (rotated)
├── docs/
│   └── ARCHITECTURE.md          # This file
├── src/
│   ├── core/
│   │   └── engine.py            # Main loop orchestrator
│   ├── data/
│   │   ├── binance_rest.py      # Self-written Binance Futures API (HMAC)
│   │   ├── candle_store.py      # Multi-TF candle management
│   │   └── news_fetcher.py      # News + Fear & Greed
│   ├── strategy/
│   │   ├── indicators.py        # 12 technical indicators (self-written)
│   │   └── regime.py            # Market regime detection
│   ├── ai/
│   │   ├── brain.py             # Multi-provider AI client
│   │   └── prompts.py           # System + cycle prompt templates
│   ├── execution/
│   │   ├── order_manager.py     # Execute orders + safety SL/TP
│   │   └── position_tracker.py  # Track positions + detect SL/TP triggers
│   ├── database/
│   │   └── repository.py        # Async Supabase insert
│   └── utils/
│       ├── config.py            # Pydantic settings from .env
│       ├── logger.py            # Loguru logging
│       ├── cache.py             # In-memory cycle cache (Python dict)
│       └── notifier.py          # Telegram + Discord
└── tests/
```

---

## Data Flow (Per Cycle)

```
API Responses (JSON) → Python dict (RAM) → Indicators → AI Input JSON → AI API → AI Output JSON → Execute → Supabase (async)
```

1. **Fetch**: Binance REST → raw JSON → store as Python dicts in RAM
2. **Process**: Calculate indicators on pandas DataFrames → add to cache dict
3. **AI**: Convert cache dict → JSON string → send to AI API → parse response JSON
4. **Execute**: Read AI actions dict → place Binance orders → record results
5. **Save**: After cycle done → async insert entire cache to Supabase

> ❗ NO disk I/O during cycle. NO Supabase reads during cycle. All in-memory.

---

## AI Provider Support

| Provider | Endpoint | Auth | Format |
|----------|----------|------|--------|
| Groq | OpenAI-compatible | Bearer token | JSON mode |
| DeepSeek | OpenAI-compatible | Bearer token | JSON mode |
| Gemini | OpenAI-compatible | Bearer token | JSON mode |
| Kimi | OpenAI-compatible | Bearer token | JSON mode |
| Claude | Anthropic API | x-api-key | Messages API |

All configured via `.env` — change `AI_PROVIDER` and `AI_MODEL` to switch.

---

## Technical Indicators (12)

| Indicator | Implementation | Purpose |
|-----------|---------------|---------|
| EMA 9/21/55 | `ewm(span=N)` | Trend + crossover |
| RSI 14 | Wilder's smoothing | Overbought/oversold |
| MACD (12,26,9) | EMA difference | Momentum |
| Bollinger Bands (20,2) | SMA ± 2σ | Volatility bands |
| ATR 14 | True Range EMA | Volatility $ |
| VWAP | Cum(TP×Vol)/Cum(Vol) | Institutional level |
| ADX 14 | DI+/DI- smoothed | Trend strength |
| Stochastic RSI | RSI of RSI | Fast reversal |
| OBV | Signed volume cumulative | Volume divergence |
| Supertrend (10,3) | ATR-based trend line | Trend direction |
| Volume Ratio | Current/Avg(20) | Volume spike |
| EMA 200 (1h) | Long-term EMA | Major trend |

---

## Risk Management

| Balance | Risk/Trade | Safety SL | Safety TP |
|---------|-----------|-----------|-----------|
| <$50 | 20% | -8% | +15% |
| $50-100 | 10% | -8% | +15% |
| $100-300 | 7% | -8% | +15% |
| $300-1000 | 4% | -8% | +15% |
| >$1000 | 2.5% | -8% | +15% |

Safety SL/TP เป็น fallback เท่านั้น — AI ตัดสินใจปิดก่อนถึง SL/TP ทุก 5 นาที

---

## Database Schema (Supabase)

```
cycles ──┬── cycle_raw_data (indicators, news, market data)
         ├── ai_decisions (prompt, response, actions)
         └── trades (orders, PnL, Binance order IDs)

daily_summary (aggregated per day)
```

ดูย้อนหลัง: cycle → ข้อมูลดิบ + AI คิดอะไร → ผลเทรด → **รู้ว่าแพ้ชนะเพราะอะไร**

---

## Security

- **Self-written Binance API** — HMAC-SHA256 signed, no external exchange libraries
- **API keys in .env** — never committed to git (in .gitignore)
- **Minimal dependencies** — only trusted, well-known packages
- **No browser automation** — pure REST/RSS for data
- **Testnet first** — always test on Binance Testnet before live
