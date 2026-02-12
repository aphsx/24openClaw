# 📊 Data Format Standardization — ClawBot AI

> ทุก data collector ต้อง return JSON format เดียวกัน เพื่อรวมกันง่าย

---

## 1. 📈 Market Data Collector (Binance)

**Input**: List of symbols, timeframes
**Output**:
```json
{
  "data_type": "market_data",
  "fetched_at": "2026-02-11T01:00:00Z",
  "coins": {
    "BTCUSDT": {
      "price": 98200,
      "indicators_5m": {
        "ema9": 98150,
        "ema21": 97900,
        "ema55": 97500,
        "rsi14": 65,
        "stoch_rsi_k": 72,
        "stoch_rsi_d": 68,
        "macd": {"line": 120, "signal": 95, "histogram": 25},
        "bb": {"upper": 98800, "mid": 97700, "lower": 96600, "width": 0.022},
        "atr14": 350,
        "atr14_pct": 0.36,
        "adx": 32,
        "vwap": 97800,
        "obv": 125000,
        "obv_trend": "rising",
        "supertrend": {"value": 97200, "direction": "up"},
        "volume_ratio": 1.3
      },
      "indicators_15m": { /* เหมือนกัน */ },
      "indicators_1h": { /* เหมือนกัน */ },
      "regime": "trending_up",
      "funding_rate": 0.0001,
      "long_short_ratio": 1.25,
      "volume_24h_usdt": 1500000000,
      "price_change_5m_pct": 0.15,
      "price_change_1h_pct": 0.8,
      "price_change_24h_pct": 2.3
    },
    "ETHUSDT": { /* ... */ }
  }
}
```

---

## 2. 📰 News Collector (Multi-Source)

**Input**: None (ดึง 20 ข่าวล่าสุด)
**Output**:
```json
{
  "data_type": "news",
  "fetched_at": "2026-02-11T01:00:05Z",
  "count": 20,
  "sources_used": ["telegram", "coingecko", "rss_coindesk", "cryptopanic"],
  "is_cached": false,
  "news": [
    {
      "id": "news_1",
      "title": "Bitcoin ETF sees $500M inflow",
      "source": "telegram:whale_alert",
      "timestamp": "2026-02-11T00:45:00Z",
      "url": "https://t.me/whale_alert/12345",
      "sentiment": "positive",
      "coins_mentioned": ["BTC"]
    },
    {
      "id": "news_2",
      "title": "Ethereum upgrade delayed",
      "source": "coingecko",
      "timestamp": "2026-02-11T00:40:00Z",
      "url": "https://www.coingecko.com/...",
      "sentiment": "neutral",
      "coins_mentioned": ["ETH"]
    }
  ]
}
```

**News Sources Priority:**
1. **Telegram** (เร็วที่สุด, real-time) - ใช้ Telethon
2. **CoinGecko API** (ข่าวคุณภาพดี)
3. **RSS Feeds** (backup, ไม่มี limit)
4. **CryptoPanic** (เสริม ถ้ายังใช้)

---

## 3. 🌡️ Market Sentiment Collector

**Input**: None
**Output**:
```json
{
  "data_type": "market_sentiment",
  "fetched_at": "2026-02-11T01:00:03Z",
  "fear_greed": {
    "value": 68,
    "label": "Greed",
    "source": "alternative.me"
  },
  "social_sentiment": {
    "twitter_sentiment": 0.65,
    "reddit_sentiment": 0.72,
    "source": "lunarcrush"
  }
}
```

---

## 4. 💼 Account State Collector (Binance)

**Input**: None
**Output**:
```json
{
  "data_type": "account",
  "fetched_at": "2026-02-11T01:00:01Z",
  "balance_usdt": 150.42,
  "available_margin": 120.00,
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "LONG",
      "binance_order_id": "12345678",
      "entry_price": 97500,
      "current_price": 98200,
      "quantity": 0.002,
      "margin_usdt": 10,
      "leverage": 20,
      "unrealized_pnl": 1.44,
      "unrealized_pnl_pct": 14.4,
      "hold_duration_min": 35,
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
      "commission": 0.08,
      "note": "SL triggered ระหว่างรอบ"
    }
  ]
}
```

---

## 🔄 Data Flow Architecture

