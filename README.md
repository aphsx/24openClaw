# 🤖 ClawBot AI — Automated Crypto Scalper

AI-powered crypto scalping bot for Binance Futures. Uses free tools only.

## Architecture

```
Collect (parallel) → Process → Aggregate → AI Decision → Execute → Notify
  ├── Binance API     ├── Technical    ├── Combined   ├── Groq (FREE)  ├── Binance  ├── Telegram
  │   (price, OHLCV,  │   Indicators   │   Scoring    │   Claude       │   Futures
  │   funding rate,    │   (RSI-7/14,   │   (55% tech  │   Kimi         │
  │   L/S ratio)       │   EMA-9/21/55  │   25% sent   │   Fallback     │
  ├── News RSS+Scrape  │   MACD, BB,    │   20% onch)  │
  │   (12+ sources,    │   ATR, Vol)    │
  │   anti-blocking)   │
  └── On-Chain         └── Sentiment
      (Fear & Greed,       (AI-analyzed)
      CoinGecko)
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url> && cd 24openClaw
cp .env.example .env
# Edit .env with your keys

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run
python main.py
```

## Free Stack (ค่าใช้จ่าย $0)

| Component | Provider | Cost |
|-----------|----------|------|
| Price Data | Binance API | FREE |
| News | RSS + Web Scraping | FREE |
| AI Brain | Groq (Llama 3.1-70B) | FREE |
| Database | Supabase (500MB) | FREE |
| Notifications | Telegram Bot | FREE |
| On-Chain | CoinGecko + Alternative.me | FREE |

## Scalping Settings

- **Cycle**: Every 2 minutes
- **Leverage**: 20x
- **Stop Loss**: -3%
- **Take Profit**: +5%
- **Max Positions**: 3 (configurable)
- **Strategy**: Trend + Momentum alignment with fast EMAs

## Docs

| Document | Description |
|----------|-------------|
| [WORKFLOW](docs/WORKFLOW.md) | Trading cycle flow |
| [DATA_SOURCES](docs/DATA_SOURCES.md) | All free data sources |
| [AI_DECISION_LOGIC](docs/AI_DECISION_LOGIC.md) | Decision framework |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | VPS setup guide |
| [NEWS_SCRAPING](docs/NEWS_SCRAPING.md) | Scraping guide & recommendations |
| [DATABASE_SCHEMA](docs/DATABASE_SCHEMA.md) | Database tables |

## Config

See `.env.example` for all available settings.
