"""
ClawBot AI — Automated Crypto Scalping Bot
Main entry point — runs 2-minute cycles on Binance Futures

Architecture:
  Collect (Binance + News + OnChain) → Process (Technical + Sentiment)
  → Aggregate → AI Decision → Execute Trades → Notify

Free stack: Groq AI + RSS + Scraping + Binance API
"""

import asyncio
import gc
import uuid
from datetime import datetime, timedelta
import traceback

# Import modules
from src.utils.config import config
from src.utils.logger import logger
from src.utils.telegram_notifier import telegram

from src.collectors import BinanceCollector, NewsCollector, OnchainCollector
from src.processors import TechnicalProcessor, SentimentProcessor, DataAggregator
from src.brain import AIBrain
from src.executor import BinanceTrader
from src.database import db


class TradingBot:
    """Main trading bot orchestrator — scalping mode"""

    def __init__(self):
        # Initialize components
        self.binance_collector = BinanceCollector()
        self.news_collector = NewsCollector()
        self.onchain_collector = OnchainCollector()

        self.technical_processor = TechnicalProcessor()
        self.sentiment_processor = SentimentProcessor()
        self.aggregator = DataAggregator()

        self.brain = AIBrain()
        self.trader = BinanceTrader()

        self.cycle_interval = config.CYCLE_INTERVAL_SECONDS
        self._last_cleanup = datetime.utcnow()
        self._cleanup_interval = timedelta(hours=24)

    async def run_cycle(self) -> dict:
        """Run a single trading cycle"""
        cycle_id = f"cycle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info("=" * 60)
        logger.info(f"🔄 Starting Trading Cycle: {cycle_id}")
        logger.info("=" * 60)

        result = {
            "cycle_id": cycle_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "status": "RUNNING",
            "errors": []
        }

        try:
            # Create cycle in database
            await db.create_cycle(cycle_id)

            # ====================================
            # PHASE 1: DATA COLLECTION (parallel)
            # ====================================
            logger.info("\n📥 PHASE 1: Collecting Data...")

            # Collect all data in parallel
            binance_data, news_data, onchain_data = await asyncio.gather(
                self.binance_collector.collect(),
                self.news_collector.collect(),
                self.onchain_collector.collect(),
                return_exceptions=True
            )

            # Handle collection errors gracefully
            if isinstance(binance_data, Exception):
                logger.error(f"Binance collection failed: {binance_data}")
                result['errors'].append(f"Binance: {binance_data}")
                binance_data = {"coins": []}

            if isinstance(news_data, Exception):
                logger.error(f"News collection failed: {news_data}")
                result['errors'].append(f"News: {news_data}")
                news_data = {"articles": []}

            if isinstance(onchain_data, Exception):
                logger.error(f"On-chain collection failed: {onchain_data}")
                result['errors'].append(f"Onchain: {onchain_data}")
                onchain_data = {"metrics": {}}

            # Store raw data
            await asyncio.gather(
                db.store_raw_binance(cycle_id, binance_data),
                db.store_raw_news(cycle_id, news_data),
                db.store_raw_onchain(cycle_id, onchain_data)
            )

            # ====================================
            # PHASE 2: DATA PROCESSING
            # ====================================
            logger.info("\n⚙️ PHASE 2: Processing Data...")

            # Process technical indicators
            technical_data = self.technical_processor.process(binance_data)

            # Process sentiment with AI
            sentiment_data = await self.sentiment_processor.process(news_data)

            # Store processed data
            await asyncio.gather(
                db.store_processed_technical(cycle_id, technical_data),
                db.store_processed_sentiment(cycle_id, sentiment_data)
            )

            # ====================================
            # PHASE 3: GET ACCOUNT STATE
            # ====================================
            logger.info("\n💰 PHASE 3: Getting Account State...")

            balance = await self.trader.get_account_balance()
            positions = await self.trader.get_positions()

            logger.info(f"   Balance: ${balance.get('total', 0):,.2f} USDT")
            logger.info(f"   Open Positions: {len(positions)}")

            # ====================================
            # PHASE 4: AGGREGATE DATA
            # ====================================
            logger.info("\n📊 PHASE 4: Aggregating Data...")

            aggregated = self.aggregator.aggregate(
                technical=technical_data,
                sentiment=sentiment_data,
                onchain=onchain_data,
                binance_raw=binance_data,  # Pass raw for funding rate + L/S ratio
                positions=positions,
                balance=balance,
                cycle_id=cycle_id
            )

            await db.store_aggregated_data(cycle_id, aggregated)

            # ====================================
            # PHASE 5: AI DECISION
            # ====================================
            logger.info("\n🧠 PHASE 5: AI Analysis...")

            decision = await self.brain.make_decision(aggregated)

            await db.store_ai_decision(cycle_id, decision)

            # ====================================
            # PHASE 6: EXECUTE TRADES
            # ====================================
            logger.info("\n🚀 PHASE 6: Executing Trades...")

            decisions = decision.get('decisions', [])
            trades_executed = 0

            for d in decisions:
                action = d.get('action', 'HOLD')
                symbol = d.get('symbol', '')
                reasoning = d.get('reasoning', '')

                if action in ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE']:
                    logger.info(f"   Executing: {action} {symbol}")

                    exec_result = await self.trader.execute_decision(d)

                    # Store trade
                    await db.store_trade(
                        cycle_id=cycle_id,
                        action=action,
                        symbol=symbol,
                        result=exec_result,
                        reasoning=reasoning
                    )

                    # Send notification
                    await telegram.send_trade_notification(
                        action=action,
                        symbol=symbol,
                        details={
                            "price": exec_result.get('price', 0),
                            "leverage": d.get('leverage', 0),
                            "margin": d.get('margin', 0),
                            "pnl": exec_result.get('closed_pnl', 0),
                            "reasoning": reasoning
                        }
                    )

                    trades_executed += 1

                else:
                    logger.info(f"   HOLD: {symbol} - {reasoning[:50]}...")

            # ====================================
            # PHASE 7: COMPLETE CYCLE
            # ====================================
            result['status'] = 'COMPLETED'
            result['completed_at'] = datetime.utcnow().isoformat() + "Z"
            result['decisions_count'] = len(decisions)
            result['trades_executed'] = trades_executed

            await db.complete_cycle(cycle_id, "COMPLETED", result)

            # Send cycle summary
            await telegram.send_cycle_summary({
                "cycle_id": cycle_id,
                "decision": decision
            })

            logger.info("\n" + "=" * 60)
            logger.info(f"✅ Cycle Complete: {trades_executed} trades executed")
            logger.info("=" * 60)

        except Exception as e:
            error_msg = str(e)
            stack = traceback.format_exc()

            logger.error(f"Cycle failed: {error_msg}")
            logger.error(stack)

            result['status'] = 'FAILED'
            result['errors'].append(error_msg)

            await db.log_error(cycle_id, "CYCLE_ERROR", error_msg, stack)
            await db.complete_cycle(cycle_id, "FAILED", result)
            await telegram.send_error(f"Cycle {cycle_id} failed: {error_msg}")

        # Memory cleanup for VPS
        gc.collect()

        return result

    async def _periodic_cleanup(self):
        """Run cleanup tasks periodically (every 24h)"""
        now = datetime.utcnow()
        if now - self._last_cleanup >= self._cleanup_interval:
            logger.info("🧹 Running periodic data cleanup...")
            try:
                await db.cleanup_old_data(days=30)
                self._last_cleanup = now
                logger.info("🧹 Cleanup complete")
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")

    async def run(self):
        """Main run loop"""
        logger.info("🤖 ClawBot AI Starting...")
        logger.info(f"   Cycle interval: {self.cycle_interval}s")
        logger.info(f"   Max positions: {config.MAX_POSITIONS}")
        logger.info(f"   Leverage: {config.DEFAULT_LEVERAGE}x")
        logger.info(f"   Stop Loss: -{config.STOP_LOSS_PERCENT}%")
        logger.info(f"   Take Profit: +{config.TAKE_PROFIT_PERCENT}%")
        logger.info(f"   Primary AI: {config.PRIMARY_AI_MODEL}")

        # Validate config
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Config validation failed: {e}")
            return

        # Send startup notification
        await telegram.send_message(
            f"🤖 <b>ClawBot AI Started</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ Interval: {self.cycle_interval}s\n"
            f"📊 Max Positions: {config.MAX_POSITIONS}\n"
            f"⚡ Leverage: {config.DEFAULT_LEVERAGE}x\n"
            f"🛑 SL: -{config.STOP_LOSS_PERCENT}% | TP: +{config.TAKE_PROFIT_PERCENT}%\n"
            f"🧠 AI: {config.PRIMARY_AI_MODEL}"
        )

        # Run first cycle immediately
        await self.run_cycle()

        # Then run on interval
        while True:
            logger.info(f"\n⏳ Waiting {self.cycle_interval}s for next cycle...")
            await asyncio.sleep(self.cycle_interval)
            await self._periodic_cleanup()
            await self.run_cycle()


async def main():
    """Entry point"""
    bot = TradingBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        # Cleanup scraper browser
        if hasattr(bot.news_collector, 'close'):
            await bot.news_collector.close()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
