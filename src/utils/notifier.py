"""
ClawBot AI — Notification Module
Sends trade alerts and daily summaries to Telegram + Discord.
"""
import asyncio
from typing import Optional

import aiohttp

from src.utils.config import settings
from src.utils.logger import log


class Notifier:
    """Send notifications to Telegram and Discord."""

    async def send(self, message: str):
        """Send message to all enabled channels."""
        tasks = []
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            tasks.append(self._send_telegram(message))
        if settings.DISCORD_WEBHOOK_URL:
            tasks.append(self._send_discord(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_trade(self, trade: dict):
        """Format and send trade notification."""
        action = trade.get("action", "")
        symbol = trade.get("symbol", "")
        side = trade.get("side", "")

        if action == "OPEN":
            emoji = "🟢" if side == "LONG" else "🔴"
            msg = (
                f"{emoji} **{action} {side}** {symbol}\n"
                f"💰 Entry: {trade.get('entry_price', 0)}\n"
                f"📦 Qty: {trade.get('quantity', 0)}\n"
                f"💵 Margin: {trade.get('margin_usdt', 0)} USDT\n"
                f"🎯 Leverage: {trade.get('leverage', 20)}x\n"
                f"🧠 Confidence: {trade.get('ai_confidence', 0)}%\n"
                f"📝 {trade.get('ai_reason', '')}"
            )
        elif action == "CLOSE":
            pnl = trade.get("realized_pnl", 0)
            pnl_pct = trade.get("realized_pnl_pct", 0)
            emoji = "✅" if pnl >= 0 else "❌"
            msg = (
                f"{emoji} **CLOSE {side}** {symbol}\n"
                f"💰 Entry: {trade.get('entry_price', 0)} → Exit: {trade.get('exit_price', 0)}\n"
                f"📊 PnL: {pnl:+.4f} USDT ({pnl_pct:+.1f}%)\n"
                f"📝 {trade.get('ai_reason', '')}"
            )
        else:
            msg = f"📋 {action} {symbol}: {trade.get('ai_reason', '')}"

        await self.send(msg)

    async def notify_cycle_summary(self, cycle_data: dict):
        """Send cycle summary."""
        msg = (
            f"⏰ **Cycle #{cycle_data.get('cycle_number', 0)}** completed\n"
            f"⏱️ Duration: {cycle_data.get('duration_ms', 0)}ms\n"
            f"💰 Balance: {cycle_data.get('balance_usdt', 0):.2f} USDT\n"
            f"📊 Actions: {cycle_data.get('actions_taken', 0)}\n"
            f"🤖 AI: {cycle_data.get('ai_model', '?')} ({cycle_data.get('ai_latency_ms', 0)}ms)"
        )
        await self.send(msg)

    async def notify_error(self, error: str):
        """Send error notification."""
        await self.send(f"🚨 **ClawBot Error**\n{error}")

    async def _send_telegram(self, message: str):
        """Send message via Telegram Bot API."""
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        log.warning(f"Telegram send failed: {resp.status}")
        except Exception as e:
            log.warning(f"Telegram error: {e}")

    async def _send_discord(self, message: str):
        """Send message via Discord webhook."""
        try:
            payload = {"content": message}
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(settings.DISCORD_WEBHOOK_URL, json=payload) as resp:
                    if resp.status not in (200, 204):
                        log.warning(f"Discord send failed: {resp.status}")
        except Exception as e:
            log.warning(f"Discord error: {e}")
