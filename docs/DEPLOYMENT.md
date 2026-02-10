# 🚀 Deployment Guide — VPS 2-Core / 8GB RAM

## Requirements

- VPS: 2 cores, 8GB RAM, 40GB SSD
- Ubuntu 22.04 LTS recommended
- Python 3.11+
- Node.js 20+ (for PM2)

---

## Step 1: VPS Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install PM2
sudo npm install -g pm2
```

## Step 2: Clone & Configure

```bash
# Clone
git clone <your-repo-url> ~/clawbot
cd ~/clawbot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (Chromium only, save space)
playwright install chromium
playwright install-deps chromium

# Configure
cp .env.example .env
nano .env  # Fill in your API keys
```

## Step 3: Create Directories

```bash
mkdir -p logs data/raw data/processed
```

## Step 4: Test Run

```bash
# Activate venv
source ~/clawbot/venv/bin/activate

# Test single cycle
python main.py
# Wait for first cycle to complete, then Ctrl+C
```

## Step 5: Production with PM2

```bash
# Start
pm2 start ecosystem.config.js

# Monitor
pm2 monit       # Real-time monitoring
pm2 logs         # View logs
pm2 status       # Check status

# Auto-restart on reboot
pm2 startup
pm2 save
```

## Step 6: Monitoring

```bash
# Check memory usage (should be < 2GB normally)
pm2 monit

# Check logs
pm2 logs clawbot-ai --lines 50

# Restart if needed
pm2 restart clawbot-ai
```

---

## Memory Management

| Component | Estimated RAM |
|-----------|--------------|
| Python bot (no Playwright) | ~100-200MB |
| Playwright Chromium | ~200-400MB |
| **Total active** | **~300-600MB** |
| OS + other services | ~1-2GB |
| **Available headroom** | **~5-6GB** |

- PM2 will auto-restart if exceeds 1GB (`max_memory_restart: '1G'`)
- Playwright browser instance is reused (not spawned each cycle)
- `gc.collect()` runs after each cycle
- Data cleanup runs every 24 hours (deletes raw data > 30 days)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| High memory | `pm2 restart clawbot-ai` |
| Playwright fails | `playwright install chromium` |
| Bot crashes on start | Check `.env` keys with `python -c "from src.utils.config import config; config.validate()"` |
| No Telegram notifications | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` |
| News scraping blocked | Will auto-fallback to RSS; check logs for warnings |
