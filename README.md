# JARVIS v5 - AI Trading Bot

## 🚀 Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure .env
copy .env.example .env
# Edit .env with your API keys

# 4. Run
python main.py
```

## 📁 Project Structure

```
jarvis_v5/
├── src/
│   ├── collectors/     # BOT Layer - Data collection
│   ├── processors/     # Transform Layer - Data processing
│   ├── brain/          # AI Layer - Decision making
│   ├── executor/       # Trade Layer - Order execution
│   ├── database/       # Data Layer - Supabase
│   └── utils/          # Utilities
├── data/               # Temp data storage
├── logs/               # Log files
├── tests/              # Test cases
└── main.py             # Entry point
```

## 🤖 AI Models

- **Claude 3** (Anthropic) - Primary decision engine
- **Kimi** (Moonshot AI) - Backup/validation

## 📊 Coins Tracked

BTC, ETH, BNB, SOL, XRP, ADA, DOGE, AVAX, DOT, LINK

## ⚙️ Configuration

See `.env.example` for all required environment variables.
