# 📋 ClawBot AI — Project Reference (รายละเอียดทั้งหมดเพื่อแก้ไขโค้ด)

> เอกสารนี้อธิบาย **ทุกส่วนของโปรแกรม** อย่างละเอียด — ใช้อ้างอิงเวลาแก้โค้ดหรือเพิ่มฟีเจอร์

---

## สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [โครงสร้างโฟลเดอร์](#2-โครงสร้างโฟลเดอร์)
3. [Data Flow ทั้ง Cycle](#3-data-flow-ทั้ง-cycle)
4. [รายละเอียดทุกไฟล์](#4-รายละเอียดทุกไฟล์)
5. [JSON Format (AI Input/Output)](#5-json-format)
6. [Supabase Database Schema](#6-supabase-database-schema)
7. [Configuration (.env)](#7-configuration)
8. [OpenClaw Skills](#8-openclaw-skills)
9. [Dependencies](#9-dependencies)
10. [Deployment & Cron](#10-deployment--cron)
11. [แก้ไขอะไร ดูตรงไหน](#11-แก้ไขอะไร-ดูตรงไหน)

---

## 1. ภาพรวมระบบ

**ClawBot AI** = Crypto Scalping Bot สำหรับ Binance Futures 20x Leverage

- เทรดทุก 5 นาที (cron) → loop ต้องจบใน <30 วินาที
- ทำกำไรได้ทั้ง **ขาขึ้น (LONG)** และ **ขาลง (SHORT)**
- **Python code = เครื่องมือ** ดึงข้อมูล + execute orders
- **OpenClaw AI = สมอง** วิเคราะห์ข้อมูลทั้งหมด → ตัดสินใจเทรด
- เหรียญ 8 ตัวหลัก: BTC, ETH, SOL, BNB, XRP, DOGE, AVAX, LINK
- ดึงข้อมูล 3 กราฟ (5m/15m/1h) + 12 indicators + 20 ข่าว + Fear & Greed

### หลักการสำคัญ:
1. **ข้อมูลเก็บใน RAM** (Python dict) — ไม่เขียนไฟล์ JSON ลง disk ระหว่าง loop
2. **PARALLEL fetch** — กราฟ + ข่าว + market data ดึงพร้อมกัน 3 ทาง
3. **Safety SL/TP** — ตั้ง SL -8% / TP +15% ไว้กัน 5 นาทีที่ bot ไม่ทำงาน
4. **AI ตัดสินทุก loop** — ไม่ fix ว่าต้องปิดที่กี่ %, ดูสถานการณ์จริง
5. **Supabase insert อย่างเดียว** — async หลังจบ loop, ไม่ read ระหว่าง loop

---

## 2. โครงสร้างโฟลเดอร์

```
24openClaw/
├── main.py                          # 🚀 Entry point (cron runs this)
├── requirements.txt                 # 📦 Dependencies
├── .env.example                     # 🔑 Config template
├── .env                             # 🔒 Config จริง (gitignore)
├── supabase_schema.sql              # 🗄️ SQL สร้าง table ใน Supabase
├── data/
│   └── cycle_state.json             # เลข cycle ล่าสุด (auto-generated)
├── logs/
│   └── clawbot.log                  # Log file (auto-rotated 10MB)
├── docs/
│   ├── ARCHITECTURE.md              # Architecture overview
│   └── PROJECT_REFERENCE.md         # ไฟล์นี้
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                        # 🔄 Main Orchestrator
│   │   ├── __init__.py
│   │   └── engine.py                # Engine class — จัดการ workflow ทั้งหมด
│   │
│   ├── data/                        # 📊 Data Fetching
│   │   ├── __init__.py
│   │   ├── binance_rest.py          # Binance Futures API (self-written, HMAC)
│   │   ├── candle_store.py          # เก็บ candle data (pandas DataFrame)
│   │   └── news_fetcher.py          # ข่าว 6 แหล่ง + Fear & Greed
│   │
│   ├── strategy/                    # 📈 Analysis
│   │   ├── __init__.py
│   │   ├── indicators.py            # 12 Technical Indicators
│   │   └── regime.py                # Market Regime Detection
│   │
│   ├── ai/                          # 🤖 AI Brain
│   │   ├── __init__.py
│   │   ├── brain.py                 # AI client (Groq/DeepSeek/Gemini/Claude/Kimi)
│   │   └── prompts.py              # System prompt + Cycle prompt builder
│   │
│   ├── execution/                   # 💰 Order Execution
│   │   ├── __init__.py
│   │   ├── order_manager.py         # เปิด/ปิด orders + safety SL/TP
│   │   └── position_tracker.py      # ติดตาม positions + ตรวจ SL/TP trigger
│   │
│   ├── database/                    # 💾 Database
│   │   ├── __init__.py
│   │   └── repository.py            # Supabase async insert
│   │
│   └── utils/                       # 🔧 Utilities
│       ├── __init__.py
│       ├── config.py                # Pydantic Settings (อ่านจาก .env)
│       ├── logger.py                # Loguru logger
│       ├── cache.py                 # In-memory cycle cache
│       └── notifier.py              # Telegram + Discord
│
├── .agent/skills/                   # 🛠️ OpenClaw Skills (6 ตัว)
│   ├── clawbot-market-data/SKILL.md
│   ├── clawbot-news/SKILL.md
│   ├── clawbot-account/SKILL.md
│   ├── clawbot-execute/SKILL.md
│   ├── clawbot-risk/SKILL.md
│   └── clawbot-notify/SKILL.md
│
└── tests/                           # 🧪 Tests (TODO)
```

---

## 3. Data Flow ทั้ง Cycle

### ลำดับการทำงาน (ต้องจบใน <30s):

```
CRON ทุก 5 นาที
    │
    ▼
main.py → asyncio.run(main())
    │
    ▼
Engine.run_cycle()
    │
    ├── STEP 1: Account Check (~200ms)
    │   ├── PositionTracker.update()
    │   │   ├── BinanceREST.get_positions()     → positions ปัจจุบัน
    │   │   ├── BinanceREST.get_account()        → balance, available_margin
    │   │   └── เปรียบเทียบกับ positions รอบก่อน
    │   │       └── ถ้าหายไป → BinanceREST.get_trades() + get_all_orders()
    │   │           → หาว่า SL/TP trigger ไหม → บันทึก PnL, fee
    │   └── เก็บลง cache.positions, cache.balance
    │
    ├── STEP 2-4: PARALLEL ──────────────────────────
    │   │
    │   ├── STEP 2: Charts (~2-5s)
    │   │   ├── BinanceREST.get_klines(symbol, "5m", 200)   x8 coins
    │   │   ├── BinanceREST.get_klines(symbol, "15m", 100)  x8 coins
    │   │   └── BinanceREST.get_klines(symbol, "1h", 48)    x8 coins
    │   │   └── CandleStore.store() → pandas DataFrame ใน RAM
    │   │
    │   ├── STEP 3: News (~1-15s, async)
    │   │   ├── CryptoPanic API (REST + key)
    │   │   ├── free-crypto-news API (REST, no key)
    │   │   ├── CoinDesk RSS
    │   │   ├── CoinTelegraph RSS
    │   │   ├── Binance Blog RSS
    │   │   └── → deduplicate → sort by time → top 20 → cache.news
    │   │
    │   └── STEP 4: Market Data (~500ms)
    │       ├── BinanceREST.get_funding_rate(symbol)        x8
    │       ├── BinanceREST.get_long_short_ratio(symbol)    x8
    │       ├── BinanceREST.get_ticker_24h(symbol)          x8
    │       └── FearGreedFetcher.fetch()                    x1
    │       └── → cache.funding_rates, cache.fear_greed
    │
    ├── STEP 5: ถ้าข่าวช้า >5s → refresh กราฟใหม่ (แทนที่ Data เก่า)
    │
    ├── Calculate Indicators (~200ms)
    │   ├── indicators.calculate_all(df) → dict ของ 12 indicators
    │   │   (ทำกับ 8 coins x 3 TF = 24 DataFrames)
    │   └── regime.detect_regime(indicators_5m) → "trending_up" etc.
    │   └── → cache.indicators[symbol][tf], cache.regimes[symbol]
    │
    ├── STEP 6: AI Decision (~2-10s)
    │   ├── cache.build_ai_input(risk_config) → สร้าง JSON ยักษ์
    │   ├── prompts.build_cycle_prompt(ai_input) → format เป็น text
    │   ├── AIBrain.decide() → httpx POST ไป AI API
    │   │   ├── ส่ง: System Prompt + Cycle Prompt
    │   │   └── รับ: JSON {"analysis": "...", "actions": [...]}
    │   └── → cache.ai_actions, cache.ai_model, cache.ai_latency_ms
    │
    ├── STEP 7: Execute Orders (~500ms)
    │   ├── OrderManager.execute_actions(actions, balance)
    │   │   ├── OPEN_LONG/OPEN_SHORT:
    │   │   │   ├── set_leverage(symbol, 20)
    │   │   │   ├── set_margin_type("ISOLATED")
    │   │   │   ├── คำนวณ quantity = (margin × leverage) / price
    │   │   │   ├── place_order(MARKET)
    │   │   │   └── place_order(STOP_MARKET) + place_order(TAKE_PROFIT_MARKET)
    │   │   │       ↑ Safety SL/TP กัน 5 นาทีที่ไม่ทำงาน
    │   │   └── CLOSE:
    │   │       ├── cancel_all_orders(symbol)  ← ยกเลิก SL/TP เก่า
    │   │       └── place_order(MARKET, reduce_only=True)
    │   └── → cache.executed_trades
    │
    └── STEP 8: Save + Notify (~200ms, async)
        ├── Repository.save_all(cache) → Supabase INSERT
        │   ├── INSERT INTO cycles
        │   ├── INSERT INTO cycle_raw_data (indicators, news, market)
        │   ├── INSERT INTO ai_decisions (prompt, response)
        │   └── INSERT INTO trades (orders, PnL, commission)
        └── Notifier.notify_trade() → Telegram + Discord
```

### ข้อมูลเก็บที่ไหน?

| ข้อมูล | ระหว่าง loop | หลัง loop |
|--------|-------------|-----------|
| Candles (กราฟ) | `CandleStore._candles` (pandas DataFrame ใน RAM) | cycle_raw_data table |
| Indicators | `cache.indicators` (Python dict ใน RAM) | cycle_raw_data table |
| News | `cache.news` (Python list ใน RAM) | cycle_raw_data table |
| Positions | `cache.positions` (Python list ใน RAM) | cycle_raw_data table |
| AI Input/Output | `cache.ai_input_json` (Python dict ใน RAM) | ai_decisions table |
| Trades | `cache.executed_trades` (Python list ใน RAM) | trades table |
| Balance | `cache.balance` (float ใน RAM) | cycles table |

---

## 4. รายละเอียดทุกไฟล์

### 4.1 `main.py` — Entry Point

```
asyncio.run(main()) → Engine().run_cycle(cycle_number, dry_run)
```
- อ่านเลข cycle จาก `data/cycle_state.json` → +1 ทุกรอบ
- `--dry-run` → ไม่ execute orders จริง
- `--cycle N` → override เลข cycle

---

### 4.2 `src/utils/config.py` — Settings

**Class**: `Settings(BaseSettings)` — Pydantic อ่านจาก `.env`

| Property | Type | Default | ใช้ตรงไหน |
|----------|------|---------|----------|
| `BINANCE_API_KEY` | str | "" | binance_rest.py |
| `BINANCE_API_SECRET` | str | "" | binance_rest.py (HMAC sign) |
| `BINANCE_TESTNET` | bool | True | เลือก URL testnet/live |
| `AI_PROVIDER` | str | "groq" | brain.py เลือก AI |
| `AI_MODEL` | str | "llama-3.3-70b-versatile" | brain.py ชื่อ model |
| `AI_API_KEY` | str | "" | brain.py auth |
| `LEVERAGE` | int | 20 | order_manager.py |
| `TRADING_SYMBOLS` | str | "BTCUSDT,..." | engine.py symbols_list |
| `SAFETY_SL_PCT` | float | 8.0 | order_manager.py (กัน crash) |
| `SAFETY_TP_PCT` | float | 15.0 | order_manager.py (กัน spike) |

**Method สำคัญ**:
- `settings.get_risk_pct(balance)` → return % risk ตาม balance tier
- `settings.symbols_list` → return list ของ symbols
- `settings.binance_base_url` → return URL ตาม testnet/live

**Singleton**: `settings = Settings()` — import จากที่ไหนก็ได้

---

### 4.3 `src/utils/cache.py` — Cycle Cache

**Class**: `CycleCache` — เก็บข้อมูลทั้ง cycle ใน RAM

**Fields หลัก**:
```python
cache.balance          # float: USDT balance
cache.positions        # list[dict]: positions ปัจจุบัน
cache.closed_between_cycles  # list[dict]: positions ที่ปิดระหว่าง 5 นาที
cache.indicators       # {symbol: {tf: {ind: val}}} — indicators ทุก coin ทุก TF
cache.regimes          # {symbol: "trending_up"} — market regime
cache.news             # list[dict]: 20 ข่าวล่าสุด
cache.fear_greed       # {"value": 68, "label": "Greed"}
cache.ai_input_json    # dict — JSON ที่ส่ง AI
cache.ai_output_json   # dict — JSON ที่ AI ตอบ
cache.ai_actions       # list[dict] — actions ที่ AI สั่ง
cache.executed_trades  # list[dict] — trades ที่ execute แล้ว
```

**Methods**:
- `cache.reset()` → clear ข้อมูลเริ่ม cycle ใหม่
- `cache.build_ai_input(risk_config)` → สร้าง JSON ยักษ์ส่ง AI
- `cache.to_supabase_cycle()` → แปลงเป็น row สำหรับ INSERT cycles

---

### 4.4 `src/data/binance_rest.py` — Binance API

**Class**: `BinanceREST` — Self-written HMAC-SHA256 client

**ไม่ใช้ ccxt หรือ python-binance** → เขียนเองทั้งหมด

**Public endpoints** (ไม่ต้อง sign):
| Method | Binance Path | ใช้ทำอะไร |
|--------|-------------|----------|
| `get_klines(symbol, interval, limit)` | `/fapi/v1/klines` | ดึงกราฟ candle |
| `get_ticker_price(symbol)` | `/fapi/v1/ticker/price` | ราคาปัจจุบัน |
| `get_ticker_24h(symbol)` | `/fapi/v1/ticker/24hr` | Volume, % change |
| `get_funding_rate(symbol)` | `/fapi/v1/fundingRate` | Funding rate |
| `get_long_short_ratio(symbol)` | `/futures/data/globalLongShortAccountRatio` | L/S ratio |
| `get_top_movers()` | `/fapi/v1/ticker/24hr` | Top movers (dynamic discovery) |

**Signed endpoints** (ต้อง HMAC sign):
| Method | Binance Path | ใช้ทำอะไร |
|--------|-------------|----------|
| `get_account()` | `/fapi/v2/account` | Balance + positions |
| `get_positions()` | `/fapi/v2/positionRisk` | Open positions |
| `get_trades(symbol, limit)` | `/fapi/v1/userTrades` | Recent fills (PnL, fee) |
| `get_all_orders(symbol, limit)` | `/fapi/v1/allOrders` | Order history |
| `set_leverage(symbol, leverage)` | `/fapi/v1/leverage` | ตั้ง leverage |
| `place_order(...)` | `/fapi/v1/order` | วาง order |
| `cancel_all_orders(symbol)` | `/fapi/v1/allOpenOrders` | ยกเลิก SL/TP เก่า |

**HMAC Signing** (`_sign` method):
```python
params["timestamp"] = int(time.time() * 1000)
query = urlencode(params)
signature = hmac.new(secret, query, sha256).hexdigest()
params["signature"] = signature
```

---

### 4.5 `src/data/candle_store.py` — Candle Storage

**Class**: `CandleStore` — เก็บ candles เป็น pandas DataFrame

- `store(symbol, tf, raw_klines)` → แปลง list[list] จาก Binance → DataFrame
- `get(symbol, tf)` → return DataFrame
- `get_latest_price(symbol)` → return float (close ล่าสุด 5m)
- `refresh_latest(symbol, tf, raw_klines)` → แทนที่ข้อมูลเก่าเลย (ตอนข่าวช้า)

**DataFrame columns**: open_time, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume

---

### 4.6 `src/data/news_fetcher.py` — ข่าว + Sentiment

**Classes**: `NewsFetcher`, `FearGreedFetcher`

**NewsFetcher.fetch_all()** → ดึดข่าวจาก 6 sources:
1. CryptoPanic API (REST, free key)
2. free-crypto-news API (REST, no key)
3. CoinDesk RSS → XML parse
4. CoinTelegraph RSS → XML parse
5. Binance Blog RSS → XML parse

**ขั้นตอน**: ดึง parallel → deduplicate (ตัดหัวข้อซ้ำ) → sort by time → top 20

**FearGreedFetcher.fetch()** → `{"value": 68, "label": "Greed"}`
- Source: https://api.alternative.me/fng/
- 0=Extreme Fear, 50=Neutral, 100=Extreme Greed

---

### 4.7 `src/strategy/indicators.py` — 12 Indicators

**Function**: `calculate_all(df: DataFrame) → dict`

ต้องมี candles อย่างน้อย 55 แท่ง

| # | Indicator | Function | Output Key |
|---|-----------|----------|-----------|
| 1 | EMA 9 | `_ema(close, 9)` | `ema9` |
| 2 | EMA 21 | `_ema(close, 21)` | `ema21` |
| 3 | EMA 55 | `_ema(close, 55)` | `ema55` |
| 4 | EMA 200 | `_ema(close, 200)` (ถ้า ≥200 แท่ง) | `ema200` |
| 5 | RSI 14 | `_rsi(close, 14)` | `rsi14` (0-100) |
| 6 | MACD | `_macd(close, 12, 26, 9)` | `macd.line, .signal, .histogram` |
| 7 | Bollinger | `_bollinger_bands(close, 20, 2)` | `bb.upper, .mid, .lower, .width` |
| 8 | ATR 14 | `_atr(high, low, close, 14)` | `atr14` ($), `atr14_pct` (%) |
| 9 | VWAP | `_vwap(df)` | `vwap` |
| 10 | ADX | `_adx(high, low, close, 14)` | `adx` (0-100) |
| 11 | Stoch RSI | `_stochastic_rsi(close)` | `stoch_rsi_k, stoch_rsi_d` (0-100) |
| 12 | OBV | `_obv(close, volume)` | `obv`, `obv_trend` ("rising"/"falling") |
| 13 | Supertrend | `_supertrend(high, low, close, 10, 3)` | `supertrend.value, .direction` |
| 14 | Vol Ratio | `current_vol / avg(20)` | `volume_ratio` |

---

### 4.8 `src/strategy/regime.py` — Market Regime

**Function**: `detect_regime(indicators: dict) → str`

| Regime | Condition | ความหมาย |
|--------|-----------|----------|
| `"trending_up"` | ADX>25 + EMA9>21>55 + Supertrend up | ตลาดขาขึ้นชัด |
| `"trending_down"` | ADX>25 + EMA9<21<55 + Supertrend down | ตลาดขาลงชัด |
| `"ranging"` | ADX<20 ± BB width แคบ | ตลาดเดี่ยง ไม่มี trend |
| `"volatile"` | ATR% > 1.5% | ตลาดผันผวนสูง |

---

### 4.9 `src/ai/prompts.py` — AI Prompts

**`SYSTEM_PROMPT`**: กฎการเทรดถาวร (ส่งทุก call) — Thai/English
- กฎ LONG/SHORT, SL/TP ตามสถานการณ์, counter-trend check
- format JSON output ที่ต้องตอบ

**`build_cycle_prompt(ai_input)`**: สร้าง prompt ใหม่ทุก cycle
- Format: account → positions → coins (8 x 3TF indicators) → news 20 → Fear & Greed
- ส่งเป็น text ยาวให้ AI อ่าน → AI ตอบ JSON

---

### 4.10 `src/ai/brain.py` — AI Client

**Class**: `AIBrain` — รองรับ 5 providers

| Provider | Endpoint | Auth | API Format |
|----------|----------|------|-----------|
| Groq | `api.groq.com/openai/v1/...` | Bearer | OpenAI-compatible |
| DeepSeek | `api.deepseek.com/v1/...` | Bearer | OpenAI-compatible |
| Gemini | `generativelanguage.googleapis.com/...` | Bearer | OpenAI-compatible |
| Kimi | `api.moonshot.cn/v1/...` | Bearer | OpenAI-compatible |
| Claude | `api.anthropic.com/v1/messages` | x-api-key | Anthropic Messages |

**Methods**:
- `decide(ai_input)` → ส่ง JSON → AI → parse response → `{"analysis": "...", "actions": [...]}`
- `_parse_response(raw)` → พยายาม parse JSON, ถ้าไม่ได้ → ดึงจาก markdown code block
- `_estimate_cost(usage)` → คำนวณค่า API ($USD)

**Fallback**: ถ้า AI ล่ม → ใช้ AI_FALLBACK_PROVIDER → ถ้ายังล่ม → return `{"actions": []}` (HOLD all)

---

### 4.11 `src/execution/order_manager.py` — Execute Orders

**Class**: `OrderManager`

**`execute_actions(actions, balance)`**:
- loop ทุก action จาก AI
- OPEN_LONG / OPEN_SHORT:
  1. `set_leverage(symbol, 20)`
  2. `set_margin_type("ISOLATED")`
  3. คำนวณ quantity: `(margin * 20) / price`
  4. `place_order(MARKET)`
  5. `place_order(STOP_MARKET, stop_price=sl)` ← Safety SL
  6. `place_order(TAKE_PROFIT_MARKET, stop_price=tp)` ← Safety TP
- CLOSE:
  1. `cancel_all_orders(symbol)` ← ยกเลิก SL/TP เก่า
  2. `place_order(MARKET, reduce_only=True)`
  3. คำนวณ PnL: `(exit - entry) * qty` (LONG) หรือ `(entry - exit) * qty` (SHORT)

**Safety SL/TP**:
```
LONG:  SL = entry × (1 - 8%) = entry × 0.92
       TP = entry × (1 + 15%) = entry × 1.15
SHORT: SL = entry × (1 + 8%) = entry × 1.08
       TP = entry × (1 - 15%) = entry × 0.85
```

---

### 4.12 `src/execution/position_tracker.py` — Position Tracking

**Class**: `PositionTracker`

**`update()`** → return `(positions, closed_between, balance, available)`

**ตรวจ SL/TP triggered**:
1. เทียบ positions ปัจจุบัน กับ `_last_positions` (รอบก่อน)
2. ถ้าเหรียญหายไป → ถูกปิดระหว่างรอบ
3. ดึง `get_trades(symbol)` → หา PnL, commission
4. ดึง `get_all_orders(symbol)` → หาว่าปิดด้วย STOP_MARKET หรือ TAKE_PROFIT_MARKET
5. Return: `{"symbol": "ETHUSDT", "closed_by": "STOP_LOSS", "realized_pnl": -2.10}`

---

### 4.13 `src/database/repository.py` — Supabase

**Class**: `Repository`

**`save_all(cache)`** — ถูกเรียกหลัง cycle จบ:
1. `INSERT cycles` → ได้ cycle_id
2. `INSERT cycle_raw_data` → indicators ทุก coin ทุก TF + news + fear_greed + positions
3. `INSERT ai_decisions` → prompt/response JSON ทั้งก้อน
4. `INSERT trades` → ทุก order ที่ execute

---

### 4.14 `src/utils/notifier.py` — Notifications

**`send(message)`** → ส่งไป Telegram + Discord พร้อมกัน
**`notify_trade(trade)`** → format: emoji + symbol + side + PnL + reason
**`notify_cycle_summary(cycle_data)`** → balance + actions + duration

---

### 4.15 `src/core/engine.py` — Main Orchestrator

**Class**: `Engine` — จัดการ workflow ทั้งหมด

**ดู Section 3 (Data Flow)** สำหรับรายละเอียดแต่ละ step

---

## 5. JSON Format

### AI Input (Code → AI) — ส่งทุก cycle

```json
{
  "cycle_id": "c_20260211_0100",
  "timestamp": "2026-02-11T01:00:00Z",
  "account": {
    "balance_usdt": 150.42,
    "available_margin": 120.00,
    "positions": [
      {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": 97500,
        "current_price": 98200,
        "quantity": 0.002,
        "margin_usdt": 10,
        "leverage": 20,
        "unrealized_pnl": 1.44,
        "unrealized_pnl_pct": 14.4,
        "safety_sl_price": 89700,
        "safety_tp_price": 112125
      }
    ],
    "closed_since_last_cycle": [
      {
        "symbol": "ETHUSDT",
        "side": "SHORT",
        "closed_by": "STOP_LOSS",
        "realized_pnl": -2.10,
        "commission": 0.08
      }
    ]
  },
  "coins": {
    "BTCUSDT": {
      "price": 98200,
      "indicators_5m": {
        "ema9": 98150, "ema21": 97900, "ema55": 97500,
        "rsi14": 65, "stoch_rsi_k": 72, "stoch_rsi_d": 68,
        "macd": {"line": 120, "signal": 95, "histogram": 25},
        "bb": {"upper": 98800, "mid": 97700, "lower": 96600, "width": 0.022},
        "atr14": 350, "atr14_pct": 0.36,
        "adx": 32, "vwap": 97800,
        "obv": 125000, "obv_trend": "rising",
        "supertrend": {"value": 97200, "direction": "up"},
        "volume_ratio": 1.3
      },
      "indicators_15m": {"ema9": 98000, "ema21": 97700, "rsi14": 60, "adx": 28, "macd_histogram": 50},
      "indicators_1h": {"ema9": 97800, "ema21": 97500, "ema200": 95000, "rsi14": 58, "supertrend_dir": "up"},
      "regime": "trending_up",
      "funding_rate": 0.0001,
      "long_short_ratio": 1.25,
      "volume_24h_usdt": 1500000000,
      "price_change_5m_pct": 0.15,
      "price_change_1h_pct": 0.8,
      "price_change_24h_pct": 2.3
    }
  },
  "news": [{"title": "Bitcoin ETF $500M inflow", "source": "CoinDesk", "timestamp": "2026-02-11T00:45:00Z", "url": "..."}],
  "fear_greed": {"value": 68, "label": "Greed"},
  "risk_config": {"balance_tier": "$100-300", "suggested_risk_pct": "7", "min_order_usdt": 5}
}
```

### AI Output (AI → Code)

```json
{
  "analysis": "ตลาด bullish BTC trend ชัด ADX 32 EMA stacked...",
  "actions": [
    {"symbol": "BTCUSDT", "action": "HOLD", "reason": "กำไร 14.4% RSI 65 ยังไม่ overbought ถือต่อ"},
    {"symbol": "ETHUSDT", "action": "OPEN_LONG", "margin_usdt": 12, "confidence": 78, "reason": "EMA cross + MACD bullish"},
    {"symbol": "SOLUSDT", "action": "SKIP", "reason": "ranging ADX 15 ไม่มี signal ชัด"}
  ]
}
```

**Action types**: `OPEN_LONG`, `OPEN_SHORT`, `CLOSE`, `HOLD`, `SKIP`

---

## 6. Supabase Database Schema

### ER Diagram
```
cycles (1) ──→ (N) cycle_raw_data
cycles (1) ──→ (1) ai_decisions
cycles (1) ──→ (N) trades

daily_summary (standalone, 1 row per day)
```

### `cycles` — 1 row = 1 cycle (ทุก 5 นาที)
| Column | Type | ดูอะไรได้ |
|--------|------|----------|
| cycle_number | BIGINT | เลขรอบที่เท่าไหร่ |
| started_at | TIMESTAMPTZ | เริ่มเมื่อไหร่ |
| duration_ms | INT | ใช้เวลากี่ ms |
| balance_usdt | DECIMAL | Balance ตอนเริ่ม |
| actions_taken | INT | AI สั่งกี่ actions |
| sl_tp_triggered | INT | มี SL/TP trigger ระหว่างรอบไหม |
| ai_model | TEXT | ใช้ AI model อะไร |
| ai_latency_ms | INT | AI ตอบนานกี่ ms |
| fear_greed_value | INT | Fear & Greed ตอนนั้น |

### `cycle_raw_data` — ข้อมูลดิบทุก cycle
- data_type: `indicators_5m`, `indicators_15m`, `indicators_1h`, `news`, `fear_greed`, `positions`
- raw_json: JSONB ข้อมูลดิบทั้งก้อน

### `ai_decisions` — AI คิดอะไร
- input_json: **JSON ทั้งก้อน** ที่ส่ง AI (ดูย้อนหลังได้)
- output_json: **JSON ที่ AI ตอบ** (ดูว่าตัดสินใจยังไง)
- analysis_text: สรุปวิเคราะห์

### `trades` — ทุก order
- binance_order_id: order ID จาก Binance
- realized_pnl + commission: PnL จริงจาก Binance API
- closed_by: `AI` / `STOP_LOSS` / `TAKE_PROFIT`
- ai_confidence + ai_reason: ทำไม AI ถึงเทรด
- cycle_id: **มาจาก cycle ไหน** → link กลับไปดูข้อมูลตอนนั้น

---

## 7. Configuration (.env)

ดู `.env.example` สำหรับทุก setting — key ทุกตัวตรงกับ `src/utils/config.py`

**เปลี่ยน AI Model**: แก้ `AI_PROVIDER` + `AI_MODEL` + `AI_API_KEY` ใน .env → ไม่ต้องแก้โค้ด

**เปลี่ยนเหรียญ**: แก้ `TRADING_SYMBOLS=BTCUSDT,ETHUSDT,...` ใน .env

**เปลี่ยน Risk**: แก้ `RISK_TIER_*` หรือ `SAFETY_SL_PCT` / `SAFETY_TP_PCT`

---

## 8. OpenClaw Skills (6 ตัว)

| Skill | ใช้ตอนไหน | ไฟล์ที่เกี่ยว |
|-------|----------|-------------|
| `clawbot-market-data` | ดึงกราฟ + คำนวณ indicators | `binance_rest.py`, `candle_store.py`, `indicators.py` |
| `clawbot-news` | ดึงข่าว + Fear & Greed | `news_fetcher.py` |
| `clawbot-account` | ดึง balance + ตรวจ positions | `position_tracker.py`, `binance_rest.py` |
| `clawbot-execute` | execute orders + safety SL/TP | `order_manager.py`, `binance_rest.py` |
| `clawbot-risk` | คำนวณ position size | `config.py` (get_risk_pct) |
| `clawbot-notify` | ส่ง alert Telegram/Discord | `notifier.py` |

---

## 9. Dependencies

| Package | Version | ใช้ตรงไหน |
|---------|---------|----------|
| `pandas` | ≥2.0 | candle_store.py, indicators.py |
| `numpy` | ≥1.24 | indicators.py |
| `pydantic` | ≥2.0 | config.py |
| `pydantic-settings` | ≥2.0 | config.py |
| `aiohttp` | ≥3.9 | binance_rest.py, news_fetcher.py, notifier.py |
| `httpx` | ≥0.25 | brain.py (AI calls) |
| `supabase` | ≥2.0 | repository.py |
| `loguru` | ≥0.7 | logger.py |
| `python-dotenv` | ≥1.0 | config.py (.env loading) |

**ไม่ใช้**: ccxt, python-binance, ta, ta-lib, playwright, beautifulsoup4

---

## 10. Deployment & Cron

### VPS Setup
```bash
# Install Python 3.11+
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
nano .env  # ใส่ API keys

# Create Supabase tables
# Copy supabase_schema.sql → Supabase SQL Editor → Run

# Test
python main.py --dry-run

# Setup Cron (ทุก 5 นาที)
crontab -e
*/5 * * * * cd /path/24openClaw && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

---

## 11. แก้ไขอะไร ดูตรงไหน

| อยากแก้ | ไปแก้ไฟล์ |
|---------|----------|
| เพิ่ม/ลด เหรียญ | `.env` → `TRADING_SYMBOLS` |
| เปลี่ยน AI model | `.env` → `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` |
| เปลี่ยน leverage | `.env` → `LEVERAGE` |
| เพิ่ม indicator ใหม่ | `src/strategy/indicators.py` → เพิ่มใน `calculate_all()` |
| แก้ AI prompt | `src/ai/prompts.py` → `SYSTEM_PROMPT` หรือ `build_cycle_prompt()` |
| เพิ่ม news source | `src/data/news_fetcher.py` → เพิ่มใน `RSS_FEEDS` dict |
| แก้ risk % | `.env` → `RISK_TIER_*` |
| แก้ safety SL/TP | `.env` → `SAFETY_SL_PCT`, `SAFETY_TP_PCT` |
| เพิ่ม notification channel | `src/utils/notifier.py` → เพิ่ม method ใหม่ |
| แก้ DB schema | `supabase_schema.sql` + `src/database/repository.py` |
| เพิ่ม timeframe | `.env` → TF settings + `engine.py` → `_fetch_all_charts` |
| แก้ regime detection | `src/strategy/regime.py` → `detect_regime()` |
| Debug cycle flow | `src/core/engine.py` → `run_cycle()` |
