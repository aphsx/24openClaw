# 💰 Cost Analysis - Free vs Paid

## ✅ ฟรีทั้งหมด (ไม่มีค่าใช้จ่าย)

| Component | Provider | Status | Notes |
|-----------|----------|--------|-------|
| **Price Data** | Binance API | ✅ FREE | 1200 req/min limit |
| **OHLCV Data** | Binance API | ✅ FREE | Included |
| **Order Book** | Binance API | ✅ FREE | Included |
| **News (RSS)** | CoinDesk, Cointelegraph, etc. | ✅ FREE | No rate limit |
| **Fear & Greed Index** | Alternative.me API | ✅ FREE | 50 req/day |
| **Market Cap Data** | CoinGecko API | ✅ FREE | 50 req/min |
| **Database** | Supabase | ✅ FREE | 500MB, 2GB bandwidth |
| **Technical Indicators** | pandas-ta (local) | ✅ FREE | Runs locally |
| **Logging** | loguru (local) | ✅ FREE | Runs locally |

---

## 💵 ค่าใช้จ่ายที่ต้องจ่าย

| Component | Provider | Cost | Notes |
|-----------|----------|------|-------|
| **VPS** | Contabo/DigitalOcean | ~$5-15/mo | 8GB RAM, 2 cores |
| **AI (Primary)** | Anthropic Claude | Pay-per-use | ~$0.002/request |
| **AI (Backup)** | Kimi/Moonshot | Pay-per-use | ~$0.001/request |
| **Telegram** | Telegram Bot API | ✅ FREE | Bot notifications |

---

## 📊 ประมาณการค่าใช้จ่าย AI

```
Cycle ทุก 5 นาที = 288 cycles/day
AI calls/cycle = 2 (sentiment + decision)
Total AI calls/day = 576

Claude Haiku = $0.00025/1K input + $0.00125/1K output
~500 tokens input, ~300 tokens output per call

Daily cost = 576 × ($0.000125 + $0.000375) = ~$0.29/day
Monthly cost = ~$8.70/month
```

---

## 🆓 Alternative FREE AI Options

หากต้องการ AI ฟรี 100%:

| Option | Free Tier | Limitation |
|--------|-----------|------------|
| **Google Gemini** | 15 req/min | Rate limited |
| **Groq (Llama)** | 30 req/min | Rate limited |
| **Ollama (Local)** | Unlimited | Needs 8GB+ RAM |

### Recommendation:
ถ้าอยากฟรี 100% → ใช้ **Groq API** (Llama 3.1) แทน Claude
- ฟรีจริง ไม่ต้องจ่าย
- เร็วมาก (inference speed)
- ข้อเสีย: Rate limit 30 req/min

---

## ⚠️ สิ่งที่ต้องระวัง

1. **Supabase Free Tier**
   - 500MB storage limit
   - ควรตั้ง data retention (ลบ data เก่า 30 วัน)

2. **CoinGecko Rate Limit**
   - 50 req/min
   - ถ้าเกินอาจถูก block

3. **Binance API**
   - 1200 req/weight/min
   - ถ้า trade เยอะอาจโดน limit
