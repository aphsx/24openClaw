# 🦞 OpenClaw AI (ClawdBot) — คู่มือสร้างระบบเทรดอัตโนมัติแบบละเอียดสุดๆ

> **อ้างอิงจาก: GitHub openclaw/openclaw (100K+ stars), molt-bot/openclaw-trading-assistant, BankrBot/openclaw-skills, docs.openclaw.ai, openclawai.me, CoinMarketCap, TradingView, Medium articles (กุมภาพันธ์ 2026)**

> ⚠️ **คำเตือน**: การเทรดคริปโตมีความเสี่ยงสูงมาก ระบบนี้เพื่อการศึกษาเท่านั้น อย่าใช้เงินที่คุณรับไม่ได้หากสูญเสีย

---

## 📋 สารบัญ

1. [OpenClaw คืออะไร? — ที่มาและพัฒนาการ](#1-openclaw-คืออะไร)
2. [Architecture ของ OpenClaw Trading System](#2-architecture-ของ-openclaw-trading-system)
3. [ขั้นตอนการติดตั้ง OpenClaw ตั้งแต่ศูนย์](#3-ขั้นตอนการติดตั้ง-openclaw-ตั้งแต่ศูนย์)
4. [ตั้งค่า Trading — เชื่อมต่อ Hyperliquid](#4-ตั้งค่า-trading--เชื่อมต่อ-hyperliquid)
5. [Skills System — หัวใจของ OpenClaw](#5-skills-system--หัวใจของ-openclaw)
6. [Trading Strategies ที่ใช้กับ OpenClaw](#6-trading-strategies-ที่ใช้กับ-openclaw)
7. [News & Sentiment — ดึงข่าวและวิเคราะห์อารมณ์ตลาด](#7-news--sentiment)
8. [Risk Management — ระบบป้องกันความเสี่ยง](#8-risk-management)
9. [Monitoring & Dashboard](#9-monitoring--dashboard)
10. [Architecture แบบ Brain + Executor (FMZ Quant)](#10-architecture-แบบ-brain--executor)
11. [ค่าใช้จ่ายและทางเลือก Model](#11-ค่าใช้จ่ายและทางเลือก-model)
12. [Security — ความปลอดภัยที่ต้องรู้](#12-security)
13. [Roadmap สำหรับมือใหม่](#13-roadmap-สำหรับมือใหม่)
14. [แหล่งข้อมูลและ Repos สำคัญ](#14-แหล่งข้อมูลและ-repos-สำคัญ)

---

## 1. OpenClaw คืออะไร?

### 1.1 ประวัติโดยย่อ

OpenClaw คือ **open-source, self-hosted personal AI assistant** ที่รันบนเครื่องของคุณเอง สร้างโดย **Peter Steinberger** (ผู้ก่อตั้ง PSPDFKit ที่ขายได้ ~$119M)

```
Timeline:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ธ.ค. 2025   │ เปิดตัวในชื่อ "Clawdbot" → viral ทันที
ม.ค. 2026   │ Anthropic ร้องเรื่อง trademark (คล้าย "Claude")
             │ → เปลี่ยนชื่อเป็น "MoltBot"
             │ → มิจฉาชีพ snipe X handle → ปล่อย fake $CLAWD token
             │   (pump ไป $16M แล้ว dump)
29 ม.ค. 2026│ เปลี่ยนชื่อเป็น "OpenClaw" อย่างเป็นทางการ
             │ "Open" = open-source + "Claw" = lobster heritage 🦞
ก.พ. 2026   │ 100,000+ GitHub stars, 2M visitors/สัปดาห์
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 1.2 OpenClaw ต่างจาก Bot ทั่วไปอย่างไร?

```
┌──────────────────────────────────────────────────────────────────┐
│  Feature              │ Bot ทั่วไป (3Commas, etc.) │ OpenClaw    │
├──────────────────────────────────────────────────────────────────┤
│  Interface            │ Config files, GUI          │ สนทนาภาษา  │
│                       │                            │ ธรรมชาติ     │
│  AI Model             │ Rule-based เท่านั้น         │ LLM (Claude,│
│                       │                            │ GPT, Gemini)│
│  รันที่ไหน             │ Cloud (ของเขา)              │ เครื่องคุณเอง│
│  ความเป็นส่วนตัว        │ ข้อมูลอยู่บน cloud          │ Local-first │
│  Extensibility        │ จำกัด                       │ Skills sys- │
│                       │                            │ tem (plugin)│
│  Browser Automation   │ ไม่มี                       │ Chrome con- │
│                       │                            │ trol เต็มรูป│
│  Persistent Memory    │ ไม่มี                       │ จำบริบทข้าม │
│                       │                            │ session ได้ │
│  ราคา                  │ $20-500/เดือน              │ ฟรี (open   │
│                       │                            │ source)     │
│  สื่อสารผ่าน           │ Web UI เท่านั้น             │ 13+ แพลต   │
│                       │                            │ ฟอร์ม        │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 แนวคิดหลัก: "You are the CIO, OpenClaw is your Lead Trader"

OpenClaw ไม่ใช่ bot ที่กด run แล้วปล่อย — มันเป็น **AI assistant ที่คุยกับคุณ** เพื่อ:
- พูดคุยเรื่อง strategy
- วิเคราะห์ตลาดให้
- ส่ง signal พร้อมเหตุผล
- ขออนุมัติก่อนเทรดใหญ่
- รายงาน PnL ให้ดู
- เรียนรู้จากการเทรดที่ผ่านมา

---

## 2. Architecture ของ OpenClaw Trading System

### 2.1 System Architecture (จาก GitHub: molt-bot/openclaw-trading-assistant)

```
┌────────────────────────────┐
│     User / Operator        │
│  Strategy · Feedback · Chat│
└──────────────┬─────────────┘
               │
    (สนทนาผ่าน OpenClaw — Telegram/WhatsApp/Discord)
               │
┌──────────────▼──────────────────────────────────────────────────┐
│              Conversational Interface                            │
│              (OpenClaw Layer)                                    │
│                                                                  │
│  - Strategy discussion (คุยเรื่อง strategy)                      │
│  - Trade explanations (อธิบายเหตุผลทุกเทรด)                     │
│  - Pre/Post trade analysis (วิเคราะห์ก่อน/หลังเทรด)             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ feedback / queries
               ▼
┌─────────────────────────────────────────────────────────────────┐
│           Decision Engine (Alpha Arena Core)                     │
│                                                                  │
│  - nof1.ai Alpha Arena models (ML/AI ที่ชนะการแข่งขัน)          │
│  - Strategy scoring & decay (ให้คะแนนและลด score กลยุทธ์ที่แพ้) │
│  - Self-evaluation loop (ประเมินตัวเอง)                          │
│  - Explainable decision output (อธิบายการตัดสินใจได้)            │
└───────────┬────────────────────────────┬────────────────────────┘
            │ signals                    │ decisions
            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────────────────┐
│  Data & Intelligence  │    │  Execution Engine                 │
│  Layer                │    │                                   │
│                       │    │  - Hyperliquid L1 (sub-second)    │
│  - Market Data        │    │  - Position management            │
│    (OHLCV, Orderbook) │    │  - Stop-loss / Take-profit        │
│  - News Sentiment     │    │  - Human-in-the-loop approval     │
│    (RSS, X/Twitter)   │    │                                   │
│  - On-chain Data      │    │  หรือ                              │
│    (Whale, OI, Fund.) │    │  - FMZ Quant Platform             │
│  - Social Signals     │    │  - Binance/OKX/Bybit via CCXT    │
│    (Reddit, Telegram) │    │                                   │
└───────────────────────┘    └───────────────────────────────────┘
```

### 2.2 Core Components

```
OpenClaw Gateway (หัวใจ)
├── Session Manager     → จัดการ conversation sessions
├── Model Router        → เลือก AI model (Claude, GPT, Gemini, etc.)
├── Tool System         → browser, canvas, exec, cron, etc.
├── Skills Engine       → โหลด SKILL.md (markdown-based plugins)
├── Channel Manager     → Telegram, WhatsApp, Discord, Slack, etc.
├── Persistent Memory   → จำบริบทข้าม session
├── Cron / Heartbeat    → ทำงานตามเวลาที่ตั้ง (เช่น เช็คตลาดทุก 10 นาที)
├── Vault               → เก็บ API keys แบบ encrypted
└── Security Layer      → DM filtering, sandbox, permission
```

---

## 3. ขั้นตอนการติดตั้ง OpenClaw ตั้งแต่ศูนย์

### 3.1 System Requirements

```
Minimum:
- OS: macOS, Linux, หรือ Windows (via WSL2)
- Node.js 18+ (สำหรับ Gateway)
- RAM: 4GB+
- Storage: 1GB+
- Internet connection

Recommended:
- macOS (ได้รับ support ดีที่สุด)
- Mac Mini M-series (สำหรับ 24/7 operation)
- หรือ VPS (DigitalOcean, Hetzner, Oracle Cloud Free Tier)
- GPU (ถ้าใช้ local LLM เช่น Ollama)
```

### 3.2 Installation

**วิธีที่ 1: Quick Install (แนะนำ)**

```bash
# ดาวน์โหลด release จาก GitHub
# ไปที่: https://github.com/openclaw/openclaw/releases
# ดาวน์โหลด .7z file → แตกไฟล์ → Run

# หรือ clone แล้ว setup
git clone https://github.com/openclaw/openclaw.git
cd openclaw
npm install
```

**วิธีที่ 2: Onboarding Wizard (แนะนำสำหรับมือใหม่)**

```bash
# รัน onboarding wizard
openclaw onboard

# Wizard จะพาคุณผ่านขั้นตอน:
# 1. ตั้งค่า Gateway
# 2. เลือก Workspace
# 3. เชื่อมต่อ Channel (Telegram/WhatsApp/Discord)
# 4. ติดตั้ง Skills
# 5. ตั้งค่า AI Model
```

**วิธีที่ 3: Docker**

```bash
docker build -t openclaw .
docker-compose up -d
```

### 3.3 เชื่อมต่อ Messaging Platform (Telegram แนะนำ)

```
ขั้นตอนเชื่อม Telegram:
1. คุยกับ @BotFather บน Telegram
2. สร้าง Bot ใหม่ → ได้ Bot Token
3. ใส่ Token ใน config:

   # openclaw.json
   {
     "channels": {
       "telegram": {
         "botToken": "YOUR_BOT_TOKEN",
         "allowFrom": ["YOUR_TELEGRAM_ID"]
       }
     }
   }

4. เริ่มแชทกับ Bot ของคุณ!
```

### 3.4 เลือก AI Model

OpenClaw รองรับหลาย model providers:

```
┌──────────────────────────────────────────────────────────────────┐
│  Provider       │ Model              │ ค่าใช้จ่าย        │ หมายเหตุ│
├──────────────────────────────────────────────────────────────────┤
│  Anthropic      │ Claude Opus 4.5    │ ~$15/MTok input    │ ดีที่สุด│
│                 │ Claude Sonnet 4.5  │ ~$3/MTok input     │ สำหรับ  │
│                 │                    │                    │ trading │
│                                                                   │
│  Google         │ Gemini 3 Flash     │ ฟรี (OAuth login)  │ ดีมาก  │
│                 │                    │                    │ ฟรี!    │
│                                                                   │
│  OpenRouter     │ หลาย model ฟรี      │ บาง model ฟรี      │ flexible│
│                                                                   │
│  Ollama (local) │ Llama 3.1, Mistral │ ฟรี 100%           │ ต้อง   │
│                 │ Qwen 2.5           │ (รันในเครื่อง)      │ มี GPU │
│                                                                   │
│  MiniMax        │ M2.1               │ ฟรี tier มี         │ แนะนำ  │
│                 │                    │                    │ อย่างเป็น│
│                 │                    │                    │ ทางการ  │
│                                                                   │
│  Groq           │ Llama 3.3 70B      │ ฟรี 30 req/min     │ เร็วมาก│
└──────────────────────────────────────────────────────────────────┘
```

**ตั้งค่า Model:**

```json
// openclaw.json
{
  "agent": {
    "model": "anthropic/claude-sonnet-4-5-20250929",
    "temperature": 0.7
  }
}
```

**ใช้ฟรีกับ Ollama (local, offline 100%):**

```bash
# ติดตั้ง Ollama
curl -fsSL https://ollama.com/install.sh | sh

# ดาวน์โหลด model
ollama pull llama3.1:8b

# ตั้งค่าใน OpenClaw
# model: "ollama/llama3.1:8b"
```

---

## 4. ตั้งค่า Trading — เชื่อมต่อ Hyperliquid

### 4.1 ทำไมต้อง Hyperliquid?

OpenClaw เลือก Hyperliquid เป็น exchange หลักเพราะ:
- **L1 blockchain** — sub-second execution
- **Perps (Crypto)** + **Spot (synthetics สำหรับ Stocks/Commodities)**
- **API ที่ดี** — รองรับ automated trading
- **ค่าธรรมเนียมต่ำ**
- ชุมชน Alpha Arena (nof1.ai) ที่ OpenClaw ดึง best practices มา

### 4.2 Setup Trading

```bash
# 1. เก็บ API keys ใน encrypted vault
openclaw vault set HYPERLIQUID_API_KEY your-key
openclaw vault set HYPERLIQUID_API_SECRET your-secret

# 2. ติดตั้ง trading skill
openclaw skills install nof1-trading

# 3. ตั้งค่าใน config
```

```yaml
# config.yaml (ส่วน trading)
skills:
  trading:
    enabled: true
    exchange: hyperliquid
    riskLimit: 0.02        # ใช้ไม่เกิน 2% ต่อ position
    mode: "human-approval"  # ต้องกดอนุมัติทุกเทรด (เริ่มต้น)
```

### 4.3 Human-in-the-Loop Mode (สำคัญมาก!)

```
┌──────────────────────────────────────────────────────────────────┐
│  Mode              │ พฤติกรรม                                     │
├──────────────────────────────────────────────────────────────────┤
│  human-approval    │ ทุกเทรดต้องกดอนุมัติใน Telegram              │
│  (แนะนำเริ่มต้น)    │ Bot ส่ง signal + เหตุผล → รอคุณกด ✅ / ❌   │
│                                                                   │
│  auto-small        │ เทรดเล็ก (< threshold) → auto execute        │
│                    │ เทรดใหญ่ (> threshold) → ขออนุมัติ            │
│                                                                   │
│  full-auto         │ ⚠️ ทำทุกอย่างเอง — ใช้เมื่อมั่นใจแล้วเท่านั้น│
│  (อันตราย)          │ ยังมี hardcoded risk limits ป้องกันอยู่       │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 ตัวอย่างการสนทนากับ OpenClaw (Trading)

```
คุณ: "I think ETH is going to dump based on the macro outlook"

Bot: "Technicals disagree (RSI is oversold at 28), but given your macro 
     view, I recommend a small short with a tight stop at $3,250. 
     
     📊 Analysis:
     - RSI (1h): 28 (oversold → ปกติจะ bounce)
     - EMA Trend: ยังเป็น bearish (EMA9 < EMA21 < EMA50)
     - Sentiment: -0.3 (slightly bearish จาก news)
     - Funding Rate: -0.01% (shorts paying)
     
     🎯 Recommendation:
     - SHORT ETH-PERP
     - Size: 0.5 ETH (~1.2% of equity)
     - Entry: $3,180
     - Stop: $3,250 (-2.2%)
     - TP: $3,050 (+4.1%)
     
     Execute? [✅ Approve] [❌ Reject] [✏️ Modify]"

คุณ: [กด ✅ Approve]

Bot: "✅ Order executed. SHORT 0.5 ETH-PERP @ $3,180.50
     Stop-loss set at $3,250. Will monitor and update."
```

```
คุณ: "Show me my PnL breakdown for AI-related tokens this week 
      and tell me where we messed up"

Bot: "📊 Weekly PnL Breakdown (AI Tokens):
     
     ✅ Wins:
     - FET long: +$45.20 (+3.2%) — caught momentum early
     - RENDER short: +$22.10 (+1.8%) — good timing
     
     ❌ Losses:
     - TAO long: -$67.50 (-4.5%) — entered too early
       → Mistake: Ignored the 4h EMA bearish cross
     - NEAR long: -$15.30 (-1.1%) — stopped out
       → Mistake: Stop was too tight for the volatility
     
     📈 Net: -$15.50 (-0.6%)
     
     🔍 Key Learnings:
     1. TAO trade: Need to wait for HTF confirmation
     2. NEAR trade: Should use ATR-based stops (1.5x ATR)
     
     I'll adjust the strategy weights accordingly."
```

---

## 5. Skills System — หัวใจของ OpenClaw

### 5.1 Skills คืออะไร?

Skills คือ **markdown-based plugins** (ไฟล์ SKILL.md) ที่สอน OpenClaw วิธีทำสิ่งต่างๆ เปรียบเหมือน "ตำราเรียน" สำหรับ AI

```
Skills = ตำราเรียน (สอนวิธีทำ)
Tools = เครื่องมือ (ทำได้จริง)

Skill ต้องมี Tool ถึงจะทำได้ เช่น:
- Skill "obsidian" สอนวิธีจัดการ notes
  → ต้องเปิด Tool "write" ถึงจะเขียนไฟล์ได้

- Skill "trading" สอนวิธีเทรด
  → ต้องเปิด Tool "exec" ถึงจะรัน script ได้
```

### 5.2 Trading Skills ที่สำคัญ

```
┌──────────────────────────────────────────────────────────────────┐
│  Skill                     │ ทำอะไร                │ ที่มา        │
├──────────────────────────────────────────────────────────────────┤
│  nof1-trading              │ Core trading engine    │ molt-bot/    │
│                            │ + Alpha Arena models   │ openclaw-    │
│                            │ + Hyperliquid exec     │ trading-     │
│                            │                        │ assistant    │
│                                                                   │
│  bankr/token-trading       │ Token trading,         │ BankrBot/    │
│                            │ portfolio management   │ openclaw-    │
│                            │                        │ skills       │
│                                                                   │
│  bankr/leverage-trading    │ Leveraged trading      │ BankrBot/    │
│                            │ on DEX/CEX             │ openclaw-    │
│                            │                        │ skills       │
│                                                                   │
│  polyclaw                  │ Polymarket trading,    │ chainstack-  │
│                            │ arbitrage, hedging     │ labs/polyclaw│
│                                                                   │
│  polymarket-assistant      │ Cross-platform         │ openclaw/    │
│                            │ Polymarket +           │ skills       │
│                            │ Hyperliquid hedging    │              │
│                                                                   │
│  bankr/automation          │ Automated workflows    │ BankrBot     │
│                                                                   │
│  CoinGecko integration     │ Price data, market cap │ community    │
│                                                                   │
│  DeFiLlama integration     │ DeFi TVL, yields       │ community    │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 วิธีติดตั้ง Skills

```bash
# วิธีที่ 1: จาก ClawHub (registry อย่างเป็นทางการ)
clawhub sync --all

# วิธีที่ 2: จาก GitHub URL
# แค่ให้ OpenClaw URL ของ repo → มันจะให้เลือก skill
# เช่น: https://github.com/BankrBot/openclaw-skills

# วิธีที่ 3: Manual install
cp -r polyclaw ~/.openclaw/skills/
cd ~/.openclaw/skills/polyclaw
uv sync

# วิธีที่ 4: ผ่าน config
# openclaw.json
{
  "skills": {
    "entries": {
      "polyclaw": {
        "enabled": true,
        "env": {
          "CHAINSTACK_NODE": "https://polygon-mainnet...",
          "POLYCLAW_PRIVATE_KEY": "0x...",
          "OPENROUTER_API_KEY": "sk-or-v1-..."
        }
      }
    }
  }
}
```

### 5.4 โครงสร้าง Skill File

```
my-trading-skill/
├── SKILL.md              # ← หัวใจ: markdown สอน AI วิธีเทรด
├── references/
│   ├── strategy-docs.md  # เอกสารเพิ่มเติม
│   └── api-reference.md
└── scripts/
    ├── trade.py          # Script execution
    └── backtest.py       # Backtesting
```

**ตัวอย่าง SKILL.md:**

```markdown
---
name: my-crypto-strategy
description: "AI-powered crypto trading with multi-timeframe analysis"
metadata:
  openclaw:
    config:
      requiredEnv: ["HYPERLIQUID_API_KEY", "HYPERLIQUID_API_SECRET"]
---

# My Crypto Trading Strategy

## Data Collection
1. ดึง OHLCV จาก Hyperliquid API สำหรับ BTC, ETH, SOL
2. Timeframes: 5m, 15m, 1h, 4h
3. คำนวณ indicators: RSI(14), EMA(9,21,50), MACD, BB(20,2)

## Decision Logic
- LONG เมื่อ: RSI < 30 + EMA9 > EMA21 + MACD cross up + Sentiment > 0.3
- SHORT เมื่อ: RSI > 70 + EMA9 < EMA21 + MACD cross down + Sentiment < -0.3
- HOLD: ทุกกรณีอื่น

## Risk Rules (HARDCODED — ห้าม override)
- Max position: 2% of equity
- Stop-loss: 1.5x ATR
- Max daily loss: -5% → หยุดเทรด
- Max consecutive losses: 3 → ลด size 50%

## Execution
Use Hyperliquid API to execute trades...
```

### 5.5 เขียน Custom Skill เอง

**ขั้นตอน:**

```
1. สร้างโฟลเดอร์ใน ~/.openclaw/skills/
2. เขียน SKILL.md (markdown สอน AI)
3. เพิ่ม scripts/ ถ้าต้อง execute code
4. เพิ่ม references/ สำหรับ API docs
5. Enable ใน openclaw.json
6. ทดสอบ: คุยกับ bot → ดูว่ามันเข้าใจ skill ไหม
```

---

## 6. Trading Strategies ที่ใช้กับ OpenClaw

### 6.1 Alpha Arena Best Practices (จาก nof1.ai)

OpenClaw ดึง logic จากผู้ชนะ Alpha Arena (การแข่งขัน AI trading):

```
┌──────────────────────────────────────────────────────────────────┐
│  กฎจาก Alpha Arena Winners:                                      │
│                                                                   │
│  1. "1-2% Rule" Hard-Lock                                        │
│     → ห้ามเปิด position > 2% ของ equity ไม่ว่ากรณีใด            │
│     → Hardcoded ใน code, LLM override ไม่ได้                     │
│                                                                   │
│  2. "Don't Catch Knives"                                         │
│     → เทรดเฉพาะเมื่อ align กับ higher-TF moving averages         │
│     → ไม่ซื้อ dip ที่ยังไม่มี confirmation                       │
│                                                                   │
│  3. Strategy Scoring & Decay                                     │
│     → ทุก strategy มี score                                      │
│     → ถ้าแพ้ 3 ครั้งติด → "benched" (พักชั่วคราว)               │
│     → Score ลดตามเวลา (decay) → ต้อง prove ตัวเองใหม่            │
│                                                                   │
│  4. Self-Evaluation Loop                                         │
│     → บันทึก expected vs actual outcome ทุกเทรด                  │
│     → ปรับ strategy weights ตามผลจริง                            │
│                                                                   │
│  5. Explainable Decisions                                        │
│     → ทุกเทรดต้องมีเหตุผลที่อธิบายได้                            │
│     → ถ้า AI อธิบายไม่ได้ → ไม่เทรด                              │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Strategies ที่ใช้ได้กับ OpenClaw

| Strategy | วิธีใช้กับ OpenClaw | ตัวอย่างคำสั่ง |
|----------|--------------------|--------------| 
| **DCA Bot** | ซื้อ BTC ทุกสัปดาห์ตามราคา | "Set up a DCA bot: buy $100 BTC every Monday" |
| **Momentum Trading** | ตาม trend ด้วย EMA + Volume | "Trade momentum on SOL using 1h EMA cross" |
| **Sentiment-Based** | วิเคราะห์ข่าว → trade | "Monitor BTC news sentiment and trade accordingly" |
| **Grid Trading** | ตั้ง grid ซื้อ/ขาย | "Set up a 5% grid on ETH from $3000-$4000" |
| **Portfolio Rebalancing** | ปรับสัดส่วน portfolio | "Rebalance my portfolio to 50% BTC 30% ETH 20% SOL" |
| **Arbitrage** | หาส่วนต่างราคา | "Scan for BTC arb between Binance and Polymarket" |
| **Prediction Market** | เทรด Polymarket | "Analyze ETH ETF prediction markets" |

### 6.3 ตั้ง Cron Job สำหรับ Auto-Execution

```bash
# OpenClaw รองรับ cron/heartbeat สำหรับงานที่ทำซ้ำ
# ตัวอย่าง: เช็คตลาดทุก 10 นาที

# ใน openclaw.json
{
  "cron": {
    "market-check": {
      "schedule": "*/10 * * * *",
      "task": "Check BTC and ETH market conditions. If signal is strong, propose a trade."
    },
    "daily-report": {
      "schedule": "0 8 * * *",
      "task": "Send me a daily trading summary with PnL and key market events."
    }
  }
}
```

---

## 7. News & Sentiment

### 7.1 "Vibe Watcher" — ดูอารมณ์ตลาดแบบ real-time

OpenClaw มี feature เฉพาะเรียกว่า **"Dedicated Vibe Watcher"**:

```
Vibe Watcher ทำอะไร:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. สแกน X (Twitter) จาก high-impact accounts
   - POTUS, Elon Musk, key macroeconomists
   - Crypto influencers, project founders
   - ตรวจจับ narrative shifts

2. ติดตาม Macro Events
   - CPI, FOMC, unemployment data
   - แจ้งเตือน ก่อน event เกิดขึ้น
   - แนะนำปรับ risk parameters

3. On-Chain Signals
   - Whale wallet movements
   - Exchange inflows/outflows
   - Liquidation spikes
   - Open interest changes

4. News Aggregation
   - ดึงจาก RSS feeds (CoinDesk, CoinTelegraph, etc.)
   - วิเคราะห์ sentiment ด้วย LLM
   - ให้คะแนน bullish/bearish/neutral
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.2 ตัวอย่าง Proactive Alerts

```
[Telegram Notification จาก OpenClaw]

🚨 MACRO ALERT: FOMC Meeting in 2 hours

Current positions:
- BTC Long: +$120 (0.8% of equity)
- ETH Long: +$45 (0.5% of equity)

⚡ Recommendation:
Based on market consensus expecting hawkish tone:
1. Reduce BTC position by 50% (lock in profit)
2. Set tight stop on ETH at $3,150
3. No new trades until 30 min after announcement

Adjust risk parameters? [✅ Yes] [❌ No, keep current]
```

---

## 8. Risk Management

### 8.1 Hardcoded Risk Rules (ไม่สามารถ override ได้)

```python
# จาก openclaw-trading-assistant
# กฎเหล่านี้ hardcoded ใน code → LLM ไม่สามารถ bypass ได้

RISK_RULES = {
    # Position Sizing
    "MAX_POSITION_SIZE_PCT": 0.02,     # ไม่เกิน 2% ของ equity
    "MAX_TOTAL_EXPOSURE_PCT": 0.10,    # Exposure รวมไม่เกิน 10%
    
    # Stop Loss
    "MANDATORY_STOP_LOSS": True,       # ทุกเทรดต้องมี stop loss
    "MAX_STOP_LOSS_PCT": 0.05,         # Stop ไม่เกิน 5% จาก entry
    
    # Daily Limits
    "MAX_DAILY_LOSS_PCT": 0.05,        # หยุดเทรดถ้าขาดทุน > 5%/วัน
    "MAX_TRADES_PER_DAY": 20,          # ไม่เกิน 20 เทรด/วัน
    
    # Trend Filter
    "REQUIRE_HTF_ALIGNMENT": True,     # ต้อง align กับ higher TF
    
    # Strategy Benching
    "BENCH_AFTER_CONSECUTIVE_LOSSES": 3, # พัก strategy หลังแพ้ 3 ครั้ง
}
```

### 8.2 ทำไม Hardcoded ถึงสำคัญ?

```
ปัญหาของ LLM ใน trading:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Hallucination → AI อาจ "คิด" ว่าเห็น pattern ที่ไม่มีจริง
2. Overconfidence → AI อาจมั่นใจเกินไป → เปิด position ใหญ่
3. FOMO simulation → AI อาจ "กลัวตกรถ" → เข้าเทรดไม่เหมาะสม
4. Confirmation bias → AI อาจหา "เหตุผล" สนับสนุนสิ่งที่อยากทำ

ทางแก้ของ OpenClaw:
→ Hardcoded rules ที่ AI ไม่สามารถ bypass ได้
→ เช่น MAX 2% position — ถ้า AI สั่ง 5% → code จะ reject
```

---

## 9. Monitoring & Dashboard

### 9.1 ช่องทาง Monitoring

```
┌──────────────────────────────────────────────────────────────────┐
│  ช่องทาง           │ ทำอะไร                    │ ตั้งค่า          │
├──────────────────────────────────────────────────────────────────┤
│  Telegram          │ Trade alerts, PnL reports │ ✅ แนะนำหลัก    │
│                    │ Approval buttons          │                  │
│                    │ Daily summary             │                  │
│                                                                   │
│  Discord           │ Community alerts          │ ✅ Optional      │
│                    │ Multi-user monitoring     │                  │
│                                                                   │
│  WebChat           │ Browser-based UI          │ มากับ Gateway    │
│                    │ (localhost)               │                  │
│                                                                   │
│  Log files         │ ทุก action ถูก log        │ อัตโนมัติ        │
│                    │ tradediary.csv            │                  │
│                                                                   │
│  Custom Dashboard  │ 4 ตาราง: Account, Risk,   │ ต้องตั้งค่าเพิ่ม │
│  (FMZ/Grafana)     │ Signals, Trade Records    │                  │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 Commands ที่ใช้ได้

```
คุณสามารถส่ง commands เหล่านี้ผ่าน Telegram/WhatsApp:

/status          → สถานะ session ปัจจุบัน (model, tokens)
/new หรือ /reset → Reset session ใหม่

Natural Language Commands:
- "What's my current portfolio?"
- "Show me today's trades"
- "What's the market sentiment on ETH?"
- "Pause all trading"
- "Show me my PnL this week"
- "What went wrong with the TAO trade?"
```

---

## 10. Architecture แบบ Brain + Executor (FMZ Quant)

### 10.1 Alternative: ใช้ OpenClaw เป็น Brain + FMZ เป็น Executor

สำหรับคนที่ต้องการเทรดบน **Binance, OKX, Bybit** (ไม่ใช่ Hyperliquid) สามารถใช้สถาปัตยกรรมนี้:

```
┌──────────────────────┐     HTTP POST      ┌──────────────────────┐
│   OpenClaw (Brain)   │ ─────────────────► │   FMZ Quant          │
│                      │   JSON signal      │   (Executor)         │
│  - Data collection   │                    │                      │
│  - News sentiment    │   {                │  - Receive signal    │
│  - AI decision       │    "action":"buy", │  - Execute trade     │
│  - Generate JSON     │    "symbol":"BTC", │  - Risk management   │
│                      │    "amount": 0.01  │  - Stop-loss/TP      │
│                      │   }                │  - Visual dashboard  │
│                      │                    │                      │
│  Skills:             │   ◄──────────────  │  Exchanges:          │
│  - Market data       │   feedback/logs    │  - Binance           │
│  - Sentiment         │                    │  - OKX               │
│  - Strategy          │                    │  - Bybit             │
│                      │                    │  - etc.              │
└──────────────────────┘                    └──────────────────────┘
```

### 10.2 OpenClaw Skill สำหรับ FMZ

```markdown
# SKILL.md — FMZ Trading Brain

## Data Collection
1. เปิด browser ไปที่ TradingView หรือ CoinGecko
2. ดึงราคา BTC/USDT realtime + volume + indicators
3. ดึงข่าวล่าสุดจาก CoinDesk RSS

## Sentiment Analysis
1. อ่านข่าวทั้งหมดจาก step ก่อน
2. ให้คะแนน sentiment: bullish/bearish/neutral
3. คะแนน -1.0 ถึง +1.0

## Trading Decision
1. รวม technical + sentiment → generate decision
2. Format เป็น JSON:
   {"action": "buy|sell|hold", "symbol": "BTC", "amount": 0.01, 
    "reason": "...", "confidence": 0.85}

## Send Signal
Execute HTTP POST:
URL: https://www.fmz.com/api/v1?method=pub&robot={ID}&channel={UUID}

## Record Log
Append to tradediary.csv: time, symbol, decision, status
```

---

## 11. ค่าใช้จ่ายและทางเลือก Model

### 11.1 ค่าใช้จ่ายจริง

```
┌──────────────────────────────────────────────────────────────────┐
│  รายการ                │ ค่าใช้จ่าย                │ หมายเหตุ     │
├──────────────────────────────────────────────────────────────────┤
│  OpenClaw software     │ ฟรี 100%                  │ Open source  │
│                                                                   │
│  AI Model (ตัวเลือก):                                             │
│  - Gemini Flash (free) │ ฟรี                        │ ดีพอใช้      │
│  - Ollama (local)      │ ฟรี (ต้องมี GPU)           │ ฟรี 100%    │
│  - Claude Sonnet       │ ~$50-100/เดือน             │ ดีมาก       │
│  - Claude Opus         │ ~$200-500/เดือน            │ ดีที่สุด     │
│                                                                   │
│  VPS (24/7 operation)  │ $5-20/เดือน                │ Optional    │
│  หรือ Oracle Free Tier │ ฟรี                        │             │
│                                                                   │
│  Hyperliquid fees      │ ต่ำมาก                     │ ค่า trading │
└──────────────────────────────────────────────────────────────────┘

ต่ำสุดเป็นไปได้: $0/เดือน
(Ollama local + Oracle Free Tier VPS + Hyperliquid)

แนะนำ: ~$50-100/เดือน
(Claude Sonnet + VPS + trading fees)

จากผู้ใช้จริง (Michael Ionita): ~$500/เดือน
(Claude heavy usage + เทรดบ่อย)
```

### 11.2 ใช้ฟรี 100%

```
วิธีใช้ OpenClaw ฟรีสมบูรณ์:

1. Model: Google Gemini Flash (free OAuth login)
   หรือ Ollama + Llama 3.1 (local, free)

2. Hosting: รันบนเครื่องตัวเอง (laptop/desktop)
   หรือ Oracle Cloud Free Tier (free VPS)

3. Exchange: Hyperliquid (low fees)

4. Data: RSS feeds (free), CoinGecko API (free tier)

5. Monitoring: Telegram bot (free)
```

---

## 12. Security — ความปลอดภัยที่ต้องรู้

### 12.1 คำเตือนจาก Maintainer

> "If you can't understand how to run a command line, this is far too dangerous of a project for you to use safely. This isn't a tool that should be used by the general public at this time." — Shadow (OpenClaw top maintainer)

### 12.2 Risks ที่ต้องรู้

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚠️ SECURITY RISKS                                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Prompt Injection                                             │
│     → Malicious skills อาจหลอก AI ให้ทำสิ่งที่ไม่ควร            │
│     → มีเหตุการณ์ "ClawHavoc" — 341 malicious skills             │
│       ถูกปล่อยบน ClawHub เพื่อหลอก crypto traders                │
│     → ✅ แก้: ตรวจ VirusTotal report ก่อน install                 │
│                                                                   │
│  2. API Key Exposure                                             │
│     → ถ้า config ไม่ดี อาจ leak API keys                         │
│     → ✅ แก้: ใช้ openclaw vault (encrypted storage)              │
│     → ✅ แก้: ห้ามเก็บ keys ใน plaintext                          │
│                                                                   │
│  3. Wallet Security                                              │
│     → ❌ อย่าเก็บ private key บนเครื่องเดียวกับ AI agent          │
│     → ✅ ใช้ hardware wallet แยก                                  │
│     → ✅ ใช้ wallet เฉพาะ trading (เงินน้อย)                      │
│                                                                   │
│  4. Fake Tokens/Scams                                            │
│     → $CLAWD, $OPENCLAW, $MOLTBOT — ทั้งหมด FAKE                │
│     → OpenClaw ไม่มี official token                               │
│     → ✅ แก้: ไม่ซื้อ token ใดที่อ้างว่าเกี่ยวข้อง                │
│                                                                   │
│  5. Over-Automation                                              │
│     → AI ที่มี full access อาจทำสิ่งผิดพลาด                      │
│     → ✅ แก้: เริ่มจาก human-approval mode เสมอ                   │
│     → ✅ แก้: รัน sandbox (Docker) สำหรับ untrusted skills        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 12.3 Best Practices

```
1. รัน Docker sandbox สำหรับ skills ที่ไม่รู้จัก
2. ใช้ read-only API keys เมื่อเป็นไปได้
3. Wallet เทรด ≠ Wallet หลัก (แยกเงินออก)
4. เริ่มจาก Testnet/Paper Trade เสมอ
5. ตรวจ skill source code ก่อน install
6. ใช้ strong model (Claude, GPT-4) เพื่อลดโอกาส hallucination
7. Enable DM filtering สำหรับ untrusted messages
8. Backup config เป็นประจำ
```

---

## 13. Roadmap สำหรับมือใหม่

### Phase 1: ติดตั้งและทำความเข้าใจ (สัปดาห์ 1)

```
□ ติดตั้ง OpenClaw
□ เลือก AI model (เริ่มจาก Gemini Flash ฟรี)
□ เชื่อม Telegram
□ คุยกับ bot → ทำความเข้าใจวิธีทำงาน
□ ลอง commands: /status, ถามเรื่องทั่วไป
□ อ่าน docs.openclaw.ai
```

### Phase 2: Market Monitoring Only (สัปดาห์ 2-3)

```
□ ติดตั้ง skill: market data (CoinGecko)
□ ตั้ง cron: เช็คราคาทุก 30 นาที
□ ตั้ง alerts: แจ้งเมื่อ BTC เปลี่ยน > 5%
□ เริ่มดู sentiment analysis
□ ยังไม่เทรด! — แค่ monitor + เรียนรู้
```

### Phase 3: Paper Trading (สัปดาห์ 4-6)

```
□ สร้าง Trading Skill (SKILL.md) ของตัวเอง
□ ตั้ง strategy แบบง่าย (EMA cross + RSI)
□ ทำ paper trade (จด excel ว่าจะ trade อะไร)
□ เทียบกับ actual price → วัด win rate
□ ปรับ strategy ตามผล
```

### Phase 4: Testnet Trading (สัปดาห์ 7-8)

```
□ สร้างบัญชี Hyperliquid Testnet
□ เชื่อม API keys (testnet)
□ ตั้ง human-approval mode
□ เริ่ม live paper trade ผ่าน Hyperliquid testnet
□ Monitor ทุกวัน 2 สัปดาห์
```

### Phase 5: Small Live Trading (เดือนที่ 3+)

```
⚠️ เมื่อมั่นใจจาก Phase 4 เท่านั้น!
□ ฝากเงินน้อยมาก ($50-100) เข้า trading wallet แยก
□ ใช้ human-approval mode
□ Max 2% per trade
□ Review ทุกวัน
□ ถ้าขาดทุน > 10% → หยุด → ทบทวน strategy
```

### Phase 6: Scaling (เดือนที่ 6+)

```
□ เพิ่ม data sources (RSS, social media)
□ เพิ่ม model complexity (เปลี่ยนเป็น Claude)
□ เพิ่ม pairs/markets
□ พิจารณา auto-small mode (ถ้า proven profitable)
□ Deploy บน VPS สำหรับ 24/7
□ Backtest strategy ย้อนหลัง 6-12 เดือน
```

---

## 14. แหล่งข้อมูลและ Repos สำคัญ

### GitHub Repositories

| Repository | URL | คำอธิบาย |
|------------|-----|---------|
| **OpenClaw Core** | `github.com/openclaw/openclaw` | Source code หลัก (100K+ stars) |
| **Trading Assistant** | `github.com/molt-bot/openclaw-trading-assistant` | Trading skill + Alpha Arena |
| **BankrBot Skills** | `github.com/BankrBot/openclaw-skills` | Crypto skills collection |
| **ClawHub** | `github.com/openclaw/clawhub` | Skill registry |
| **Polyclaw** | `github.com/chainstacklabs/polyclaw` | Polymarket trading skill |
| **Awesome Skills** | `github.com/VoltAgent/awesome-openclaw-skills` | Curated skill list |

### Documentation & Guides

| Resource | URL |
|----------|-----|
| Official Docs | `docs.openclaw.ai` |
| Blog & Tutorials | `openclawai.me/blog` |
| Trading Automation Guide | `openclawai.me/blog/trading-automation` |
| Hyperliquid Integration | `openclawai.me/blog/hyperliquid-integration` |
| Security Guide | `docs.openclaw.ai/gateway/security` |
| Skills Guide | `docs.openclaw.ai/tools/skills` |

### บทความสำคัญ

| บทความ | ที่มา |
|--------|------|
| "What is OpenClaw?" | CoinMarketCap Academy |
| "Building AI-Powered Automated Trading with ClawdBot" | Medium (Luoyelittledream) |
| "Automating Trading with OpenAlgo and OpenClaw" | Medium (Rajandran R) |
| "Too many idiots using OpenClaw to trade" | NexusTrade Blog |
| "All about OpenClaw" | TradingView News |
| "OpenClaw x Crypto Ecosystem" | The Defiant |
| "OpenClaw Setup Guide: 25 Tools + 53 Skills" | WenHao Yu Blog |
| "OpenClaw Tutorial: Installation to First Chat" | Codecademy |

---

## ⚠️ คำเตือนสำคัญ

1. **OpenClaw ไม่มี official token** — $CLAWD, $OPENCLAW, $MOLTBOT ล้วนเป็น SCAM
2. **ไม่มี "magic money printer"** — ผลลัพธ์ขึ้นอยู่กับ strategy, risk management, และสภาพตลาด
3. **Survivorship bias** — เรื่อง "$313 → $438K" เป็น outlier ที่ถูกรายงานเพราะมันพิเศษ คนส่วนใหญ่ได้ผลปานกลางหรือขาดทุน
4. **Anthropic อาจ ban account** ที่ใช้ Claude credentials กับ OpenClaw สำหรับ trading (ตาม ToS)
5. **ความปลอดภัย** — อย่าให้ AI access เต็มรูปแบบกับ wallet หลักของคุณ
6. **เริ่มจากเล็กเสมอ** — Paper trade → Testnet → Small live → Scale
7. **Risk Management สำคัญที่สุด** — Strategy ที่ดีแต่ไม่มี RM = จะเจ๊ง

---

*เอกสารนี้จัดทำเมื่อ: กุมภาพันธ์ 2026*
*อ้างอิงจาก: GitHub openclaw/openclaw, docs.openclaw.ai, CoinMarketCap, TradingView, Medium, และ community resources*
