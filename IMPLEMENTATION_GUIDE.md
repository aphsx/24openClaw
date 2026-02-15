# Multi-Agent Trading Bot - Complete Implementation Guide

## สารบัญ
1. [Phase 1: Foundation Files](#phase-1-foundation-files)
2. [Phase 2: Specialist Agents](#phase-2-specialist-agents)
3. [Phase 3: Manager & Risk](#phase-3-manager--risk)
4. [Phase 4: Learning System](#phase-4-learning-system)
5. [Phase 5: Integration](#phase-5-integration)
6. [Phase 6: Configuration](#phase-6-configuration)

---

## Phase 1: Foundation Files

### 1.1 `src/ai/agents/base_agent.py`

```python
"""
Base Agent Class - Abstract base for all specialist agents
Extracts provider calling logic from brain.py for reuse
"""
import json
import time
from typing import Any, Dict, Optional
import httpx
from src.utils.logger import log

# Reuse provider configs from brain.py
AI_PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "headers_fn": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
}


class BaseAgent:
    """
    Abstract base class for all specialist agents.
    Handles provider API calls and JSON parsing.
    """

    def __init__(
        self,
        agent_name: str,
        provider: str,
        model: str,
        api_key: str,
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
        timeout: float = 12.0,
    ):
        self.agent_name = agent_name
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def analyze(self, data: dict) -> dict:
        """
        Main entry point for analysis.
        Subclasses should override this to build specific prompts.
        Returns: {agent: str, ...agent-specific fields, error: str (optional)}
        """
        raise NotImplementedError("Subclasses must implement analyze()")

    async def _call_provider(self, user_prompt: str) -> tuple:
        """
        Call AI provider API.
        Returns: (response_text, usage_dict, latency_ms)
        """
        provider_config = AI_PROVIDERS.get(self.provider)
        if not provider_config:
            log.error(f"[{self.agent_name}] Unknown provider: {self.provider}")
            return self._error_response(f"Unknown provider: {self.provider}"), {}, 0

        start_time = time.time()
        try:
            if self.provider == "claude":
                content, usage = await self._call_claude(user_prompt, provider_config)
            else:
                content, usage = await self._call_openai_compatible(user_prompt, provider_config)

            latency_ms = int((time.time() - start_time) * 1000)
            return content, usage, latency_ms

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            log.error(f"[{self.agent_name}] API call failed: {e}")
            return self._error_response(str(e)), {}, latency_ms

    async def _call_openai_compatible(self, user_prompt: str, config: dict) -> tuple:
        """Call OpenAI-compatible API (Groq, DeepSeek, Gemini, Kimi)."""
        headers = config["headers_fn"](self.api_key)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(config["url"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        usage = data.get("usage", {})
        return content, usage

    async def _call_claude(self, user_prompt: str, config: dict) -> tuple:
        """Call Anthropic Claude API."""
        headers = config["headers_fn"](self.api_key)
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": self.temperature,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(config["url"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [{}])[0].get("text", "{}")
        usage = data.get("usage", {})
        # Map Claude usage keys to standard
        usage = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
        return content, usage

    def _parse_json(self, raw: str) -> dict:
        """
        Parse AI response JSON, handling potential formatting issues.
        Reuses logic from brain.py.
        """
        try:
            # Try direct JSON parse
            parsed = json.loads(raw)
            return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        try:
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

        # Try finding JSON object in text
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        log.error(f"[{self.agent_name}] Failed to parse response: {raw[:200]}")
        return {"error": "JSON parse failed", "raw": raw[:200]}

    def _error_response(self, error_msg: str) -> str:
        """Return error as JSON string."""
        return json.dumps({"error": error_msg, "agent": self.agent_name})
```

### 1.2 `src/ai/provider_pool.py`

```python
"""
Provider Pool - Manages multiple AI provider configs with rate limiting
"""
from typing import Dict, Any
from dataclasses import dataclass
from src.utils.config import settings
from src.utils.logger import log


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    provider: str
    model: str
    api_key: str
    temperature: float = 0.2
    max_tokens: int = 800
    timeout: float = 12.0


class ProviderPool:
    """
    Manages AI provider configurations for all agents.
    Loads from settings and provides configs on demand.
    """

    def __init__(self):
        self.configs: Dict[str, ProviderConfig] = {}
        self._load_configs()

    def _load_configs(self):
        """Load all agent provider configs from settings."""
        # Technical Agent
        self.configs["technical"] = ProviderConfig(
            provider=settings.AGENT_TECHNICAL_PROVIDER,
            model=settings.AGENT_TECHNICAL_MODEL,
            api_key=settings.AGENT_TECHNICAL_API_KEY,
            temperature=0.2,
            max_tokens=800,
            timeout=settings.AGENT_SPECIALIST_TIMEOUT,
        )

        # Sentiment Agent
        self.configs["sentiment"] = ProviderConfig(
            provider=settings.AGENT_SENTIMENT_PROVIDER,
            model=settings.AGENT_SENTIMENT_MODEL,
            api_key=settings.AGENT_SENTIMENT_API_KEY,
            temperature=0.2,
            max_tokens=800,
            timeout=settings.AGENT_SPECIALIST_TIMEOUT,
        )

        # Whale Agent
        self.configs["whale"] = ProviderConfig(
            provider=settings.AGENT_WHALE_PROVIDER,
            model=settings.AGENT_WHALE_MODEL,
            api_key=settings.AGENT_WHALE_API_KEY,
            temperature=0.2,
            max_tokens=800,
            timeout=settings.AGENT_SPECIALIST_TIMEOUT,
        )

        # Macro Agent
        self.configs["macro"] = ProviderConfig(
            provider=settings.AGENT_MACRO_PROVIDER,
            model=settings.AGENT_MACRO_MODEL,
            api_key=settings.AGENT_MACRO_API_KEY,
            temperature=0.2,
            max_tokens=800,
            timeout=settings.AGENT_SPECIALIST_TIMEOUT,
        )

        # Manager Agent
        self.configs["manager"] = ProviderConfig(
            provider=settings.AGENT_MANAGER_PROVIDER,
            model=settings.AGENT_MANAGER_MODEL,
            api_key=settings.AGENT_MANAGER_API_KEY,
            temperature=0.3,
            max_tokens=1500,
            timeout=settings.AGENT_MANAGER_TIMEOUT,
        )

    def get_config(self, agent_name: str) -> ProviderConfig:
        """Get provider config for a specific agent."""
        config = self.configs.get(agent_name)
        if not config:
            log.warning(f"No config for agent '{agent_name}', using default")
            return ProviderConfig(
                provider="groq",
                model="llama-3.3-70b-versatile",
                api_key=settings.AI_API_KEY,
            )
        return config

    def get_all_configs(self) -> Dict[str, ProviderConfig]:
        """Get all provider configs."""
        return self.configs


# Singleton
provider_pool = ProviderPool()
```

---

## Phase 2: Specialist Agents

### 2.1 `src/ai/prompts_v2.py`

```python
"""
Multi-Agent Prompts - System prompts for all 5 agents
All prompts in Thai (matching existing system language)
"""

# ===== TECHNICAL ANALYST =====
TECHNICAL_AGENT_PROMPT = """คุณคือ Technical Analyst ผู้เชี่ยวชาญด้านการวิเคราะห์กราฟและ indicators
หน้าที่: วิเคราะห์ indicators ทั้งหมด (5m/15m/1h/4h) และบอก signal ที่ชัดเจน

## กฎการวิเคราะห์:
1. ดูเฉพาะตัวเลข indicators เท่านั้น — ห้ามคิดเรื่องข่าว sentiment whale
2. หา confluence: ถ้าหลาย indicators ชี้ทางเดียวกัน → signal แข็งแรง
3. Multi-timeframe confirmation: 5m entry signal + 15m/1h confirm → ดีกว่า 5m alone
4. ระบุ support/resistance ที่สำคัญ (จาก VWAP, BB, EMA200, Supertrend)
5. ให้คะแนนความมั่นใจ 1-10 ต่อเหรียญ

## ตอบเป็น JSON เท่านั้น:
{
  "agent": "technical",
  "signals": {
    "BTCUSDT": {
      "bias": "LONG|SHORT|NEUTRAL",
      "strength": 7,
      "key_levels": {"support": 96500, "resistance": 99200},
      "entry_trigger": "อธิบายสั้นๆ setup ที่เห็น",
      "invalidation": "ถ้าเกิดอะไร setup เสีย"
    }
  },
  "cross_coin_notes": "BTC+ETH aligned bullish, SOL lagging..."
}

ห้ามพูดยาว ตอบแค่ JSON ไม่ต้องมี markdown หรือคำอธิบายนอก JSON"""


# ===== SENTIMENT ANALYST =====
SENTIMENT_AGENT_PROMPT = """คุณคือ Sentiment Analyst ผู้เชี่ยวชาญด้านการอ่านข่าว social sentiment market mood
หน้าที่: อ่านข่าว + Fear/Greed + funding rate แล้วบอกว่า sentiment ตลาดเป็นยังไง

## กฎการวิเคราะห์:
1. ดูเฉพาะข่าว Fear/Greed funding rate — ห้ามคิดเรื่อง indicators
2. ข่าวบวก (ETF inflow, adoption, institutional buying) → bullish
3. ข่าวลบ (hack, regulation, FUD) → bearish
4. Fear/Greed: <25 = Extreme Fear (contrarian buy), >75 = Extreme Greed (careful)
5. Funding rate สูง (>0.02%) = long ล้น อันตราย / ต่ำมาก (<-0.01%) = short ล้น
6. ระบุข่าวสำคัญที่มี impact ต่อแต่ละเหรียญ

## ตอบเป็น JSON เท่านั้น:
{
  "agent": "sentiment",
  "market_mood": "cautious_optimism|fear|greed|neutral",
  "fear_greed_interpretation": "68 Greed - not extreme, room to run",
  "news_impact": {
    "BTCUSDT": {
      "impact": "bullish|bearish|neutral",
      "catalyst": "ข่าวสำคัญที่เห็น",
      "urgency": "high|medium|low"
    }
  },
  "funding_signal": "ETHUSDT funding 0.03% overleveraged longs"
}

ห้ามพูดยาว ตอบแค่ JSON"""


# ===== WHALE ANALYST =====
WHALE_AGENT_PROMPT = """คุณคือ Whale/Smart Money Analyst ผู้เชี่ยวชาญการอ่าน order flow
หน้าที่: ดู taker ratio, top traders, open interest, order book แล้วบอกว่า whale กำลังทำอะไร

## กฎการวิเคราะห์:
1. ดูเฉพาะ whale data — ห้ามคิดเรื่อง indicators หรือข่าว
2. Taker Buy/Sell > 1.2 = whale ซื้อ, < 0.8 = whale ขาย
3. Top Trader Long > 60% = smart money long, < 40% = smart money short
4. OI เพิ่ม + ราคาขึ้น = bullish continuation / OI เพิ่ม + ราคาลง = bearish continuation
5. OI ลง + ราคาขึ้น = short squeeze / OI ลง + ราคาลง = long squeeze
6. Bid wall ใหญ่ = แนวรับ / Ask wall ใหญ่ = แนวต้าน
7. ให้คะแนนความมั่นใจ 1-10

## ตอบเป็น JSON เท่านั้น:
{
  "agent": "whale",
  "signals": {
    "BTCUSDT": {
      "smart_money_bias": "accumulating|distributing|neutral",
      "taker_signal": "buy_pressure (1.35)|sell_pressure (0.75)",
      "top_traders": "62% long - following smart money",
      "oi_change": "rising = new money entering",
      "key_walls": ["Bid wall 96500 (15.2 BTC)", "Ask wall 99800"],
      "confidence": 8
    }
  },
  "aggregate_flow": "Net institutional buying across majors"
}

ห้ามพูดยาว ตอบแค่ JSON"""


# ===== MACRO ANALYST =====
MACRO_AGENT_PROMPT = """คุณคือ Macro/Regime Analyst ผู้เชี่ยวชาญด้าง market phase และภาพใหญ่
หน้าที่: ดู regime (trending/ranging/volatile), 4h timeframe, BTC dominance แล้วบอก strategy ที่เหมาะสม

## กฎการวิเคราะห์:
1. Market regime จะบอกว่าควรเล่นแบบไหน:
   - trending_up: Trend-following, buy dips
   - trending_down: Short rallies, sell strength
   - ranging: Mean reversion, fade extremes
   - volatile: Reduce size or skip
2. BTC dominance: ถ้า BTC ขึ้นแรงกว่า alts = BTC dominance เพิ่ม = alts จะตาม 2-4h ข้างหน้า
3. ดู 4h trend เป็นหลัก — short term noise ไม่สำคัญ
4. Cross-coin correlation: ถ้าทุกเหรียญขึ้นพร้อม = low risk / ถ้าแยกทิศ = high risk
5. แนะนำ strategy class ที่เหมาะสม

## ตอบเป็น JSON เท่านั้น:
{
  "agent": "macro",
  "market_phase": "early_bull|late_bull|early_bear|late_bear|ranging",
  "btc_dominance_signal": "BTC leading, alts will follow",
  "regime_summary": {
    "trending_up": ["BTCUSDT", "ETHUSDT"],
    "ranging": ["XRPUSDT"],
    "volatile": ["SOLUSDT"]
  },
  "strategy_recommendation": "Trend-follow BTC/ETH, avoid ranging coins",
  "correlated_risks": "All majors >0.8 correlation = single point of failure"
}

ห้ามพูดยาว ตอบแค่ JSON"""


# ===== MANAGER AGENT =====
MANAGER_AGENT_PROMPT = """คุณคือ Chief Trading Officer ที่รับรายงานจาก 4 specialists แล้วตัดสินใจสุดท้าย

## บทบาท:
คุณได้รับรายงานจาก:
1. Technical Analyst (indicators, charts)
2. Sentiment Analyst (news, fear/greed)
3. Whale Analyst (order flow, smart money)
4. Macro Analyst (regime, big picture)

+ ข้อมูล backtesting (similar setups ในอดีตชนะกี่%)
+ ข้อมูล learning (เทรดล่าสุดเป็นยังไง AI calibrated ดีไหม)

## กฎการตัดสินใจ (CRITICAL):
1. **Agreement Check**: นับว่า agents เห็นตรงกันกี่ตัว
   - 4/4 agree → confidence 80-90
   - 3/4 agree → confidence 70-80
   - 2/2 split → ระวัง มองว่า contradiction

2. **Contradiction Resolution**:
   - ถ้า Technical=LONG แต่ Sentiment=bearish → ดู Whale+Macro เป็นตัวชี้ขาด
   - ถ้า 2v2 split → SKIP เว้นแต่ backtest win rate >75%

3. **Quality > Quantity** (Alpha Arena lesson):
   - Winners เทรด <3 ครั้ง/วัน
   - ห้ามเทรดมากกว่า 3 เหรียญต่อ cycle
   - Confidence <70 → SKIP

4. **Backtest Weight**:
   - ถ้า backtest win rate >70% + sample >10 → เพิ่ม confidence +10
   - ถ้า backtest <50% → ลด confidence -15 หรือ SKIP

5. **Learning Integration**:
   - ถ้า strategy score <50 → ลดขนาด position
   - ถ้า consecutive losses >=2 → เพิ่มความระวัง confidence -5
   - ถ้า symbol นั้นเทรดแพ้บ่อย → หลีกเลี่ยง

6. **Position Management**:
   - มี position กำไร >12% → ดูว่ายังไปต่อไหวไหม
   - มี position ขาดทุน → ประเมินว่าจะกลับไหม

7. **Risk Limits**:
   - Max 3 positions พร้อมกัน
   - ไม่ counter-trend เว้นแต่ confidence 85+

## ตอบเป็น JSON เท่านั้น:
{
  "market_view": "สรุปสถานการณ์โดยรวมสั้นๆ",
  "agent_consensus": {
    "aligned": ["BTCUSDT_LONG: 4/4 agents bullish"],
    "contradictions": ["SOLUSDT: tech=LONG but sent=bearish"],
    "resolution": "อธิบายว่าจัดการ contradiction ยังไง"
  },
  "actions": [
    {
      "symbol": "BTCUSDT",
      "action": "OPEN_LONG|OPEN_SHORT|CLOSE|HOLD|SKIP",
      "margin_usdt": 10,
      "sl_price": 96500,
      "tp_price": 99200,
      "confidence": 82,
      "reason": "4/4 agents bullish, backtest 73% win rate"
    }
  ]
}

**ห้ามเทรดเยอะ เทรดน้อยแต่แม่น คือหัวใจสำคัญ**
ตอบแค่ JSON ไม่ต้องมี markdown"""


def build_technical_prompt(data: dict) -> str:
    """Build prompt for Technical Agent."""
    coins = data.get("coins", {})
    positions = data.get("positions", [])

    # Format positions
    pos_text = "ไม่มี position"
    if positions:
        pos_lines = [f"{p['symbol']} {p['side']} @ {p.get('entry_price', 0)} (PnL: {p.get('unrealized_pnl_pct', 0):+.1f}%)"
                     for p in positions]
        pos_text = ", ".join(pos_lines)

    # Format coins indicators
    coins_text = []
    for symbol, coin_data in coins.items():
        ind_5m = coin_data.get("indicators_5m", {})
        ind_15m = coin_data.get("indicators_15m", {})
        ind_1h = coin_data.get("indicators_1h", {})
        ind_4h = coin_data.get("indicators_4h", {})
        regime = coin_data.get("regime", "unknown")
        price = coin_data.get("price", 0)

        coins_text.append(f"""
{symbol} (regime: {regime}, price: {price})
5m: EMA9={ind_5m.get('ema9',0):.0f} EMA21={ind_5m.get('ema21',0):.0f} EMA55={ind_5m.get('ema55',0):.0f} RSI={ind_5m.get('rsi14',0):.0f} ADX={ind_5m.get('adx',0):.0f} MACD_hist={ind_5m.get('macd',{}).get('histogram',0):.1f} StochRSI_K={ind_5m.get('stoch_rsi_k',0):.0f} BB_width={ind_5m.get('bb',{}).get('width',0):.3f} ATR%={ind_5m.get('atr14_pct',0):.2f} Supertrend={ind_5m.get('supertrend',{}).get('direction','?')} VolRatio={ind_5m.get('volume_ratio',1):.2f}
15m: EMA9={ind_15m.get('ema9',0):.0f} EMA21={ind_15m.get('ema21',0):.0f} RSI={ind_15m.get('rsi14',0):.0f} ADX={ind_15m.get('adx',0):.0f}
1h: EMA9={ind_1h.get('ema9',0):.0f} EMA21={ind_1h.get('ema21',0):.0f} EMA200={ind_1h.get('ema200',0):.0f} RSI={ind_1h.get('rsi14',0):.0f} Supertrend={ind_1h.get('supertrend_dir','?')}
4h: EMA9={ind_4h.get('ema9',0):.0f} EMA21={ind_4h.get('ema21',0):.0f} RSI={ind_4h.get('rsi14',0):.0f} Supertrend={ind_4h.get('supertrend_dir','?')}""")

    return f"""## Positions ปัจจุบัน
{pos_text}

## Indicators (8 coins x 4 TF)
{"".join(coins_text)}

วิเคราะห์ indicators ทั้งหมดแล้วตอบเป็น JSON ตาม format ที่กำหนด"""


def build_sentiment_prompt(data: dict) -> str:
    """Build prompt for Sentiment Agent."""
    news = data.get("news", [])
    fear_greed = data.get("fear_greed", {})
    funding_rates = {symbol: coin.get("funding_rate", 0) for symbol, coin in data.get("coins", {}).items()}

    # Format news
    news_text = "ไม่มีข่าว"
    if news:
        news_lines = []
        for n in news[:15]:
            news_lines.append(f"[{n.get('source','')}] {n.get('title','')} - {n.get('description','')[:80]}")
        news_text = "\n".join(news_lines)

    # Format funding
    funding_text = "\n".join([f"{sym}: {rate:.4f}" for sym, rate in funding_rates.items()])

    return f"""## ข่าว (15 ล่าสุด)
{news_text}

## Fear & Greed Index
Value: {fear_greed.get('value', 50)}/100 ({fear_greed.get('label', 'Neutral')})

## Funding Rates
{funding_text}

วิเคราะห์ sentiment ทั้งหมดแล้วตอบเป็น JSON"""


def build_whale_prompt(data: dict) -> str:
    """Build prompt for Whale Agent."""
    coins = data.get("coins", {})

    coins_text = []
    for symbol, coin_data in coins.items():
        whale = coin_data.get("whale_activity", {})
        price = coin_data.get("price", 0)

        taker_ratio = whale.get("taker_buy_sell_ratio", 0)
        top_long = whale.get("top_trader_long_pct", 0)
        top_short = whale.get("top_trader_short_pct", 0)
        oi = whale.get("open_interest_usdt", 0)
        bid_ask = whale.get("order_book_bid_ask_ratio", 0)
        walls = whale.get("whale_walls", [])

        coins_text.append(f"""
{symbol} (price: {price})
Taker Buy/Sell Ratio: {taker_ratio:.2f}
Top Trader Long: {top_long:.1f}% | Short: {top_short:.1f}%
Open Interest: ${oi/1e6:.1f}M
Order Book Bid/Ask: {bid_ask:.2f}
Whale Walls: {', '.join(walls[:3]) if walls else 'None'}""")

    return f"""## Whale Data (8 coins)
{"".join(coins_text)}

วิเคราะห์ whale activity แล้วตอบเป็น JSON"""


def build_macro_prompt(data: dict) -> str:
    """Build prompt for Macro Agent."""
    coins = data.get("coins", {})

    # Categorize by regime
    regimes = {"trending_up": [], "trending_down": [], "ranging": [], "volatile": [], "unknown": []}
    for symbol, coin_data in coins.items():
        regime = coin_data.get("regime", "unknown")
        regimes[regime].append(symbol)

    # BTC vs others performance
    btc_change = coins.get("BTCUSDT", {}).get("price_change_24h_pct", 0)
    eth_change = coins.get("ETHUSDT", {}).get("price_change_24h_pct", 0)

    # 4h indicators
    coins_4h = []
    for symbol, coin_data in coins.items():
        ind_4h = coin_data.get("indicators_4h", {})
        ema9 = ind_4h.get("ema9", 0)
        ema21 = ind_4h.get("ema21", 0)
        st_dir = ind_4h.get("supertrend_dir", "?")
        coins_4h.append(f"{symbol}: EMA9={ema9:.0f} EMA21={ema21:.0f} Supertrend={st_dir}")

    return f"""## Market Regimes
Trending Up: {', '.join(regimes['trending_up']) or 'None'}
Trending Down: {', '.join(regimes['trending_down']) or 'None'}
Ranging: {', '.join(regimes['ranging']) or 'None'}
Volatile: {', '.join(regimes['volatile']) or 'None'}

## 24h Performance
BTC: {btc_change:+.2f}% | ETH: {eth_change:+.2f}%

## 4h Trend (macro timeframe)
{chr(10).join(coins_4h)}

วิเคราะห์ market phase และ regime แล้วตอบเป็น JSON"""


def build_manager_prompt(data: dict) -> str:
    """Build prompt for Manager Agent."""
    specialist_reports = data.get("specialist_reports", {})
    backtest_results = data.get("backtest_results", {})
    learning_context = data.get("learning_context", {})
    account = data.get("account", {})
    positions = account.get("positions", [])

    # Format specialist reports
    tech_report = specialist_reports.get("technical", {})
    sent_report = specialist_reports.get("sentiment", {})
    whale_report = specialist_reports.get("whale", {})
    macro_report = specialist_reports.get("macro", {})

    import json
    reports_text = f"""
TECHNICAL ANALYST:
{json.dumps(tech_report, indent=2, ensure_ascii=False)}

SENTIMENT ANALYST:
{json.dumps(sent_report, indent=2, ensure_ascii=False)}

WHALE ANALYST:
{json.dumps(whale_report, indent=2, ensure_ascii=False)}

MACRO ANALYST:
{json.dumps(macro_report, indent=2, ensure_ascii=False)}"""

    # Format backtest
    backtest_text = "No backtest data yet"
    if backtest_results:
        bt_lines = []
        for symbol, bt in backtest_results.items():
            bt_lines.append(f"{symbol}: {bt.get('win_rate', 0):.0f}% win rate, {bt.get('sample_size', 0)} samples, confidence={bt.get('confidence', 50)}")
        backtest_text = "\n".join(bt_lines)

    # Format learning
    learning_text = "No learning data yet (cold start)"
    if learning_context:
        learning_text = f"""Win rate: {learning_context.get('recent_win_rate', 0):.0f}%
Strategy score: {learning_context.get('strategy_score', 50)}/100
Streak: {learning_context.get('consecutive_streak', 0):+d}
Last 5 trades summary: {learning_context.get('last_5_summary', 'N/A')}"""

    # Format positions
    pos_text = "ไม่มี position"
    if positions:
        pos_lines = [f"{p['symbol']} {p['side']} @ {p.get('entry_price', 0)} (PnL: {p.get('unrealized_pnl_pct', 0):+.1f}%)"
                     for p in positions]
        pos_text = "\n".join(pos_lines)

    return f"""## Account
Balance: {account.get('balance_usdt', 0):.2f} USDT
Positions: {len(positions)}
{pos_text}

## Specialist Reports (4 agents)
{reports_text}

## Backtesting Results
{backtest_text}

## Learning Context
{learning_text}

วิเคราะห์รายงานทั้งหมด ตรวจสอบความสอดคล้อง แล้วตัดสินใจขั้นสุดท้าย ตอบเป็น JSON"""
```

### 2.2 `src/ai/agents/technical_agent.py`

```python
"""
Technical Analyst Agent - Pure chart/indicator analysis
"""
from .base_agent import BaseAgent
from src.ai.prompts_v2 import TECHNICAL_AGENT_PROMPT, build_technical_prompt
from src.utils.logger import log


class TechnicalAgent(BaseAgent):
    """
    Specialist in technical analysis.
    Focuses only on indicators across all timeframes.
    """

    def __init__(self, provider: str, model: str, api_key: str, timeout: float = 12.0):
        super().__init__(
            agent_name="technical",
            provider=provider,
            model=model,
            api_key=api_key,
            system_prompt=TECHNICAL_AGENT_PROMPT,
            temperature=0.2,
            max_tokens=800,
            timeout=timeout,
        )

    async def analyze(self, data: dict) -> dict:
        """
        Analyze technical indicators.

        Args:
            data: {
                "coins": {...},  # All symbols with indicators
                "positions": [...],  # Current positions
            }

        Returns:
            {
                "agent": "technical",
                "signals": {...},
                "cross_coin_notes": "...",
                "error": "..." (if failed)
            }
        """
        try:
            user_prompt = build_technical_prompt(data)
            response_text, usage, latency_ms = await self._call_provider(user_prompt)

            parsed = self._parse_json(response_text)

            # Add metadata
            parsed["latency_ms"] = latency_ms
            parsed["tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            log.info(f"[Technical Agent] Analyzed in {latency_ms}ms, {parsed.get('tokens', 0)} tokens")
            return parsed

        except Exception as e:
            log.error(f"[Technical Agent] Analysis failed: {e}")
            return {
                "agent": "technical",
                "error": str(e),
                "signals": {},
            }
```

### 2.3 `src/ai/agents/sentiment_agent.py`

```python
"""
Sentiment Analyst Agent - News + Fear/Greed + Funding interpretation
"""
from .base_agent import BaseAgent
from src.ai.prompts_v2 import SENTIMENT_AGENT_PROMPT, build_sentiment_prompt
from src.utils.logger import log


class SentimentAgent(BaseAgent):
    """
    Specialist in news and market sentiment analysis.
    """

    def __init__(self, provider: str, model: str, api_key: str, timeout: float = 12.0):
        super().__init__(
            agent_name="sentiment",
            provider=provider,
            model=model,
            api_key=api_key,
            system_prompt=SENTIMENT_AGENT_PROMPT,
            temperature=0.2,
            max_tokens=800,
            timeout=timeout,
        )

    async def analyze(self, data: dict) -> dict:
        """
        Analyze sentiment from news, fear/greed, funding.

        Args:
            data: {
                "news": [...],
                "fear_greed": {...},
                "coins": {...}  # For funding rates
            }

        Returns:
            {
                "agent": "sentiment",
                "market_mood": "...",
                "news_impact": {...},
                "funding_signal": "...",
                "error": "..." (if failed)
            }
        """
        try:
            user_prompt = build_sentiment_prompt(data)
            response_text, usage, latency_ms = await self._call_provider(user_prompt)

            parsed = self._parse_json(response_text)
            parsed["latency_ms"] = latency_ms
            parsed["tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            log.info(f"[Sentiment Agent] Analyzed in {latency_ms}ms")
            return parsed

        except Exception as e:
            log.error(f"[Sentiment Agent] Analysis failed: {e}")
            return {
                "agent": "sentiment",
                "error": str(e),
                "market_mood": "neutral",
            }
```

### 2.4 `src/ai/agents/whale_agent.py`

```python
"""
Whale/Smart Money Analyst Agent - Order flow analysis
"""
from .base_agent import BaseAgent
from src.ai.prompts_v2 import WHALE_AGENT_PROMPT, build_whale_prompt
from src.utils.logger import log


class WhaleAgent(BaseAgent):
    """
    Specialist in whale data and order flow analysis.
    """

    def __init__(self, provider: str, model: str, api_key: str, timeout: float = 12.0):
        super().__init__(
            agent_name="whale",
            provider=provider,
            model=model,
            api_key=api_key,
            system_prompt=WHALE_AGENT_PROMPT,
            temperature=0.2,
            max_tokens=800,
            timeout=timeout,
        )

    async def analyze(self, data: dict) -> dict:
        """
        Analyze whale activity and smart money flow.

        Args:
            data: {
                "coins": {...}  # whale_activity for each symbol
            }

        Returns:
            {
                "agent": "whale",
                "signals": {...},
                "aggregate_flow": "...",
                "error": "..." (if failed)
            }
        """
        try:
            user_prompt = build_whale_prompt(data)
            response_text, usage, latency_ms = await self._call_provider(user_prompt)

            parsed = self._parse_json(response_text)
            parsed["latency_ms"] = latency_ms
            parsed["tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            log.info(f"[Whale Agent] Analyzed in {latency_ms}ms")
            return parsed

        except Exception as e:
            log.error(f"[Whale Agent] Analysis failed: {e}")
            return {
                "agent": "whale",
                "error": str(e),
                "signals": {},
            }
```

### 2.5 `src/ai/agents/macro_agent.py`

```python
"""
Macro/Regime Analyst Agent - Market phase and big picture
"""
from .base_agent import BaseAgent
from src.ai.prompts_v2 import MACRO_AGENT_PROMPT, build_macro_prompt
from src.utils.logger import log


class MacroAgent(BaseAgent):
    """
    Specialist in market regime and macro trends.
    """

    def __init__(self, provider: str, model: str, api_key: str, timeout: float = 12.0):
        super().__init__(
            agent_name="macro",
            provider=provider,
            model=model,
            api_key=api_key,
            system_prompt=MACRO_AGENT_PROMPT,
            temperature=0.2,
            max_tokens=800,
            timeout=timeout,
        )

    async def analyze(self, data: dict) -> dict:
        """
        Analyze market regime and recommend strategy.

        Args:
            data: {
                "coins": {...}  # regime + 4h indicators for each
            }

        Returns:
            {
                "agent": "macro",
                "market_phase": "...",
                "regime_summary": {...},
                "strategy_recommendation": "...",
                "error": "..." (if failed)
            }
        """
        try:
            user_prompt = build_macro_prompt(data)
            response_text, usage, latency_ms = await self._call_provider(user_prompt)

            parsed = self._parse_json(response_text)
            parsed["latency_ms"] = latency_ms
            parsed["tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            log.info(f"[Macro Agent] Analyzed in {latency_ms}ms")
            return parsed

        except Exception as e:
            log.error(f"[Macro Agent] Analysis failed: {e}")
            return {
                "agent": "macro",
                "error": str(e),
                "market_phase": "unknown",
            }
```

---

## Phase 3: Manager & Risk

### 3.1 `src/ai/agents/manager_agent.py`

```python
"""
Manager Agent - Synthesizes all specialist reports and makes final decision
Uses DeepSeek (proven best in Alpha Arena)
"""
from .base_agent import BaseAgent
from src.ai.prompts_v2 import MANAGER_AGENT_PROMPT, build_manager_prompt
from src.utils.logger import log


class ManagerAgent(BaseAgent):
    """
    Chief Trading Officer - receives all specialist reports and decides.
    """

    def __init__(self, provider: str, model: str, api_key: str, timeout: float = 15.0):
        super().__init__(
            agent_name="manager",
            provider=provider,
            model=model,
            api_key=api_key,
            system_prompt=MANAGER_AGENT_PROMPT,
            temperature=0.3,
            max_tokens=1500,
            timeout=timeout,
        )

    async def decide(self, data: dict) -> dict:
        """
        Make final trading decision based on all inputs.

        Args:
            data: {
                "specialist_reports": {
                    "technical": {...},
                    "sentiment": {...},
                    "whale": {...},
                    "macro": {...}
                },
                "backtest_results": {...},
                "learning_context": {...},
                "account": {...},
            }

        Returns:
            {
                "market_view": "...",
                "agent_consensus": {...},
                "actions": [...],  # Same format as old brain.py
                "error": "..." (if failed)
            }
        """
        try:
            user_prompt = build_manager_prompt(data)
            response_text, usage, latency_ms = await self._call_provider(user_prompt)

            parsed = self._parse_json(response_text)

            # Add metadata (compatible with old system)
            parsed["meta"] = {
                "model": self.model,
                "provider": self.provider,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "cost_usd": self._estimate_cost(usage),
            }

            log.info(f"[Manager] Decision made in {latency_ms}ms, {len(parsed.get('actions', []))} actions")
            return parsed

        except Exception as e:
            log.error(f"[Manager] Decision failed: {e}")
            return {
                "market_view": "Error - holding positions",
                "actions": [],
                "error": str(e),
            }

    def _estimate_cost(self, usage: dict) -> float:
        """Estimate API cost (DeepSeek pricing)."""
        prompt_tok = usage.get("prompt_tokens", 0)
        completion_tok = usage.get("completion_tokens", 0)

        # DeepSeek pricing per million tokens
        input_price, output_price = (0.28, 0.42)
        cost = (prompt_tok * input_price / 1_000_000) + (completion_tok * output_price / 1_000_000)
        return round(cost, 6)
```

### 3.2 `src/strategy/risk_manager.py`

```python
"""
Advanced Risk Manager
Kelly Criterion + Confidence Gate + Streak Awareness + Volatility Adjustment
"""
from typing import Dict, Any, List
from src.utils.config import settings
from src.utils.logger import log


class RiskManager:
    """
    Validates AI decisions and calculates optimal position sizes.
    """

    def __init__(self):
        self.min_confidence = settings.MIN_CONFIDENCE_TO_TRADE
        self.high_confidence = settings.HIGH_CONFIDENCE_THRESHOLD

    def filter_actions(
        self,
        ai_actions: List[dict],
        balance: float,
        current_positions: List[dict],
        learning_context: dict,
    ) -> List[dict]:
        """
        Filter and adjust AI actions through risk gates.

        Returns: List of approved actions with adjusted position sizes
        """
        approved_actions = []

        for action in ai_actions:
            symbol = action.get("symbol")
            ai_action = action.get("action")
            confidence = action.get("confidence", 50)
            margin_usdt = action.get("margin_usdt", 0)

            # Skip HOLD/SKIP
            if ai_action in ["HOLD", "SKIP"]:
                continue

            # Gate 1: Confidence threshold
            if ai_action in ["OPEN_LONG", "OPEN_SHORT"]:
                if confidence < self.min_confidence:
                    log.info(f"[RiskMgr] Rejected {symbol} {ai_action}: confidence {confidence} < {self.min_confidence}")
                    continue

            # Gate 2: Calculate adjusted position size
            result = self.calculate_position_size(
                balance=balance,
                confidence=confidence,
                symbol=symbol,
                action=ai_action,
                ai_suggested_margin=margin_usdt,
                current_positions=current_positions,
                learning_context=learning_context,
            )

            if not result["approved"]:
                log.info(f"[RiskMgr] Rejected {symbol} {ai_action}: {result['reason']}")
                continue

            # Update margin with risk-adjusted size
            action["margin_usdt"] = result["margin_usdt"]
            action["risk_note"] = result.get("note", "")
            approved_actions.append(action)

        log.info(f"[RiskMgr] Approved {len(approved_actions)}/{len(ai_actions)} actions")
        return approved_actions

    def calculate_position_size(
        self,
        balance: float,
        confidence: int,
        symbol: str,
        action: str,
        ai_suggested_margin: float,
        current_positions: List[dict],
        learning_context: dict,
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size using multiple factors.
        """
        # For CLOSE actions, no sizing needed
        if action == "CLOSE":
            return {"approved": True, "margin_usdt": 0, "note": "Close action"}

        # Get base risk from tier system
        base_risk_pct = settings.get_risk_pct(balance) / 100

        # === Confidence Multiplier ===
        if confidence < 60:
            return {"approved": False, "reason": f"Confidence {confidence} < 60"}
        elif confidence < 70:
            conf_mult = 0.5  # Half size
        elif confidence < 85:
            conf_mult = 1.0  # Normal size
        else:
            conf_mult = 1.3  # Enhanced size

        # === Kelly Criterion (simplified) ===
        kelly_mult = 1.0
        win_rate = learning_context.get("recent_win_rate", 50) / 100
        avg_win_pct = learning_context.get("avg_win_pct", 4.0) / 100
        avg_loss_pct = abs(learning_context.get("avg_loss_pct", -3.0)) / 100

        if win_rate > 0 and avg_win_pct > 0:
            # Kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
            loss_rate = 1 - win_rate
            kelly_fraction = (win_rate * avg_win_pct - loss_rate * avg_loss_pct) / avg_win_pct
            # Use half-Kelly for safety
            kelly_mult = max(0.5, min(1.5, kelly_fraction / 2))

        # === Streak Adjustment ===
        streak = learning_context.get("consecutive_streak", 0)
        if streak <= -3:
            streak_mult = 0.5
        elif streak <= -2:
            streak_mult = 0.7
        elif streak == -1:
            streak_mult = 0.85
        elif streak >= 3:
            streak_mult = 1.15
        else:
            streak_mult = 1.0

        # === Volatility Adjustment ===
        # Get symbol's ATR% from learning context if available
        atr_pct = learning_context.get("symbol_volatility", {}).get(symbol, 1.0)
        if atr_pct > 2.0:
            vol_mult = 0.6
        elif atr_pct > 1.0:
            vol_mult = 0.8
        else:
            vol_mult = 1.0

        # === Final Calculation ===
        margin_usdt = (
            balance
            * base_risk_pct
            * conf_mult
            * kelly_mult
            * streak_mult
            * vol_mult
        )

        # Clamp to minimum
        margin_usdt = max(margin_usdt, settings.MIN_ORDER_USDT)

        # === Max Exposure Check ===
        total_margin_used = sum(p.get("margin_usdt", 0) for p in current_positions)
        if total_margin_used + margin_usdt > balance * 0.80:
            return {
                "approved": False,
                "reason": f"Max exposure 80% of balance reached ({total_margin_used + margin_usdt:.2f} > {balance * 0.80:.2f})"
            }

        return {
            "approved": True,
            "margin_usdt": round(margin_usdt, 2),
            "note": f"conf={conf_mult:.1f}x kelly={kelly_mult:.2f}x streak={streak_mult:.2f}x vol={vol_mult:.1f}x",
        }
```

### 3.3 `src/strategy/backtester.py`

```python
"""
Backtester - Pattern matching without AI
Stores indicator fingerprints and queries historical win rates
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.config import settings
from src.utils.logger import log


class Backtester:
    """
    Code-based backtesting using indicator fingerprints.
    No AI - pure pattern matching.
    """

    def __init__(self):
        self.snapshot_file = Path(settings.BACKTEST_SNAPSHOT_PATH)
        self.max_snapshots = settings.BACKTEST_WINDOW_SIZE
        self.snapshots: List[dict] = []
        self._load_snapshots()

    def _load_snapshots(self):
        """Load snapshots from disk."""
        if self.snapshot_file.exists():
            try:
                with open(self.snapshot_file, 'r', encoding='utf-8') as f:
                    self.snapshots = json.load(f)
                log.info(f"[Backtester] Loaded {len(self.snapshots)} snapshots")
            except Exception as e:
                log.error(f"[Backtester] Failed to load snapshots: {e}")
                self.snapshots = []
        else:
            self.snapshots = []
            log.info("[Backtester] No snapshot file, starting fresh")

    def _save_snapshots(self):
        """Save snapshots to disk."""
        try:
            self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(self.snapshots[-self.max_snapshots:], f, indent=2)
        except Exception as e:
            log.error(f"[Backtester] Failed to save snapshots: {e}")

    def create_fingerprint(self, indicators: dict, regime: str) -> str:
        """
        Create a hashable fingerprint of market conditions.

        Example: "trending_up|rsi_55-65|adx_25-35|ema_bullish|macd_pos|st_up|vol_high"
        """
        # RSI buckets
        rsi = indicators.get("rsi14", 50)
        if rsi < 35:
            rsi_bucket = "rsi_<35"
        elif rsi < 45:
            rsi_bucket = "rsi_35-45"
        elif rsi < 55:
            rsi_bucket = "rsi_45-55"
        elif rsi < 65:
            rsi_bucket = "rsi_55-65"
        else:
            rsi_bucket = "rsi_>65"

        # ADX buckets
        adx = indicators.get("adx", 20)
        if adx < 20:
            adx_bucket = "adx_<20"
        elif adx < 30:
            adx_bucket = "adx_20-30"
        elif adx < 40:
            adx_bucket = "adx_30-40"
        else:
            adx_bucket = "adx_>40"

        # EMA cross
        ema9 = indicators.get("ema9", 0)
        ema21 = indicators.get("ema21", 0)
        ema55 = indicators.get("ema55", 0)
        if ema9 > ema21 > ema55:
            ema_cross = "ema_bullish"
        elif ema9 < ema21 < ema55:
            ema_cross = "ema_bearish"
        else:
            ema_cross = "ema_mixed"

        # MACD histogram
        macd_hist = indicators.get("macd", {}).get("histogram", 0)
        macd_sign = "macd_pos" if macd_hist > 0 else "macd_neg"

        # Supertrend
        st_dir = indicators.get("supertrend", {}).get("direction", "?")
        st = f"st_{st_dir}"

        # Volume ratio
        vol_ratio = indicators.get("volume_ratio", 1.0)
        if vol_ratio > 1.5:
            vol_bucket = "vol_high"
        elif vol_ratio > 0.8:
            vol_bucket = "vol_normal"
        else:
            vol_bucket = "vol_low"

        return f"{regime}|{rsi_bucket}|{adx_bucket}|{ema_cross}|{macd_sign}|{st}|{vol_bucket}"

    def store_snapshot(
        self,
        symbol: str,
        indicators: dict,
        regime: str,
        action_taken: str,
        confidence: int,
    ):
        """
        Store a snapshot for future backtesting.
        outcome_pnl_pct will be filled when position closes.
        """
        fingerprint = self.create_fingerprint(indicators, regime)
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "fingerprint": fingerprint,
            "action_taken": action_taken,
            "confidence": confidence,
            "outcome_pnl_pct": None,  # To be filled later
        }
        self.snapshots.append(snapshot)

        # Keep rolling window
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        self._save_snapshots()

    def update_outcome(self, symbol: str, timestamp_str: str, pnl_pct: float):
        """
        Update the outcome of a snapshot when position closes.
        """
        for snap in reversed(self.snapshots):
            if snap["symbol"] == symbol and snap["timestamp"] == timestamp_str:
                snap["outcome_pnl_pct"] = pnl_pct
                self._save_snapshots()
                log.info(f"[Backtester] Updated {symbol} snapshot outcome: {pnl_pct:+.2f}%")
                return

    def get_historical_confidence(
        self,
        symbol: str,
        fingerprint: str,
        action: str,
    ) -> Dict[str, Any]:
        """
        Look up how similar setups performed historically.

        Returns:
            {
                "sample_size": int,
                "win_rate": float,
                "avg_pnl_pct": float,
                "confidence": int (0-100),
                "note": str
            }
        """
        # Find matches
        matches = [
            s for s in self.snapshots
            if s["fingerprint"] == fingerprint
            and s["action_taken"] == action
            and s["symbol"] == symbol
            and s["outcome_pnl_pct"] is not None
        ]

        if len(matches) < 3:
            return {
                "sample_size": len(matches),
                "win_rate": 50.0,
                "avg_pnl_pct": 0.0,
                "confidence": 50,
                "note": "Insufficient data (need 3+ samples)"
            }

        # Calculate stats
        wins = sum(1 for m in matches if m["outcome_pnl_pct"] > 0)
        win_rate = (wins / len(matches)) * 100
        avg_pnl = sum(m["outcome_pnl_pct"] for m in matches) / len(matches)

        # Calculate confidence score
        # Formula: win_rate * 0.8 + min(sample_size, 20) * 1.0
        confidence = min(90, int(win_rate * 0.8 + min(len(matches), 20) * 1.0))

        return {
            "sample_size": len(matches),
            "win_rate": round(win_rate, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "confidence": confidence,
            "note": f"{wins}W/{len(matches)-wins}L"
        }

    def evaluate_signals(
        self,
        specialist_reports: Dict[str, dict],
        indicators: Dict[str, Dict[str, dict]],
    ) -> Dict[str, dict]:
        """
        Evaluate specialist signals against historical patterns.

        Returns: {symbol: backtest_result}
        """
        results = {}

        # Get technical signals
        tech_signals = specialist_reports.get("technical", {}).get("signals", {})

        for symbol, signal in tech_signals.items():
            bias = signal.get("bias", "NEUTRAL")
            if bias == "NEUTRAL":
                continue

            # Get 5m indicators for this symbol
            ind_5m = indicators.get(symbol, {}).get("5m", {})
            regime = indicators.get(symbol, {}).get("regime", "unknown")

            if not ind_5m:
                continue

            # Create fingerprint
            fingerprint = self.create_fingerprint(ind_5m, regime)

            # Map bias to action
            action = "OPEN_LONG" if bias == "LONG" else "OPEN_SHORT"

            # Query historical performance
            bt_result = self.get_historical_confidence(symbol, fingerprint, action)
            results[symbol] = bt_result

        return results
```

---

## Phase 4: Learning System

### 4.1 `src/learning/__init__.py`

```python
"""
Learning System - Track outcomes and improve over time
"""
from .trade_journal import TradeJournal
from .outcome_tracker import OutcomeTracker

__all__ = ["TradeJournal", "OutcomeTracker"]
```

### 4.2 `src/learning/trade_journal.py`

```python
"""
Trade Journal - Local JSON storage for fast reads
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.utils.config import settings
from src.utils.logger import log


class TradeJournal:
    """
    Simple JSON file manager for trade records.
    Append-only during cycle, rolling window.
    """

    def __init__(self):
        self.journal_file = Path(settings.LEARNING_JOURNAL_PATH)
        self.max_trades = settings.LEARNING_WINDOW_SIZE
        self.trades: List[dict] = []
        self._load()

    def _load(self):
        """Load journal from disk."""
        if self.journal_file.exists():
            try:
                with open(self.journal_file, 'r', encoding='utf-8') as f:
                    self.trades = json.load(f)
                log.info(f"[TradeJournal] Loaded {len(self.trades)} trades")
            except Exception as e:
                log.error(f"[TradeJournal] Failed to load: {e}")
                self.trades = []
        else:
            self.trades = []

    def _save(self):
        """Save journal to disk."""
        try:
            self.journal_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.journal_file, 'w', encoding='utf-8') as f:
                json.dump(self.trades[-self.max_trades:], f, indent=2)
        except Exception as e:
            log.error(f"[TradeJournal] Failed to save: {e}")

    def append_trade(self, trade: dict):
        """Append a trade record."""
        self.trades.append(trade)
        if len(self.trades) > self.max_trades:
            self.trades = self.trades[-self.max_trades:]
        self._save()

    def get_recent(self, n: int = 50) -> List[dict]:
        """Get last N trades."""
        return self.trades[-n:]

    def get_by_symbol(self, symbol: str, n: int = 20) -> List[dict]:
        """Get last N trades for a specific symbol."""
        symbol_trades = [t for t in self.trades if t.get("symbol") == symbol]
        return symbol_trades[-n:]

    def get_streak(self) -> int:
        """
        Get current win/loss streak.
        Positive = consecutive wins, Negative = consecutive losses.
        """
        if not self.trades:
            return 0

        streak = 0
        for trade in reversed(self.trades):
            pnl = trade.get("realized_pnl_pct", 0)
            if pnl > 0:
                if streak >= 0:
                    streak += 1
                else:
                    break
            elif pnl < 0:
                if streak <= 0:
                    streak -= 1
                else:
                    break
            else:
                break

        return streak

    def get_stats(self, n: int = 50) -> Dict[str, Any]:
        """Get statistics for last N trades."""
        recent = self.get_recent(n)
        if not recent:
            return {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_win_pct": 0.0,
                "avg_loss_pct": 0.0,
            }

        wins = [t for t in recent if t.get("realized_pnl_pct", 0) > 0]
        losses = [t for t in recent if t.get("realized_pnl_pct", 0) < 0]

        avg_win = sum(t["realized_pnl_pct"] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t["realized_pnl_pct"] for t in losses) / len(losses) if losses else 0.0

        return {
            "total": len(recent),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(recent)) * 100 if recent else 0.0,
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
        }
```

### 4.3 `src/learning/outcome_tracker.py`

```python
"""
Outcome Tracker - Track expected vs actual, strategy scoring
"""
from typing import Dict, Any
from .trade_journal import TradeJournal
from src.utils.logger import log


class OutcomeTracker:
    """
    Tracks strategy performance and provides context for AI decisions.
    """

    def __init__(self):
        self.journal = TradeJournal()

    def record_trade(
        self,
        symbol: str,
        side: str,
        action: str,
        confidence: int,
        expected_outcome: str,
        realized_pnl_pct: Optional[float] = None,
    ):
        """Record a trade to the journal."""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "action": action,
            "confidence": confidence,
            "expected_outcome": expected_outcome,
            "realized_pnl_pct": realized_pnl_pct,
        }
        self.journal.append_trade(trade_record)

    def update_outcome(self, symbol: str, timestamp_str: str, pnl_pct: float):
        """Update outcome when position closes."""
        # Find matching trade in journal
        for trade in reversed(self.journal.trades):
            if trade["symbol"] == symbol and trade["timestamp"] == timestamp_str:
                trade["realized_pnl_pct"] = pnl_pct
                self.journal._save()
                log.info(f"[OutcomeTracker] Updated {symbol} outcome: {pnl_pct:+.2f}%")
                return

    def get_learning_context(self, n: int = 50) -> Dict[str, Any]:
        """
        Generate learning context for AI Manager.

        Returns:
            {
                "recent_win_rate": float,
                "avg_win_pct": float,
                "avg_loss_pct": float,
                "strategy_score": int (0-100),
                "consecutive_streak": int,
                "last_5_summary": str,
                "confidence_accuracy": float (correlation),
            }
        """
        stats = self.journal.get_stats(n)
        streak = self.journal.get_streak()

        # Strategy score with decay
        win_rate = stats["win_rate"]
        score = int(50 + (win_rate - 50) * 0.5)  # Centered at 50, scaled
        score = max(0, min(100, score))

        # Last 5 trades summary
        last_5 = self.journal.get_recent(5)
        if last_5:
            summary_parts = []
            for t in last_5:
                symbol = t.get("symbol", "?")
                side = t.get("side", "?")
                pnl = t.get("realized_pnl_pct", 0)
                conf = t.get("confidence", 0)
                outcome = "WIN" if pnl > 0 else "LOSS"
                summary_parts.append(f"{symbol} {side} {pnl:+.1f}% (conf={conf}) {outcome}")
            last_5_summary = " | ".join(summary_parts)
        else:
            last_5_summary = "No trades yet"

        # Confidence accuracy (simple: high confidence trades win more?)
        # Could be improved with actual correlation calculation
        confidence_accuracy = 0.5  # Placeholder

        return {
            "recent_win_rate": stats["win_rate"],
            "avg_win_pct": stats["avg_win_pct"],
            "avg_loss_pct": stats["avg_loss_pct"],
            "strategy_score": score,
            "consecutive_streak": streak,
            "last_5_summary": last_5_summary,
            "confidence_accuracy": confidence_accuracy,
            "symbol_volatility": {},  # Could add per-symbol ATR tracking
        }


# Singleton
outcome_tracker = OutcomeTracker()
```

---

## Phase 5: Integration

### 5.1 Updated `src/utils/config.py` (Add these settings)

```python
# At the end of the Settings class, add:

    # === Multi-Agent Configuration ===
    MULTI_AGENT_ENABLED: bool = True  # Toggle to switch between multi-agent and single-brain

    # Technical Agent
    AGENT_TECHNICAL_PROVIDER: str = "groq"
    AGENT_TECHNICAL_MODEL: str = "llama-3.3-70b-versatile"
    AGENT_TECHNICAL_API_KEY: str = ""

    # Sentiment Agent
    AGENT_SENTIMENT_PROVIDER: str = "gemini"
    AGENT_SENTIMENT_MODEL: str = "gemini-2.0-flash-exp"
    AGENT_SENTIMENT_API_KEY: str = ""

    # Whale Agent
    AGENT_WHALE_PROVIDER: str = "groq"
    AGENT_WHALE_MODEL: str = "llama-3.3-70b-versatile"
    AGENT_WHALE_API_KEY: str = ""

    # Macro Agent
    AGENT_MACRO_PROVIDER: str = "gemini"
    AGENT_MACRO_MODEL: str = "gemini-2.0-flash-exp"
    AGENT_MACRO_API_KEY: str = ""

    # Manager Agent (DeepSeek proven best)
    AGENT_MANAGER_PROVIDER: str = "deepseek"
    AGENT_MANAGER_MODEL: str = "deepseek-chat"
    AGENT_MANAGER_API_KEY: str = ""

    # Agent timeouts
    AGENT_SPECIALIST_TIMEOUT: float = 12.0
    AGENT_MANAGER_TIMEOUT: float = 15.0

    # Confidence gating
    MIN_CONFIDENCE_TO_TRADE: int = 60
    HIGH_CONFIDENCE_THRESHOLD: int = 85

    # Learning paths
    LEARNING_JOURNAL_PATH: str = "data/trade_journal.json"
    BACKTEST_SNAPSHOT_PATH: str = "data/indicator_snapshots.json"
    LEARNING_WINDOW_SIZE: int = 200
    BACKTEST_WINDOW_SIZE: int = 2000
```

### 5.2 Updated `src/utils/cache.py` (Add these fields to reset())

```python
# In CycleCache.reset(), add after line 70:

        # Multi-agent data
        self.specialist_reports: Dict[str, dict] = {}
        self.specialist_timings: Dict[str, int] = {}
        self.backtest_results: dict = {}
        self.learning_context: dict = {}
        self.manager_consensus: dict = {}
        self.confidence_scores: Dict[str, int] = {}
```

### 5.3 New `src/core/engine_multiagent.py` (Rewritten engine)

Copy this full file content - it's the complete rewrite of engine.py with multi-agent orchestration. Due to length, I'll provide the key changes summary instead:

**Key Changes:**
1. Import all 5 agents + provider_pool + risk_manager + backtester + outcome_tracker
2. Init all agents in `__init__()` with configs from provider_pool
3. In `run_cycle()`:
   - After indicators (Step 5), load learning context
   - Run 4 specialists in PARALLEL (asyncio.gather)
   - Run backtester.evaluate_signals() (code-only, instant)
   - Run Manager agent with all inputs
   - Run risk_manager.filter_actions() (code-only)
   - Execute filtered actions
   - Update learning/backtesting after execution

**This is too long for MD. Instead, I'll create a separate file:**

---

## Phase 6: Configuration Files

### 6.1 Updated `.env.example`

```bash
# === Binance API ===
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true

# === Multi-Agent Toggle ===
MULTI_AGENT_ENABLED=true

# === Single-Brain AI (fallback) ===
AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=your_groq_key
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000

# === Multi-Agent Providers ===
# Technical Agent (Groq Llama 3.3 70B)
AGENT_TECHNICAL_PROVIDER=groq
AGENT_TECHNICAL_MODEL=llama-3.3-70b-versatile
AGENT_TECHNICAL_API_KEY=your_groq_key

# Sentiment Agent (Gemini 2.5 Flash)
AGENT_SENTIMENT_PROVIDER=gemini
AGENT_SENTIMENT_MODEL=gemini-2.0-flash-exp
AGENT_SENTIMENT_API_KEY=your_gemini_key

# Whale Agent (Groq Llama 3.3 70B)
AGENT_WHALE_PROVIDER=groq
AGENT_WHALE_MODEL=llama-3.3-70b-versatile
AGENT_WHALE_API_KEY=your_groq_key_2_or_same

# Macro Agent (Gemini 2.5 Flash)
AGENT_MACRO_PROVIDER=gemini
AGENT_MACRO_MODEL=gemini-2.0-flash-exp
AGENT_MACRO_API_KEY=your_gemini_key_same

# Manager Agent (DeepSeek V3 - proven best)
AGENT_MANAGER_PROVIDER=deepseek
AGENT_MANAGER_MODEL=deepseek-chat
AGENT_MANAGER_API_KEY=your_deepseek_key

# Agent Timeouts
AGENT_SPECIALIST_TIMEOUT=12.0
AGENT_MANAGER_TIMEOUT=15.0

# Confidence Settings
MIN_CONFIDENCE_TO_TRADE=60
HIGH_CONFIDENCE_THRESHOLD=85

# Learning Paths
LEARNING_JOURNAL_PATH=data/trade_journal.json
BACKTEST_SNAPSHOT_PATH=data/indicator_snapshots.json
LEARNING_WINDOW_SIZE=200
BACKTEST_WINDOW_SIZE=2000

# === Trading (unchanged) ===
LEVERAGE=20
TRADING_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,AVAXUSDT,LINKUSDT
MAX_POSITIONS=5
MIN_ORDER_USDT=5.0
SAFETY_SL_PCT=8.0
SAFETY_TP_PCT=15.0

# Risk tiers
RISK_TIER_TINY=20.0
RISK_TIER_SMALL=10.0
RISK_TIER_MEDIUM=7.0
RISK_TIER_LARGE=4.0
RISK_TIER_XL=2.5

# === News ===
CRYPTOPANIC_API_KEY=free
NEWS_COUNT=20
NEWS_TIMEOUT_SECONDS=15

# === Notifications ===
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

# === Database ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# === Logging ===
LOG_LEVEL=INFO
LOG_FILE=logs/clawbot.log
```

### 6.2 Updated `supabase_schema.sql`

```sql
-- Add to existing schema:

-- Agent decisions per cycle
CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID REFERENCES cycles(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    latency_ms INT,
    prompt_tokens INT,
    completion_tokens INT,
    output_json JSONB NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_agent_decisions_cycle ON agent_decisions(cycle_id);
CREATE INDEX idx_agent_decisions_agent ON agent_decisions(agent_name);

-- Trade outcomes for learning
CREATE TABLE IF NOT EXISTS trade_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID REFERENCES trades(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    open_confidence INT,
    open_regime TEXT,
    indicator_fingerprint TEXT,
    expected_outcome TEXT,
    actual_pnl_pct DECIMAL(8,4),
    outcome TEXT,
    hold_duration_min INT,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trade_outcomes_symbol ON trade_outcomes(symbol);
CREATE INDEX idx_trade_outcomes_fingerprint ON trade_outcomes(indicator_fingerprint);
```

---

## Testing & Deployment

### Test Command
```bash
# Dry run with multi-agent
python main.py --dry-run

# Check logs for all 5 agents
tail -f logs/clawbot.log | grep -E 'Technical|Sentiment|Whale|Macro|Manager'
```

### Verify
1. ✅ All 5 agents produce valid JSON
2. ✅ Manager receives all 4 specialist reports
3. ✅ Backtester creates fingerprints (even with 0 samples)
4. ✅ Risk manager filters low-confidence actions
5. ✅ Total cycle time < 30 seconds
6. ✅ Learning journal updates after trades

### Fallback to Single-Brain
```bash
# In .env
MULTI_AGENT_ENABLED=false

# System automatically uses old brain.py
```

---

## File Checklist

- [x] `src/ai/agents/__init__.py`
- [x] `src/ai/agents/base_agent.py`
- [x] `src/ai/agents/technical_agent.py`
- [x] `src/ai/agents/sentiment_agent.py`
- [x] `src/ai/agents/whale_agent.py`
- [x] `src/ai/agents/macro_agent.py`
- [x] `src/ai/agents/manager_agent.py`
- [x] `src/ai/prompts_v2.py`
- [x] `src/ai/provider_pool.py`
- [x] `src/strategy/risk_manager.py`
- [x] `src/strategy/backtester.py`
- [x] `src/learning/__init__.py`
- [x] `src/learning/trade_journal.py`
- [x] `src/learning/outcome_tracker.py`
- [x] Updated: `src/utils/config.py`
- [x] Updated: `src/utils/cache.py`
- [ ] **TODO: Create `src/core/engine_multiagent.py`** (full rewrite, see next section)
- [x] Updated: `supabase_schema.sql`
- [x] Updated: `.env.example`

---

## END OF IMPLEMENTATION GUIDE

**สำคัญ**: ไฟล์ที่เหลือ `src/core/engine_multiagent.py` ยาวเกินไป ผมจะสร้างไฟล์แยกต่างหาก ดู `ENGINE_MULTIAGENT.md`
