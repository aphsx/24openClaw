# 🚀 Deployment Guide

## Prerequisites

- VPS with 8GB RAM, 2 cores
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

---

## Step 2: Clone/Upload Project

```bash
# Create directory
mkdir -p ~/jarvis-v5
cd ~/jarvis-v5

# Upload your project files (via SFTP or git)
# scp -r C:\Users\aphis\Desktop\24\* user@vps:~/jarvis-v5/
```

---

## Step 3: Setup Virtual Environment

```bash
cd ~/jarvis-v5

# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (if needed)
playwright install chromium
```

---

## Step 4: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required values:
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
ANTHROPIC_API_KEY=your_key (or GROQ_API_KEY)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Step 5: Setup Database

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Go to SQL Editor
4. Paste contents of `supabase_schema.sql`
5. Run

---

## Step 6: Test Run

```bash
# Activate venv
source venv/bin/activate

# Test run
python main.py
```

Check for:
- ✅ No import errors
- ✅ Binance connection OK
- ✅ AI API working
- ✅ Telegram notifications received

---

## Step 7: Start with PM2

```bash
# Start bot
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs jarvis-v5

# Set to auto-start on boot
pm2 startup
pm2 save
```

---

## PM2 Commands

```bash
pm2 status          # Check status
pm2 logs jarvis-v5  # View logs
pm2 restart jarvis-v5  # Restart
pm2 stop jarvis-v5  # Stop
pm2 delete jarvis-v5   # Remove
```

---

## Monitoring

### Real-time Logs
```bash
pm2 logs jarvis-v5 --lines 100
```

### Log Files
```bash
tail -f ~/jarvis-v5/logs/jarvis_*.log
```

### Supabase Dashboard
- Go to supabase.com → Your project → Table Editor

---

## Troubleshooting

### Bot Not Starting
```bash
# Check Python path
which python3.11

# Check venv activated
source venv/bin/activate

# Run manually to see errors
python main.py
```

### No Telegram Notifications
```bash
# Test bot token
curl https://api.telegram.org/bot<TOKEN>/getMe
```

### API Errors
```bash
# Check environment variables
cat .env | grep -v '#'
```

---

## Security Tips

1. **Never share `.env` file**
2. **Use firewall**: `sudo ufw enable`
3. **SSH key only**: Disable password auth
4. **Regular updates**: `sudo apt update && upgrade`
