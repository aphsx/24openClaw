---
description: Fetch crypto news from 6 free sources and Fear & Greed Index
---

# ClawBot News Skill

## Purpose
Aggregate latest crypto news from multiple free sources and fetch the Fear & Greed Index for market sentiment.

## Steps

1. **Fetch News (async, parallel)**:
   ```python
   from src.data.news_fetcher import NewsFetcher
   fetcher = NewsFetcher()
   news = await fetcher.fetch_all()  # Returns list of 20 news dicts
   ```

2. **Fetch Fear & Greed**:
   ```python
   from src.data.news_fetcher import FearGreedFetcher
   fg = FearGreedFetcher()
   result = await fg.fetch()  # {"value": 68, "label": "Greed"}
   ```

## News Sources (6, all free)
| Source | Method | Rate Limit |
|--------|--------|-----------|
| CryptoPanic API | REST + free key | Unlimited |
| CryptoPanic RSS | RSS | Unlimited |
| free-crypto-news | REST, no key | Unlimited |
| CoinDesk RSS | RSS | Unlimited |
| CoinTelegraph RSS | RSS | Unlimited |
| Binance Blog RSS | RSS | Unlimited |

## Output Format
```json
[
  {
    "title": "Bitcoin ETF sees $500M inflow",
    "source": "CoinDesk",
    "timestamp": "2026-02-11T00:45:00Z",
    "url": "https://..."
  }
]
```

## Timeout Handling
- If news takes >15s → use cached news (marked as `cached`)
- If news takes >5s → refresh chart data after (to ensure latest prices)
