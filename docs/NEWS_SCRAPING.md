# 📰 News Scraping Guide & Recommendations

## Current Implementation

ClawBot ใช้ระบบ hybrid 2 ชั้น:

### Layer 1: RSS Feeds (Primary)
เร็ว, เบา, ไม่โดน block — ใช้เป็นหลัก

| Source | URL | Type |
|--------|-----|------|
| CoinDesk | `coindesk.com/arc/outboundfeeds/rss/` | Major |
| Cointelegraph | `cointelegraph.com/rss` | Major |
| CryptoNews | `cryptonews.com/news/feed/` | Major |
| Decrypt | `decrypt.co/feed` | Major |
| Bitcoin Magazine | `bitcoinmagazine.com/feed` | Major |
| The Block | `theblock.co/rss.xml` | Tier 2 |
| Blockworks | `blockworks.co/feed/` | Tier 2 |
| CryptoSlate | `cryptoslate.com/feed/` | Tier 2 |
| NewsBTC | `newsbtc.com/feed/` | Tier 2 |
| AMBCrypto | `ambcrypto.com/feed/` | Tier 2 |
| U.Today | `u.today/rss` | Tier 2 |
| BeInCrypto | `beincrypto.com/feed/` | Tier 2 |

### Layer 2: Web Scraping (Fallback)
ใช้เมื่อ RSS ส่ง articles < 10 — httpx + BeautifulSoup เป็น primary, Playwright เป็น backup

**Sites ที่ scrape:**
- CoinDesk `/markets/` page
- Cointelegraph `/tags/bitcoin` page
- CryptoNews `/news/` page

---

## Anti-Blocking Measures

| Technique | Implementation |
|-----------|---------------|
| **User-Agent Rotation** | `fake-useragent` library สุ่ม UA ทุก request |
| **Random Delays** | 2-5 วินาทีระหว่าง requests |
| **Browser Headers** | httpx ส่ง headers เหมือน browser จริง (Accept, DNT, Sec-Fetch) |
| **Playwright Stealth** | Launch args ที่ลด fingerprint (no-sandbox, disable-gpu) |
| **Resource Blocking** | Block images, fonts, ads, analytics ใน Playwright |
| **Browser Reuse** | ไม่ spawn Chromium ใหม่ทุกรอบ (ประหยัด RAM) |

---

## 💡 Recommendations สำหรับเพิ่มในอนาคต

### 1. Twitter/X Monitoring (ดีมากสำหรับ scalping)

ข่าว crypto เร็วที่สุดมาจาก Twitter เสมอ ใช้ free methods:

- **Nitter RSS**: `nitter.net/<username>/rss` — RSS feed ของ Twitter accounts
  - ตัวอย่าง: `nitter.net/whale_alert/rss`, `nitter.net/cabornek/rss` 
  - ⚠️ Nitter instances อาจ down ต้องมี fallback list
  
- **Twitter API (Free tier)**: 1,500 tweets/month — ใช้ track keywords "bitcoin", "eth", "solana"

### 2. Reddit Sentiment

- Reddit RSS: `reddit.com/r/cryptocurrency/.rss`
- ดูจำนวน upvotes + comments velocity = sentiment indicator

### 3. Telegram Channel Monitoring

- สร้าง bot ที่ join crypto channels แล้วดูด messages
- Channels แนะนำ: CryptoWhale, WhaleTankChat, CoinMarketCal

### 4. On-Chain Alerts (Free)

- **Whale Alert** RSS: `whale-alert.io/feed`
- วาฬย้ายเหรียญเข้า exchange = สัญญาณขาย
- วาฬย้ายเหรียญออก exchange = สัญญาณ hold/buy

### 5. Exchange-Specific Data

- **Binance Announcements**: `binance.com/en/support/announcement` — listing/delisting
- **Open Interest**: Binance API `/fapi/v1/openInterest`
- **Liquidation Stream**: WebSocket `wss://fstream.binance.com/ws/forceOrder` (real-time liquidations)

### 6. Enhanced Scraping (Advanced)

- **Proxy Rotation**: ใช้ free proxy list หรือ rotating proxy service
- **Headless Detection Bypass**: `playwright-stealth` plugin
- **CAPTCHA Solving**: ถ้า sites เริ่ม block — ส่วนใหญ่ใช้ Cloudflare ต้องใช้ `cloudscraper`

---

## VPS Memory Usage

| Method | RAM Usage | Speed |
|--------|-----------|-------|
| RSS (feedparser) | ~5MB | ~1-2s per feed |
| httpx scraping | ~10-20MB | ~2-3s per site |
| Playwright | ~200-400MB | ~5-10s per site |

กลยุทธ์: ใช้ RSS เป็นหลัก, httpx เป็น supplement, Playwright เฉพาะกรณีจำเป็น
