# 📰 Extended Data Sources - Complete List

## 🔗 RSS Feeds (FREE - ไม่มี Rate Limit)

### Tier 1: Major Crypto News (ใช้ในระบบแล้ว)

| Source | URL | Articles/Day | Language |
|--------|-----|--------------|----------|
| **Cointelegraph** | https://cointelegraph.com/rss | ~50 | EN |
| **CoinDesk** | https://www.coindesk.com/arc/outboundfeeds/rss/ | ~40 | EN |
| **CryptoNews** | https://cryptonews.com/news/feed/ | ~30 | EN |
| **Decrypt** | https://decrypt.co/feed | ~20 | EN |
| **Bitcoin Magazine** | https://bitcoinmagazine.com/feed | ~15 | EN |

### Tier 2: Additional Sources (แนะนำเพิ่ม)

| Source | URL | Articles/Day | Notes |
|--------|-----|--------------|-------|
| **The Block** | https://www.theblock.co/rss.xml | ~30 | Research quality |
| **Blockworks** | https://blockworks.co/feed/ | ~25 | DeFi focus |
| **CryptoSlate** | https://cryptoslate.com/feed/ | ~40 | Altcoin coverage |
| **NewsBTC** | https://www.newsbtc.com/feed/ | ~35 | Trading focus |
| **AMBCrypto** | https://ambcrypto.com/feed/ | ~25 | Altcoin analysis |
| **U.Today** | https://u.today/rss | ~30 | Breaking news |
| **CryptoPotato** | https://cryptopotato.com/feed/ | ~20 | Market analysis |
| **Bitcoinist** | https://bitcoinist.com/feed/ | ~25 | Bitcoin focus |
| **BeInCrypto** | https://beincrypto.com/feed/ | ~35 | Global coverage |
| **DailyHodl** | https://dailyhodl.com/feed/ | ~25 | Market moves |

### Tier 3: Specialized / Regional

| Source | URL | Focus |
|--------|-----|-------|
| **DeFi Pulse** | https://defipulse.com/feed | DeFi specific |
| **NFT Now** | https://nftnow.com/feed/ | NFT news |
| **Crypto Briefing** | https://cryptobriefing.com/feed/ | Deep analysis |
| **Protos** | https://protos.com/feed/ | Investigative |
| **Crypto.news** | https://crypto.news/feed/ | Mixed |

---

## 📊 Market Data APIs (FREE)

### Price & Volume

| API | Endpoint | Rate Limit | Data |
|-----|----------|------------|------|
| **Binance** | api.binance.com | 1200 req/min | Price, OHLCV, Order Book |
| **CoinGecko** | api.coingecko.com | 50 req/min | Price, Market Cap, Volume |
| **CryptoCompare** | min-api.cryptocompare.com | 100K req/mo | Price, Historical |
| **CoinCap** | api.coincap.io | 200 req/min | Real-time price |
| **Messari** | data.messari.io | 20 req/min | Price, Metrics |

### Example: เพิ่ม CryptoCompare

```python
# src/collectors/cryptocompare_collector.py
async def get_news():
    url = "https://min-api.cryptocompare.com/data/v2/news/"
    params = {"lang": "EN", "categories": "BTC,ETH,Trading"}
    response = await httpx.get(url, params=params)
    return response.json()
```

---

## 🐋 On-Chain Data APIs (FREE Tier)

### Fear & Greed Index

```python
# Alternative.me (FREE, ไม่จำกัด)
url = "https://api.alternative.me/fng/?limit=10"

Response:
{
    "data": [
        {"value": "45", "value_classification": "Fear"}
    ]
}
```

### Whale Alert (FREE Tier)

```python
# FREE: 10 req/min
url = "https://api.whale-alert.io/v1/transactions"
params = {
    "api_key": "YOUR_KEY",
    "min_value": 500000,
    "start": int(time.time()) - 3600
}

# Response: Large transactions >$500K
```

### DeFi Llama (FREE, No Key)

```python
# TVL Data
url = "https://api.llama.fi/tvl/ethereum"

# Protocol Rankings
url = "https://api.llama.fi/protocols"

# Chain TVL
url = "https://api.llama.fi/chains"
```

### Etherscan Gas (FREE, 5 req/sec)

```python
url = "https://api.etherscan.io/api"
params = {
    "module": "gastracker",
    "action": "gasoracle",
    "apikey": "YOUR_KEY"
}

# Response: gasPrice, suggestBaseFee
```

---

## 🐦 Social Sentiment (Alternatives to Twitter)

### Reddit (FREE via PRAW)

```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_ID",
    client_secret="YOUR_SECRET",
    user_agent="crypto_bot"
)

# Get top posts from crypto subreddits
subreddits = ["cryptocurrency", "bitcoin", "ethereum", "altcoin"]
for sub in subreddits:
    posts = reddit.subreddit(sub).hot(limit=25)
    for post in posts:
        print(post.title, post.score)
```

### StockTwits (FREE API)

```python
# Crypto trending
url = "https://api.stocktwits.com/api/2/streams/trending.json"

# Specific symbol
url = "https://api.stocktwits.com/api/2/streams/symbol/BTC.X.json"
```

### LunarCrush (FREE Tier)

```python
# 10 req/day FREE
url = "https://lunarcrush.com/api3/coins/list"
params = {"key": "YOUR_KEY"}

# Returns: social volume, engagement, sentiment
```

---

## 🏦 Exchange-Specific Data

### Binance (เรามีแล้ว)

```python
# Funding Rate (Perpetual)
url = "https://fapi.binance.com/fapi/v1/fundingRate"
params = {"symbol": "BTCUSDT", "limit": 10}

# Open Interest
url = "https://fapi.binance.com/fapi/v1/openInterest"

# Long/Short Ratio
url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
```

### OKX (FREE)

```python
# Funding Rate
url = "https://www.okx.com/api/v5/public/funding-rate"
params = {"instId": "BTC-USD-SWAP"}

# Open Interest
url = "https://www.okx.com/api/v5/public/open-interest"
```

### Bybit (FREE)

```python
# Risk Limit
url = "https://api.bybit.com/v5/market/risk-limit"
params = {"category": "linear", "symbol": "BTCUSDT"}
```

---

## 📈 Priority Order: สิ่งที่ควรเพิ่ม

### ✅ Already Have

- [x] Binance price/OHLCV
- [x] RSS news (5 sources)
- [x] Fear & Greed Index
- [x] CoinGecko market data

### 🔜 Recommended Additions (FREE)

| Priority | Source | Type | Effort |
|----------|--------|------|--------|
| 1 | เพิ่ม RSS sources (Tier 2) | News | 5 min |
| 2 | Binance Funding Rate | On-chain | 15 min |
| 3 | Binance Long/Short Ratio | Sentiment | 15 min |
| 4 | DeFi Llama TVL | On-chain | 30 min |
| 5 | Reddit sentiment | Social | 1 hr |

---

## 🔧 เพิ่ม RSS Sources ได้เลย

แก้ไขไฟล์ `src/collectors/news_collector.py`:

```python
RSS_FEEDS = [
    # Tier 1 (มีแล้ว)
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptonews.com/news/feed/",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/feed",
    
    # Tier 2 (เพิ่มใหม่)
    "https://www.theblock.co/rss.xml",
    "https://blockworks.co/feed/",
    "https://cryptoslate.com/feed/",
    "https://www.newsbtc.com/feed/",
    "https://ambcrypto.com/feed/",
    "https://u.today/rss",
    "https://beincrypto.com/feed/",
]
```

**ผลลัพธ์:** จาก ~150 articles/day → ~400+ articles/day
