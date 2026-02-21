# 🤖 ClawBot AI — Crypto Scalping Bot

> tradingclaw AI-powered scalping bot for Binance Futures
> Profit in **both bull and bear** markets | 20x leverage | 5-minute cycles

## ⚡ Quick Start

```bash
# 1. Clone & install
git clone <repo-url>
cd 24tradingclaw
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Setup database (optional)
# Run supabase_schema.sql in Supabase SQL Editor

# 4. Test run
python main.py --dry-run

# 5. Live (cron every 5 min)
# */5 * * * * cd /path/24tradingclaw && python main.py
```

## 🏗️ Architecture

```
Cron (5min) → Engine → Parallel Data Fetch → Indicators → AI Decision → Execute → Save
```

- **AI Brain**: Groq / DeepSeek / Gemini / Claude / Kimi (configurable)
- **Data**: Self-written Binance REST API (HMAC-SHA256)
- **Indicators**: 12 technical indicators (EMA, RSI, MACD, BB, ATR, VWAP, ADX, StochRSI, OBV, Supertrend)
- **News**: 6 free sources (CryptoPanic, CoinDesk, CoinTelegraph, Binance Blog)
- **Risk**: Dynamic position sizing based on balance tier + safety SL/TP

📖 Full docs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📦 Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Exchange | Binance Futures REST (self-written) |
| AI | Groq/DeepSeek/Gemini/Claude/Kimi |
| Indicators | pandas + numpy (self-written) |
| Database | Supabase (PostgreSQL) |
| Notifications | Telegram + Discord |
| Logging | Loguru |

## 🔒 Security

- No external exchange libraries (self-written HMAC-signed API)
- API keys stored in `.env` (gitignored)
- Minimal trusted dependencies only
- Testnet mode by default

## 📄 License

MIT
