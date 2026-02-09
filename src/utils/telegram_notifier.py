"""
Telegram Notifier
Sends notifications to Telegram chat
"""

import asyncio
from telegram import Bot
from telegram.error import TelegramError

from src.utils.config import config
from src.utils.logger import logger


class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN) if config.TELEGRAM_BOT_TOKEN else None
        self.chat_id = config.TELEGRAM_CHAT_ID
        
    async def send_message(self, message: str):
        """Send message to Telegram"""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram not configured, skipping notification")
            return False
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.debug(f"Telegram sent: {message[:50]}...")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    async def send_trade_notification(self, action: str, symbol: str, details: dict):
        """Send formatted trade notification"""
        emoji = {
            'OPEN_LONG': '🟢',
            'OPEN_SHORT': '🔴',
            'CLOSE': '⚪',
            'HOLD': '⏸️'
        }.get(action, '📊')
        
        msg = f"{emoji} <b>{action}</b> {symbol}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        
        if details.get('price'):
            msg += f"💰 Price: ${details['price']:,.2f}\n"
        if details.get('leverage'):
            msg += f"⚡ Leverage: {details['leverage']}x\n"
        if details.get('margin'):
            msg += f"💵 Margin: ${details['margin']}\n"
        if details.get('pnl'):
            pnl = details['pnl']
            pnl_emoji = '📈' if pnl >= 0 else '📉'
            msg += f"{pnl_emoji} PnL: {pnl:+.2f}%\n"
        if details.get('reasoning'):
            msg += f"\n📝 {details['reasoning'][:100]}"
        
        await self.send_message(msg)
    
    async def send_cycle_summary(self, cycle_data: dict):
        """Send cycle summary notification"""
        cycle_id = cycle_data.get('cycle_id', 'N/A')[:19]
        decision = cycle_data.get('decision', {})
        
        msg = f"🔄 <b>Cycle Complete</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        msg += f"🕐 {cycle_id}\n\n"
        
        # Market assessment
        analysis = decision.get('analysis', {})
        if analysis.get('market_assessment'):
            msg += f"📊 {analysis['market_assessment'][:100]}\n\n"
        
        # Decisions
        for d in decision.get('decisions', []):
            action = d.get('action', 'HOLD')
            symbol = d.get('symbol', '')
            
            if action == 'OPEN_LONG':
                msg += f"🟢 OPEN LONG {symbol}\n"
            elif action == 'OPEN_SHORT':
                msg += f"🔴 OPEN SHORT {symbol}\n"
            elif action == 'CLOSE':
                msg += f"⚪ CLOSE {symbol}\n"
            else:
                msg += f"⏸️ HOLD\n"
        
        # Confidence
        if decision.get('confidence'):
            msg += f"\n🎯 Confidence: {decision['confidence']*100:.0f}%"
        
        await self.send_message(msg)
    
    async def send_error(self, error_message: str):
        """Send error notification"""
        msg = f"❌ <b>Error</b>\n{error_message[:500]}"
        await self.send_message(msg)


# Create singleton
telegram = TelegramNotifier()