```python
# main.py - Main orchestrator

async def main_cycle():
    cycle_id = f"c_{datetime.now().strftime('%Y%m%d_%H%M')}"

    # Step 1: Parallel fetch (ใช้ asyncio.gather)
    results = await asyncio.gather(
        fetch_account_data(),      # → account_data JSON
        fetch_market_data(),       # → market_data JSON
        fetch_news(),              # → news_data JSON
        fetch_market_sentiment()   # → sentiment_data JSON
    )

    account_data, market_data, news_data, sentiment_data = results

    # Step 2: Combine ทั้งหมดเป็น JSON ใหญ่
    combined_input = {
        "cycle_id": cycle_id,
        "timestamp": datetime.now().isoformat(),
        "account": account_data,
        "coins": market_data["coins"],
        "news": news_data["news"],
        "fear_greed": sentiment_data["fear_greed"],
        "risk_config": get_risk_config(account_data["balance_usdt"])
    }

    # Step 3: ส่ง AI
    ai_decision = await send_to_ai(combined_input)

    # Step 4: Execute
    await execute_orders(ai_decision["actions"])

    # Step 5: Save to Supabase (async, ไม่ block)
    asyncio.create_task(save_to_supabase(cycle_id, combined_input, ai_decision))
```

---

## 📝 News Fetcher Implementation

### แหล่งข่าวฟรีที่แนะนำ (เรียงตามความเร็ว):

| Source | วิธีใช้ | Rate Limit | Setup |
|--------|---------|-----------|-------|
| **Telegram** | Telethon | ไม่จำกัด | ต้องสร้าง Telegram App (ฟรี) |
| **CoinGecko** | REST API | 30 calls/min | ไม่ต้อง key (Demo mode) |
| **Messari** | REST API | 20 calls/min | ต้อง free API key |
| **LunarCrush** | REST API | 100/day | ต้อง free API key |
| **RSS Feeds** | feedparser | ไม่จำกัด | ไม่ต้อง setup |
| **CryptoPanic** | REST API | unlimited (ช้า) | ต้อง free API key |

### ตัวอย่าง Implementation:

```python
# src/data/news_fetcher.py

import asyncio
from telethon import TelegramClient
import feedparser
import aiohttp
from datetime import datetime

class NewsAggregator:
    def __init__(self):
        self.sources = {
            "telegram": TelegramNewsSource(),
            "coingecko": CoinGeckoNewsSource(),
            "rss": RSSNewsSource(),
            "cryptopanic": CryptoPanicSource()  # optional
        }

    async def fetch_news(self, target_count=20) -> dict:
        """ดึงข่าวจากหลายแหล่งพร้อมกัน"""

        # Parallel fetch
        results = await asyncio.gather(
            self.sources["telegram"].get_latest(limit=10),
            self.sources["coingecko"].get_latest(limit=5),
            self.sources["rss"].get_latest(limit=5),
            return_exceptions=True  # ถ้าแหล่งใดล้ม ไม่ fail ทั้งหมด
        )

        # รวมข่าวทั้งหมด
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)

        # Sort by timestamp (ใหม่สุดก่อน)
        all_news.sort(key=lambda x: x["timestamp"], reverse=True)

        # เอาแค่ 20 ข่าวล่าสุด + deduplicate
        unique_news = self._deduplicate(all_news[:target_count])

        return {
            "data_type": "news",
            "fetched_at": datetime.now().isoformat(),
            "count": len(unique_news),
            "sources_used": list(self.sources.keys()),
            "is_cached": False,
            "news": unique_news
        }

    def _deduplicate(self, news_list):
        """ลบข่าวซ้ำ (เช็คจาก title similarity)"""
        seen = set()
        unique = []
        for news in news_list:
            title_clean = news["title"].lower().strip()[:100]
            if title_clean not in seen:
                seen.add(title_clean)
                unique.append(news)
        return unique


# 1. Telegram Source (เร็วที่สุด, real-time)
class TelegramNewsSource:
    def __init__(self):
        self.channels = [
            "whale_alert",      # ข่าว whale movements
            "binance",          # Binance official
            "cointelegraph"     # CoinTelegraph
        ]
        # Get from https://my.telegram.org/apps
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.client = TelegramClient('clawbot_session', self.api_id, self.api_hash)

    async def get_latest(self, limit=10) -> list:
        """ดึงข้อความล่าสุดจาก Telegram channels"""
        await self.client.start()

        messages = []
        per_channel = limit // len(self.channels)

        for channel in self.channels:
            try:
                async for msg in self.client.iter_messages(channel, limit=per_channel):
                    if msg.text:
                        messages.append({
                            "id": f"tg_{msg.id}_{channel}",
                            "title": msg.text[:200],
                            "source": f"telegram:{channel}",
                            "timestamp": msg.date.isoformat(),
                            "url": f"https://t.me/{channel}/{msg.id}",
                            "coins_mentioned": self._extract_coins(msg.text)
                        })
            except Exception as e:
                print(f"Telegram channel {channel} failed: {e}")
                continue

        return messages[:limit]

    def _extract_coins(self, text: str) -> list:
        """หา coin symbols จาก text"""
        coins = []
        symbols = ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "AVAX", "LINK"]
        text_upper = text.upper()
        for coin in symbols:
            if coin in text_upper or f"${coin}" in text_upper:
                coins.append(coin)
        return list(set(coins))


# 2. CoinGecko Source (ข่าวคุณภาพดี)
class CoinGeckoNewsSource:
    async def get_latest(self, limit=5) -> list:
        """ดึงข่าวจาก CoinGecko (ไม่ต้อง API key)"""
        url = "https://api.coingecko.com/api/v3/news"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    return [
                        {
                            "id": f"cg_{item['id']}",
                            "title": item["title"],
                            "source": "coingecko",
                            "timestamp": item["published_at"],
                            "url": item["url"]
                        }
                        for item in data.get("data", [])[:limit]
                    ]
        except Exception as e:
            print(f"CoinGecko failed: {e}")
            return []


# 3. RSS Source (backup, ไม่มี limit)
class RSSNewsSource:
    def __init__(self):
        self.feeds = [
            ("https://cointelegraph.com/rss", "cointelegraph"),
            ("https://coindesk.com/arc/outboundfeeds/rss/", "coindesk"),
            ("https://www.binance.com/en/blog/rss.xml", "binance_blog")
        ]

    async def get_latest(self, limit=5) -> list:
        """ดึงข่าวจาก RSS feeds"""
        news = []
        per_feed = max(1, limit // len(self.feeds))

        for feed_url, source_name in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:per_feed]:
                    news.append({
                        "id": f"rss_{abs(hash(entry.link))}",
                        "title": entry.title,
                        "source": f"rss:{source_name}",
                        "timestamp": entry.get("published", datetime.now().isoformat()),
                        "url": entry.link
                    })
            except Exception as e:
                print(f"RSS {source_name} failed: {e}")
                continue

        return news[:limit]


# 4. CryptoPanic Source (เสริม)
class CryptoPanicSource:
    def __init__(self):
        self.api_key = os.getenv("CRYPTOPANIC_API_KEY")  # optional
        self.base_url = "https://cryptopanic.com/api/v1/posts/"

    async def get_latest(self, limit=5) -> list:
        """ดึงข่าวจาก CryptoPanic"""
        params = {
            "auth_token": self.api_key,
            "kind": "news",
            "filter": "rising"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    data = await resp.json()
                    return [
                        {
                            "id": f"cp_{item['id']}",
                            "title": item["title"],
                            "source": "cryptopanic",
                            "timestamp": item["published_at"],
                            "url": item["url"]
                        }
                        for item in data.get("results", [])[:limit]
                    ]
        except Exception as e:
            print(f"CryptoPanic failed: {e}")
            return []
```

