# 📡 Data Sources — Complete List (All FREE)

## ✅ Currently Used

### Binance API (FREE)
| Data | Endpoint | Rate Limit | Interval |
|------|----------|------------|----------|
| Ticker Price | `/api/v3/ticker/price` | 1200/min | Every cycle |
| 24h Stats | `/api/v3/ticker/24hr` | 1200/min | Every cycle |
| OHLCV 1m | `/api/v3/klines?interval=1m` | 1200/min | 60 candles |
| OHLCV 5m | `/api/v3/klines?interval=5m` | 1200/min | 200 candles |
| OHLCV 1h | `/api/v3/klines?interval=1h` | 1200/min | 48 candles |
| Order Book | `/api/v3/depth` | 1200/min | Top 5 |
| **Funding Rate** | `/fapi/v1/fundingRate` | 500/min | Latest |
| **L/S Ratio** | `/futures/data/globalLongShortAccountRatio` | 500/min | 5m |

### News (FREE — RSS + Scraping)
| Source | Method | Articles/Day |
|--------|--------|--------------|
| CoinDesk | RSS + Scrape | ~40 |
| Cointelegraph | RSS + Scrape | ~50 |
| CryptoNews | RSS + Scrape | ~30 |
| Decrypt | RSS | ~20 |
| Bitcoin Magazine | RSS | ~10 |
| The Block | RSS | ~30 |
| Blockworks | RSS | ~25 |
| CryptoSlate | RSS | ~20 |
| NewsBTC | RSS | ~15 |
| AMBCrypto | RSS | ~10 |
| U.Today | RSS | ~20 |
| BeInCrypto | RSS | ~15 |

### On-Chain (FREE)
| Data | Provider | Rate Limit |
|------|----------|------------|
| Fear & Greed Index | Alternative.me | 50/day |
| Market Cap Data | CoinGecko | 30/min |

### AI Processing (FREE)
| Provider | Model | Cost | Limit |
|----------|-------|------|-------|
| **Groq** (primary) | Llama 3.1-70B | FREE | 30 req/min |
| Claude (backup) | Haiku | ~$0.25/1M tokens | Pay-per-use |
| Kimi (backup) | Moonshot-v1-8k | FREE tier | Limited |

---

## 💡 Recommended Additions (Future)

| Source | Method | สำหรับ |
|--------|--------|--------|
| Twitter/X (via Nitter) | RSS | Real-time market sentiment |
| Reddit r/cryptocurrency | RSS | Community mood |
| Whale Alert | RSS | Large transaction detection |
| Binance Open Interest | REST API | Market positioning |
| Binance Liquidations | WebSocket | Squeeze detection |

ดูรายละเอียดเพิ่มที่ [NEWS_SCRAPING.md](NEWS_SCRAPING.md)
