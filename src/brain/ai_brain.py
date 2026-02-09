"""
AI Brain - Decision Engine
Uses Claude or Kimi to make trading decisions based on aggregated data
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import httpx
import json

from src.utils.config import config
from src.utils.logger import logger


class AIBrain:
    """AI-powered trading decision engine"""
    
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
        """Build prompt for AI analysis"""
        
        account = data.get('account', {})
        positions = data.get('current_positions', [])
        market = data.get('market_data', {})
        summary = data.get('summary', {})
        
        # Build market data section
        market_text = ""
        for symbol, coin in market.items():
            tech = coin.get('technical', {})
            market_text += f"""
{symbol}:
  Price: ${coin['price']:,.2f}
  Trend: {tech['trend']} | Momentum: {tech['momentum']} | RSI: {tech['rsi_14']:.1f}
  EMAs: 20={tech['ema_20']:,.2f}, 50={tech['ema_50']:,.2f}, 200={tech['ema_200']:,.2f}
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
        
        prompt = f"""You are a professional crypto trading AI. Analyze this market data and make trading decisions.

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
Risk Level: {summary.get('risk_level', 'MEDIUM')}

=== DECISION RULES ===
1. POSITION ANALYSIS (for open positions):
   - If trend ALIGNED with position AND momentum strong → HOLD (let winner run)
   - If trend AGAINST position → CLOSE (cut losses)
   - If profit > 10% but momentum weakening → CLOSE (take profit)
   - If loss > -15% regardless of trend → CLOSE (stop loss)

2. NEW OPPORTUNITY (only if positions < max):
   - Require 2+ ALIGNED signals (technical + sentiment + onchain)
   - Combined score >= 70 = STRONG signal
   - NEVER chase when overbought (RSI > 70) or oversold (RSI < 30)
   
3. RISK MANAGEMENT:
   - Max {self.max_positions} positions at a time
   - Default leverage: 20x, margin: $10
   - Never enter when market outlook is opposite to trade direction

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

If all positions should HOLD and no new opportunities, return empty decisions array.
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
        """Fallback decision logic without AI"""
        logger.warning("Using fallback decision logic")
        
        decisions = []
        positions = data.get('current_positions', [])
        market = data.get('market_data', {})
        summary = data.get('summary', {})
        
        # Analyze existing positions
        for pos in positions:
            symbol = pos['symbol']
            pnl_pct = pos['pnl_percent']
            side = pos['side'].lower()
            
            coin_data = market.get(symbol, {})
            trend = coin_data.get('technical', {}).get('trend', 'NEUTRAL')
            
            # Decision logic
            should_close = False
            reason = ""
            
            # Stop loss
            if pnl_pct <= -15:
                should_close = True
                reason = f"Stop loss triggered at {pnl_pct:.2f}%"
            # Take profit
            elif pnl_pct >= 10:
                should_close = True
                reason = f"Taking profit at {pnl_pct:.2f}%"
            # Trend against position
            elif (side == 'long' and 'BEARISH' in trend) or (side == 'short' and 'BULLISH' in trend):
                should_close = True
                reason = f"Trend ({trend}) against {side} position"
            
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
            if best and summary.get('best_score', 0) >= 70:
                coin_data = market.get(best, {})
                signal = coin_data.get('combined_signal', 'NEUTRAL')
                
                if signal == 'BULLISH':
                    decisions.append({
                        "action": "OPEN_LONG",
                        "symbol": best,
                        "reasoning": f"Strong bullish signal (score: {summary['best_score']})",
                        "leverage": config.DEFAULT_LEVERAGE,
                        "margin": config.DEFAULT_MARGIN,
                        "conviction": 0.7
                    })
                elif signal == 'BEARISH':
                    decisions.append({
                        "action": "OPEN_SHORT",
                        "symbol": best,
                        "reasoning": f"Strong bearish signal (score: {summary['best_score']})",
                        "leverage": config.DEFAULT_LEVERAGE,
                        "margin": config.DEFAULT_MARGIN,
                        "conviction": 0.7
                    })
        
        return {
            "ai_model": "fallback_rules",
            "analysis": {
                "market_assessment": f"Market: {summary.get('market_outlook', 'NEUTRAL')}",
                "key_observations": ["Using fallback rules due to AI failure"],
                "risk_warnings": ["AI unavailable, using basic rules"]
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


# Test
async def test_brain():
    """Test the AI brain"""
    sample_data = {
        "cycle_id": "test_001",
        "account": {"balance_usdt": 1000, "available_margin": 900},
        "current_positions": [],
        "market_data": {
            "BTCUSDT": {
                "price": 70000,
                "technical": {"trend": "BULLISH", "momentum": "NEUTRAL", "score": 75,
                             "ema_20": 69500, "ema_50": 68000, "ema_200": 65000, "rsi_14": 55},
                "combined_score": 72,
                "combined_signal": "BULLISH",
                "signal_agreement": "2/3 ALIGNED"
            }
        },
        "summary": {
            "market_outlook": "BULLISH",
            "bullish_coins": 6,
            "bearish_coins": 2,
            "best_opportunity": "BTCUSDT",
            "best_score": 72,
            "risk_level": "LOW"
        }
    }
    
    brain = AIBrain()
    decision = await brain.make_decision(sample_data)
    print(f"\n{'='*50}")
    print("AI Brain Test")
    print(f"{'='*50}")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    asyncio.run(test_brain())