---

## 🔧 Setup Instructions

### 1. Telegram (แนะนำ - เร็วที่สุด)

```bash
# 1. ไปที่ https://my.telegram.org/apps
# 2. สร้าง app ใหม่ → ได้ api_id + api_hash

# 3. ติดตั้ง Telethon
pip install telethon

# 4. เพิ่มใน .env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

### 2. CoinGecko (ไม่ต้อง key)

```bash
# ไม่ต้อง setup อะไร - ใช้ได้เลย
# Demo mode: 30 calls/min
```

### 3. RSS Feeds (ไม่ต้อง setup)

```bash
pip install feedparser
```

### 4. CryptoPanic (Optional)

```bash
# ไปที่ https://cryptopanic.com/developers/api/
# สมัคร free plan → ได้ API key

# เพิ่มใน .env
CRYPTOPANIC_API_KEY=your_key
```

---

## ✅ Summary

### Data Flow สุดท้าย:

```
┌─────────────────┐
│  Telegram (10)  │──┐
└─────────────────┘  │
┌─────────────────┐  │
│ CoinGecko (5)   │──┤
└─────────────────┘  │    ┌──────────────┐      ┌─────────┐
┌─────────────────┐  ├───→│ Aggregator   │─────→│ AI Brain│
│   RSS (5)       │──┤    │ (Combine +   │      └─────────┘
└─────────────────┘  │    │  Dedupe)     │
┌─────────────────┐  │    └──────────────┘
│ CryptoPanic (5) │──┘
└─────────────────┘
     (optional)
```

### ข้อดี:
1. **ไม่พึ่ง Twitter** - หลีกเลี่ยงปัญหาถูก block
2. **ไม่พึ่ง CryptoPanic แค่ตัวเดียว** - มีหลายแหล่งสำรอง
3. **Telegram real-time** - เร็วที่สุด, ข่าวก่อนใคร
4. **ฟรีทั้งหมด** - ไม่มีค่าใช้จ่าย
5. **Fault-tolerant** - แหล่งใดล้มไม่กระทบทั้งระบบ

### Next Steps:
1. ติดตั้ง Telegram API (5 นาที)
2. ทดสอบ NewsAggregator แยก
3. Integrate เข้า main loop
4. ทดสอบ 20 ข่าว/cycle