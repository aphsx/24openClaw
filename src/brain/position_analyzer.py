from typing import Dict, List, Any
from src.utils.config import config
from src.utils.logger import logger


class PositionAnalyzer:
    """Analyzes positions using trend-based logic - Optimized for Scalping"""
    
    def __init__(self):
        # Use config for dynamic risk parameters
        self.stop_loss_pct = config.STOP_LOSS_PERCENT  # -3% for 20x
        self.take_profit_pct = config.TAKE_PROFIT_PERCENT  # +5% target
    
    def analyze(self, position: Dict, market_data: Dict) -> Dict:
        """
        Analyze a position and recommend action
        
        Logic Priority:
        1. TREND ALIGNMENT - Is position direction aligned with market trend?
        2. MOMENTUM STATUS - Is momentum strengthening or weakening?
        3. PnL only for profit-taking, NOT for holding decision
        
        SCALPING MODE: Tighter stops, faster exits
        """
        symbol = position.get('symbol', '')
        side = position.get('side', '').lower()
        pnl_pct = position.get('pnl_percent', 0)
        entry_price = position.get('entry_price', 0)
        current_price = position.get('current_price', 0)
        
        # Get market data for this coin
        coin_data = market_data.get(symbol, {})
        tech = coin_data.get('technical', {})
        
        trend = tech.get('trend', 'NEUTRAL')
        momentum = tech.get('momentum', 'NEUTRAL')
        rsi_7 = tech.get('rsi_7', 50)  # Fast RSI for scalping
        rsi_14 = tech.get('rsi_14', 50)
        score = tech.get('score', 50)
        ema_9 = tech.get('ema_9', current_price)  # Fast EMA
        ema_21 = tech.get('ema_21', current_price)
        volume_ratio = tech.get('volume_ratio', 1)
        
        # Initialize analysis
        analysis = {
            "symbol": symbol,
            "side": side.upper(),
            "action": "HOLD",
            "pnl_percent": pnl_pct,
            "trend": trend,
            "momentum": momentum,
            "reasoning": "",
            "conviction": 0.5
        }
        
        # ====================================
        # CORE LOGIC: SCALPING EXITS
        # ====================================
        
        # Check if trend ALIGNED with position
        trend_aligned = (
            (side == 'long' and 'BULLISH' in trend) or
            (side == 'short' and 'BEARISH' in trend)
        )
        
        # Check if trend AGAINST position
        trend_against = (
            (side == 'long' and 'BEARISH' in trend) or
            (side == 'short' and 'BULLISH' in trend)
        )
        
        # Scalping momentum signals (use fast RSI-7)
        momentum_weakening = (
            (side == 'long' and rsi_7 > 75) or  # Overbought for long
            (side == 'short' and rsi_7 < 25) or  # Oversold for short
            volume_ratio < 0.5 or  # Volume drying up
            score < 45  # Score dropping fast
        )
        
        # Fast EMA cross check
        ema_crossed = (
            (side == 'long' and current_price < ema_9) or
            (side == 'short' and current_price > ema_9)
        )
        
        # ====================================
        # DECISION CASES - SCALPING MODE
        # ====================================
        
        # CASE 1: HARD STOP LOSS (use config value)
        if pnl_pct <= -self.stop_loss_pct:
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"🛑 Stop loss: {pnl_pct:.2f}% ถึง -{self.stop_loss_pct}% ตัดทันที (20x leverage)"
            analysis['conviction'] = 0.99
            
        # CASE 2: LOSS + TREND AGAINST = CLOSE IMMEDIATELY
        elif pnl_pct < -1 and trend_against:
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"❌ ขาดทุน {abs(pnl_pct):.2f}% + trend สวน ({trend}) ตัดก่อนเสียมากกว่านี้"
            analysis['conviction'] = 0.9
            
        # CASE 3: LOSS + EMA CROSSED = WARNING, consider close
        elif pnl_pct < 0 and ema_crossed:
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"⚠️ ขาดทุน {abs(pnl_pct):.2f}% + ราคาหลุด EMA9 สัญญาณอ่อน ตัดขาดทุน"
            analysis['conviction'] = 0.75
            
        # CASE 4: TAKE PROFIT when target reached
        elif pnl_pct >= self.take_profit_pct:
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"💰 เป้าหมาย! กำไร {pnl_pct:.2f}% >= {self.take_profit_pct}% เก็บกำไร"
            analysis['conviction'] = 0.95
            
        # CASE 5: PROFIT + MOMENTUM WEAK = SECURE PROFIT
        elif pnl_pct >= 2 and momentum_weakening:
            weak_reasons = []
            if side == 'long' and rsi_7 > 75:
                weak_reasons.append("RSI-7 overbought")
            if side == 'short' and rsi_7 < 25:
                weak_reasons.append("RSI-7 oversold")
            if volume_ratio < 0.5:
                weak_reasons.append("volume อ่อน")
            
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"💰 กำไร {pnl_pct:.2f}% + sัญญาณอ่อน ({', '.join(weak_reasons)}) เก็บก่อน"
            analysis['conviction'] = 0.8
            
        # CASE 6: PROFIT + TREND AGAINST = TAKE PROFIT
        elif pnl_pct >= 1.5 and trend_against:
            analysis['action'] = 'CLOSE'
            analysis['reasoning'] = f"💰 กำไร {pnl_pct:.2f}% + trend เปลี่ยน ({trend}) เก็บกำไรก่อนกลับตัว"
            analysis['conviction'] = 0.85
            
        # CASE 7: SMALL LOSS BUT TREND ALIGNED = HOLD (patience)
        elif pnl_pct >= -2 and trend_aligned and not ema_crossed:
            analysis['action'] = 'HOLD'
            analysis['reasoning'] = f"💎 ขาดทุนเล็กน้อย {abs(pnl_pct):.2f}% แต่ {side.upper()} + {trend} ถูกทาง รอกลับ"
            analysis['conviction'] = 0.6
            
        # CASE 8: DEFAULT HOLD
        else:
            analysis['action'] = 'HOLD'
            analysis['reasoning'] = f"⏸️ รอ | PnL: {pnl_pct:+.2f}% | Trend: {trend} | RSI-7: {rsi_7:.0f}"
            analysis['conviction'] = 0.5
        
        return analysis
    
    def analyze_all(self, positions: List[Dict], market_data: Dict) -> List[Dict]:
        """Analyze all positions"""
        results = []
        
        for pos in positions:
            analysis = self.analyze(pos, market_data)
            results.append(analysis)
            
            # Log
            action = analysis['action']
            symbol = analysis['symbol']
            reason = analysis['reasoning']
            emoji = '✅' if action == 'HOLD' else '❌' if action == 'CLOSE' else '📊'
            logger.info(f"{emoji} {symbol}: {action} - {reason}")
        
        return results


# Test
def test_analyzer():
    """Test position analyzer"""
    analyzer = PositionAnalyzer()
    
    # Test case: Loss but trend aligned (should HOLD)
    position = {
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_price": 72000,
        "current_price": 70000,
        "pnl_percent": -2.8
    }
    
    market_data = {
        "BTCUSDT": {
            "technical": {
                "trend": "BULLISH",
                "momentum": "NEUTRAL",
                "score": 65,
                "rsi_14": 55,
                "ema_20": 69500,
                "volume_ratio": 1.2
            }
        }
    }
    
    result = analyzer.analyze(position, market_data)
    print(f"\n{'='*50}")
    print("Position Analyzer Test")
    print(f"{'='*50}")
    print(f"Position: {position['side'].upper()} at ${position['entry_price']}")
    print(f"Current: ${position['current_price']} ({position['pnl_percent']:.2f}%)")
    print(f"Market Trend: {market_data['BTCUSDT']['technical']['trend']}")
    print(f"\nDecision: {result['action']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Conviction: {result['conviction']*100:.0f}%")


if __name__ == "__main__":
    test_analyzer()
