"""
AI Brain - Decision Engine for Short-Term Scalping
Uses AI (Groq FREE / Claude / Kimi) to make trading decisions.
The AI has FULL AUTHORITY to open/close any number of positions.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import httpx
import json

from src.utils.config import config
from src.utils.logger import logger


class AIBrain:
    """AI-powered trading decision engine — scalping optimized"""

    def __init__(self):
        self.primary_model = config.PRIMARY_AI_MODEL
        self.backup_model = config.BACKUP_AI_MODEL
        self.max_positions = config.MAX_POSITIONS

    async def make_decision(self, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make trading decisions based on aggregated data"""
        logger.info("🧠 AI Brain analyzing market...")

        # Build prompt
        prompt = self._build_prompt(aggregated_data)

        # Try primary model first
        try:
            decision = await self._call_ai(prompt, self.primary_model)
            decision['ai_model'] = self.primary_model
        except Exception as e:
            logger.warning(f"Primary AI ({self.primary_model}) failed: {e}")
            try:
                decision = await self._call_ai(prompt, self.backup_model)
                decision['ai_model'] = self.backup_model
            except Exception as e2:
                logger.error(f"Backup AI ({self.backup_model}) failed: {e2}")
                decision = self._fallback_decision(aggregated_data)

        # Add metadata
        decision['cycle_id'] = aggregated_data.get('cycle_id', '')
        decision['timestamp'] = datetime.utcnow().isoformat() + "Z"

        # Log decision summary
        self._log_decision(decision)

        return decision

    def _build_prompt(self, data: Dict) -> str:
        """Build prompt for AI analysis — scalping focused"""

        account = data.get('account', {})
        positions = data.get('current_positions', [])
        market = data.get('market_data', {})
        summary = data.get('summary', {})

        # Build market data section with ALL scalping data
        market_text = ""
        for symbol, coin in market.items():
            tech = coin.get('technical', {})
            fr = coin.get('funding_rate', 0)
            ls = coin.get('long_short_ratio', {})
            ls_val = ls.get('long_short_ratio', 1.0) if isinstance(ls, dict) else 1.0

            market_text += f"""
{symbol}:
  Price: ${coin['price']:,.2f}
  Trend: {tech['trend']} | Momentum: {tech['momentum']} | Volatility: {tech.get('volatility', 'N/A')}
  Fast EMAs (Scalping): EMA9={tech.get('ema_9', 0):,.2f}, EMA21={tech.get('ema_21', 0):,.2f}, EMA55={tech.get('ema_55', 0):,.2f}
  Standard EMAs: EMA20={tech['ema_20']:,.2f}, EMA50={tech['ema_50']:,.2f}, EMA200={tech['ema_200']:,.2f}
  RSI-7 (Fast): {tech.get('rsi_7', 50):.1f} | RSI-14: {tech['rsi_14']:.1f} | Volume Ratio: {tech.get('volume_ratio', 1.0):.2f}
  MACD Histogram: {tech.get('macd_histogram', 0):.4f} | ATR: {tech.get('atr_14', 0):.4f}
  Funding Rate: {fr:.6f} ({'POSITIVE=shorts pay' if fr > 0 else 'NEGATIVE=longs pay' if fr < 0 else 'neutral'})
  L/S Ratio: {ls_val:.2f}
  Technical Score: {tech['score']}/100 | Combined Score: {coin['combined_score']}/100
  Signal: {coin['combined_signal']} ({coin['signal_agreement']})
"""

        # Build positions section
        if positions:
            pos_text = ""
            for pos in positions:
                pos_text += f"""
  - {pos['symbol']}: {pos['side'].upper()} @ ${pos['entry_price']:,.2f}
    Current: ${pos['current_price']:,.2f} | PnL: {pos['pnl_percent']:+.2f}%
    Margin: ${pos['margin']:.2f} | Leverage: {pos['leverage']}x
"""
        else:
            pos_text = "  (No open positions)"

        stop_loss = config.STOP_LOSS_PERCENT
        take_profit = config.TAKE_PROFIT_PERCENT

        prompt = f"""You are ClawBot AI — an aggressive short-term crypto scalper on Binance Futures.
Your job: MAXIMIZE profit through fast entries and exits. You have FULL AUTHORITY.

=== ACCOUNT ===
Balance: ${account.get('balance_usdt', 0):,.2f} USDT
Available: ${account.get('available_margin', 0):,.2f} USDT
Max Positions: {self.max_positions}

=== CURRENT POSITIONS ===
{pos_text}

=== MARKET DATA ===
{market_text}

=== MARKET SUMMARY ===
Market Outlook: {summary.get('market_outlook', 'NEUTRAL')}
Bullish Coins: {summary.get('bullish_coins', 0)} | Bearish Coins: {summary.get('bearish_coins', 0)}
Best Opportunity: {summary.get('best_opportunity', 'None')} (Score: {summary.get('best_score', 0)})
Avg Funding Rate: {summary.get('avg_funding_rate', 0):.6f}
Risk Level: {summary.get('risk_level', 'MEDIUM')}

=== SCALPING RULES (20x LEVERAGE) ===

POSITION MANAGEMENT:
1. Hard stop loss at -{stop_loss}% — ALWAYS close, no exceptions
2. Take profit at +{take_profit}% — secure gains
3. Loss + trend AGAINST position → CLOSE immediately (don't wait for stop)
4. Profit ≥ 2% + momentum weakening (RSI-7 >75 for long, <25 for short) → CLOSE
5. Price drops below EMA-9 for long (or above for short) + in loss → CLOSE
6. Small loss but trend ALIGNED → HOLD (patience)

NEW ENTRIES:
1. Require 2+ ALIGNED signals (technical + sentiment + onchain)
2. Combined score >= {config.MIN_ENTRY_SCORE}
3. DON'T chase overbought (RSI-7 > 75) or oversold (RSI-7 < 25)
4. PREFER entries near EMA-9/EMA-21 support/resistance (pullback entries)
5. LOOK AT funding rate: high positive = crowded longs (careful with longs)
6. VOLUME RATIO > 1.0 is confirmation (volume supporting the move)
7. You CAN open MULTIPLE positions if you see multiple strong setups

RISK:
- Max {self.max_positions} simultaneous positions
- Default leverage: {config.DEFAULT_LEVERAGE}x, margin: ${config.DEFAULT_MARGIN}
- NEVER enter against clear market trend
- Reduce margin if risk_level is HIGH

You are AUTONOMOUS. Make your own decisions. Open/close/hold as you see fit.

Respond ONLY with this JSON format:
{{
  "analysis": {{
    "market_assessment": "<1-line market view>",
    "key_observations": ["observation1", "observation2"],
    "risk_warnings": ["warning1"] or []
  }},
  "decisions": [
    {{
      "action": "OPEN_LONG|OPEN_SHORT|CLOSE|HOLD",
      "symbol": "BTCUSDT",
      "reasoning": "<why this decision>",
      "leverage": 20,
      "margin": 10,
      "conviction": 0.8
    }}
  ],
  "confidence": 0.85
}}

If HOLD and no new opportunities, return empty decisions array.
Only valid JSON, no explanation outside the JSON."""

        return prompt

    async def _call_ai(self, prompt: str, model: str) -> Dict:
        """Call AI model for decision"""

        if model == "claude":
            return await self._call_claude(prompt)
        elif model == "kimi":
            return await self._call_kimi(prompt)
        elif model == "groq":
            return await self._call_groq(prompt)
        else:
            raise ValueError(f"Unknown model: {model}")

    async def _call_claude(self, prompt: str) -> Dict:
        """Call Claude API"""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=60.0
            )

            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code} - {response.text}")

            data = response.json()
            text = data['content'][0]['text']

            return self._parse_decision(text)

    async def _call_kimi(self, prompt: str) -> Dict:
        """Call Kimi API"""
        if not config.KIMI_API_KEY:
            raise ValueError("KIMI_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.moonshot.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.KIMI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "moonshot-v1-8k",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=60.0
            )

            if response.status_code != 200:
                raise Exception(f"Kimi API error: {response.status_code}")

            data = response.json()
            text = data['choices'][0]['message']['content']

            return self._parse_decision(text)

    async def _call_groq(self, prompt: str) -> Dict:
        """Call Groq API (FREE - Llama 3.1)"""
        groq_key = getattr(config, 'GROQ_API_KEY', '')
        if not groq_key:
            raise ValueError("GROQ_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",  # FREE tier
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=60.0
            )

            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.status_code}")

            data = response.json()
            text = data['choices'][0]['message']['content']

            return self._parse_decision(text)

    def _parse_decision(self, text: str) -> Dict:
        """Parse JSON decision from AI response"""
        # Find JSON in response
        start = text.find('{')
        end = text.rfind('}') + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        json_str = text[start:end]
        return json.loads(json_str)

    def _fallback_decision(self, data: Dict) -> Dict:
        """Fallback decision logic without AI — scalping rules"""
        logger.warning("Using fallback decision logic (scalping rules)")

        decisions = []
        positions = data.get('current_positions', [])
        market = data.get('market_data', {})
        summary = data.get('summary', {})

        stop_loss = config.STOP_LOSS_PERCENT
        take_profit = config.TAKE_PROFIT_PERCENT

        # Analyze existing positions
        for pos in positions:
            symbol = pos['symbol']
            pnl_pct = pos['pnl_percent']
            side = pos['side'].lower()

            coin_data = market.get(symbol, {})
            tech = coin_data.get('technical', {})
            trend = tech.get('trend', 'NEUTRAL')
            rsi_7 = tech.get('rsi_7', 50)
            ema_9 = tech.get('ema_9', pos['current_price'])

            # Decision logic — scalping thresholds from config
            should_close = False
            reason = ""

            # Stop loss
            if pnl_pct <= -stop_loss:
                should_close = True
                reason = f"Stop loss at {pnl_pct:.2f}% (limit: -{stop_loss}%)"
            # Take profit
            elif pnl_pct >= take_profit:
                should_close = True
                reason = f"Taking profit at {pnl_pct:.2f}% (target: +{take_profit}%)"
            # Profit + momentum weak
            elif pnl_pct >= 2 and (
                (side == 'long' and rsi_7 > 75) or
                (side == 'short' and rsi_7 < 25)
            ):
                should_close = True
                reason = f"Profit {pnl_pct:.2f}% + RSI-7 extreme ({rsi_7:.0f}), securing gains"
            # Trend against position + in loss
            elif pnl_pct < -1 and (
                (side == 'long' and 'BEARISH' in trend) or
                (side == 'short' and 'BULLISH' in trend)
            ):
                should_close = True
                reason = f"Trend ({trend}) against {side}, loss {pnl_pct:.2f}%"
            # Price below EMA-9 for long + in loss
            elif pnl_pct < 0 and side == 'long' and pos['current_price'] < ema_9:
                should_close = True
                reason = f"Price below EMA-9, loss {pnl_pct:.2f}%"
            elif pnl_pct < 0 and side == 'short' and pos['current_price'] > ema_9:
                should_close = True
                reason = f"Price above EMA-9, loss {pnl_pct:.2f}%"

            if should_close:
                decisions.append({
                    "action": "CLOSE",
                    "symbol": symbol,
                    "reasoning": reason,
                    "conviction": 0.7
                })
            else:
                decisions.append({
                    "action": "HOLD",
                    "symbol": symbol,
                    "reasoning": "Trend aligned, holding position",
                    "conviction": 0.6
                })

        # Look for new opportunities
        if len(positions) < self.max_positions:
            best = summary.get('best_opportunity')
            best_score = summary.get('best_score', 0)
            if best and best_score >= config.MIN_ENTRY_SCORE:
                coin_data = market.get(best, {})
                signal = coin_data.get('combined_signal', 'NEUTRAL')
                tech = coin_data.get('technical', {})
                rsi_7 = tech.get('rsi_7', 50)

                # Don't chase extremes
                if 25 <= rsi_7 <= 75:
                    if signal == 'BULLISH':
                        decisions.append({
                            "action": "OPEN_LONG",
                            "symbol": best,
                            "reasoning": f"Strong bullish signal (score: {best_score}, RSI-7: {rsi_7:.0f})",
                            "leverage": config.DEFAULT_LEVERAGE,
                            "margin": config.DEFAULT_MARGIN,
                            "conviction": 0.7
                        })
                    elif signal == 'BEARISH':
                        decisions.append({
                            "action": "OPEN_SHORT",
                            "symbol": best,
                            "reasoning": f"Strong bearish signal (score: {best_score}, RSI-7: {rsi_7:.0f})",
                            "leverage": config.DEFAULT_LEVERAGE,
                            "margin": config.DEFAULT_MARGIN,
                            "conviction": 0.7
                        })

        return {
            "ai_model": "fallback_scalping_rules",
            "analysis": {
                "market_assessment": f"Market: {summary.get('market_outlook', 'NEUTRAL')}",
                "key_observations": ["Using fallback scalping rules due to AI failure"],
                "risk_warnings": ["AI unavailable, using rule-based scalping logic"]
            },
            "decisions": decisions,
            "confidence": 0.5
        }

    def _log_decision(self, decision: Dict):
        """Log decision summary"""
        logger.info(f"🧠 AI Decision Summary:")
        logger.info(f"   Model: {decision.get('ai_model', 'unknown')}")
        logger.info(f"   Assessment: {decision.get('analysis', {}).get('market_assessment', 'N/A')}")
        logger.info(f"   Confidence: {decision.get('confidence', 0)*100:.0f}%")

        for d in decision.get('decisions', []):
            action = d.get('action', 'UNKNOWN')
            symbol = d.get('symbol', '')
            reason = d.get('reasoning', '')[:50]
            logger.info(f"   → {action} {symbol}: {reason}...")
