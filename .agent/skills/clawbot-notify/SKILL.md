---
description: Send trade alerts and summaries to Telegram and Discord
---

# ClawBot Notify Skill

## Purpose
Send trade notifications, cycle summaries, and error alerts to Telegram and Discord.

## Usage
```python
from src.utils.notifier import Notifier

notifier = Notifier()

# Trade notification
await notifier.notify_trade(trade_dict)

# Cycle summary
await notifier.notify_cycle_summary(cycle_data)

# Error alert
await notifier.notify_error("Something went wrong")
```

## Notification Types

### Trade Opened
```
🟢 OPEN LONG BTCUSDT
💰 Entry: 97500
📦 Qty: 0.002
💵 Margin: 10 USDT
🎯 Leverage: 20x
🧠 Confidence: 85%
📝 EMA cross + MACD bullish
```

### Trade Closed
```
✅ CLOSE LONG BTCUSDT
💰 Entry: 97500 → Exit: 98200
📊 PnL: +1.44 USDT (+14.4%)
📝 RSI overbought, taking profit
```

### Error
```
🚨 ClawBot Error
Cycle #42: Connection timeout
```

## Config (.env)
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```
