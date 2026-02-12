"""
ClawBot AI — Main Engine (Orchestrator)
Runs the complete cycle: data → indicators → AI → execute → save
Must complete under 30 seconds on VPS (8GB RAM, 2 Core).
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any

from src.data.binance_rest import BinanceREST
from src.data.candle_store import CandleStore
from src.data.news_fetcher import NewsFetcher, FearGreedFetcher
from src.strategy import indicators
from src.strategy.regime import detect_regime
from src.ai.brain import AIBrain
from src.execution.order_manager import OrderManager
from src.execution.position_tracker import PositionTracker
from src.database.repository import Repository
from src.utils.cache import CycleCache
from src.utils.config import settings
from src.utils.logger import log
from src.utils.notifier import Notifier


class Engine:
    """
    Main orchestrator — runs one cycle per invocation (cron every 5 min).
    
    Flow:
    1. Check balance + positions + detect SL/TP triggered between cycles
    2. PARALLEL: fetch charts (3 TF) + news + market data
    3. Calculate indicators + regime
    4. Build JSON → send to AI → get decisions
    5. Execute orders + set safety SL/TP
    6. Save everything to Supabase (async)
    7. Notify Telegram/Discord
    """

    def __init__(self):
        self.client = BinanceREST()
        self.candles = CandleStore()
        self.news_fetcher = NewsFetcher()
        self.fear_greed_fetcher = FearGreedFetcher()
        self.ai = AIBrain()
        self.order_manager = OrderManager(self.client)
        self.tracker = PositionTracker(self.client)
        self.repo = Repository()
        self.cache = CycleCache()
        self.notifier = Notifier()

    async def run_cycle(self, cycle_number: int = 0, dry_run: bool = False):
        """
        Execute one complete trading cycle.
        Args:
            cycle_number: cycle counter
            dry_run: if True, skip actual order execution
        """
        self.cache.reset()
        self.cache.cycle_number = cycle_number
        self.cache.cycle_id = f"c_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"

        log.info(f"{'='*60}")
        log.info(f"🔄 Cycle #{cycle_number} — {self.cache.cycle_id}")
        log.info(f"{'='*60}")

        try:
            # ===== STEP 1: Account + Position Check =====
            t0 = time.time()
            positions, closed_between, balance, available = await self.tracker.update()
            self.cache.positions = positions
            self.cache.closed_between_cycles = closed_between
            self.cache.balance = balance
            self.cache.available_margin = available
            self.cache.set_timing("account", int((time.time() - t0) * 1000))

            log.info(f"💰 Balance: {balance:.2f} USDT | Positions: {len(positions)} | Closed between: {len(closed_between)}")

            # ===== STEP 2-4: PARALLEL DATA FETCH =====
            t1 = time.time()
            symbols = settings.symbols_list

            chart_task = self._fetch_all_charts(symbols)
            news_task = self._fetch_news_with_timeout()
            market_task = self._fetch_market_data(symbols)
            whale_task = self._fetch_whale_data(symbols)

            chart_result, news_result, market_result, whale_result = await asyncio.gather(
                chart_task, news_task, market_task, whale_task,
                return_exceptions=True,
            )

            # Handle exceptions
            if isinstance(chart_result, Exception):
                log.error(f"Chart fetch failed: {chart_result}")
            if isinstance(news_result, Exception):
                log.warning(f"News fetch failed: {news_result}")
            if isinstance(whale_result, Exception):
                log.warning(f"Whale data fetch failed: {whale_result}")

            self.cache.set_timing("data_fetch", int((time.time() - t1) * 1000))

            # ===== STEP 5: Refresh charts if news was slow =====
            news_elapsed = self.cache.phase_timings.get("news_fetch", 0)
            if news_elapsed > 5000:  # >5 seconds
                log.info(f"📊 Refreshing charts (news took {news_elapsed}ms)...")
                await self._fetch_all_charts(symbols)

            # ===== Calculate Indicators + Regime =====
            t2 = time.time()
            for symbol in symbols:
                # Calculate for all TFs including macro
                for tf in [settings.TF_PRIMARY, settings.TF_SECONDARY, settings.TF_TERTIARY, settings.TF_MACRO]:
                    df = self.candles.get(symbol, tf)
                    if df is not None:
                        ind = indicators.calculate_all(df)
                        if symbol not in self.cache.indicators:
                            self.cache.indicators[symbol] = {}
                        self.cache.indicators[symbol][tf] = ind

                # Regime from 5m indicators
                ind_5m = self.cache.indicators.get(symbol, {}).get("5m", {})
                self.cache.regimes[symbol] = detect_regime(ind_5m)

                # Current price
                self.cache.prices[symbol] = self.candles.get_latest_price(symbol)

            self.cache.set_timing("indicators", int((time.time() - t2) * 1000))

            # ===== STEP 6: AI Decision =====
            t3 = time.time()
            risk_config = {
                "balance_tier": self._get_balance_tier(balance),
                "suggested_risk_pct": f"{settings.get_risk_pct(balance):.0f}",
                "min_order_usdt": settings.MIN_ORDER_USDT,
            }
            ai_input = self.cache.build_ai_input(risk_config)

            ai_result = await self.ai.decide(ai_input)
            self.cache.ai_output_json = ai_result
            self.cache.ai_analysis = ai_result.get("analysis", "")
            self.cache.ai_actions = ai_result.get("actions", [])
            meta = ai_result.get("meta", {})
            self.cache.ai_model = meta.get("model", "")
            self.cache.ai_latency_ms = meta.get("latency_ms", 0)
            self.cache.ai_cost_usd = meta.get("cost_usd", 0)
            self.cache.ai_prompt_tokens = meta.get("prompt_tokens", 0)
            self.cache.ai_completion_tokens = meta.get("completion_tokens", 0)

            self.cache.set_timing("ai", int((time.time() - t3) * 1000))
            log.info(f"🤖 AI: {self.cache.ai_analysis[:100]}...")
            log.info(f"📋 Actions: {len(self.cache.ai_actions)}")

            # ===== STEP 7: Execute Orders =====
            t4 = time.time()
            if dry_run:
                log.info("🧪 DRY RUN — skipping order execution")
                self.cache.executed_trades = []
            else:
                self.cache.executed_trades = await self.order_manager.execute_actions(
                    self.cache.ai_actions, balance,
                )
            self.cache.set_timing("execution", int((time.time() - t4) * 1000))

            # ===== STEP 8: Save + Notify (async) =====
            t5 = time.time()
            save_task = self.repo.save_all(self.cache)

            # Notify trades
            notify_tasks = []
            for trade in self.cache.executed_trades:
                notify_tasks.append(self.notifier.notify_trade(trade))

            await asyncio.gather(save_task, *notify_tasks, return_exceptions=True)
            self.cache.set_timing("save_notify", int((time.time() - t5) * 1000))

            # Summary
            total_ms = int((time.time() - t0) * 1000)
            log.info(f"✅ Cycle #{cycle_number} completed in {total_ms}ms")
            log.info(f"   Timings: {self.cache.phase_timings}")

        except Exception as e:
            log.error(f"❌ Cycle #{cycle_number} failed: {e}")
            await self.notifier.notify_error(f"Cycle #{cycle_number}: {e}")

        finally:
            await self.client.close()
            await self.news_fetcher.close()

    async def _fetch_all_charts(self, symbols):
        """Fetch candles for all symbols and all timeframes."""
        tasks = []
        tf_map = {
            settings.TF_PRIMARY: settings.CANDLES_PRIMARY,
            settings.TF_SECONDARY: settings.CANDLES_SECONDARY,
            settings.TF_TERTIARY: settings.CANDLES_TERTIARY,
            settings.TF_MACRO: settings.CANDLES_MACRO,
        }
        for symbol in symbols:
            for tf, limit in tf_map.items():
                tasks.append(self._fetch_candles_single(symbol, tf, limit))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_candles_single(self, symbol: str, tf: str, limit: int):
        """Fetch candles for one symbol/TF and store."""
        try:
            raw = await self.client.get_klines(symbol, tf, limit)
            self.candles.store(symbol, tf, raw)
        except Exception as e:
            log.warning(f"Failed to fetch {symbol} {tf}: {e}")

    async def _fetch_news_with_timeout(self):
        """Fetch news with timing tracked."""
        t = time.time()
        try:
            news = await asyncio.wait_for(
                self.news_fetcher.fetch_all(),
                timeout=settings.NEWS_TIMEOUT_SECONDS,
            )
            self.cache.news = news
            self.cache.news_is_cached = False
        except asyncio.TimeoutError:
            log.warning(f"News timed out after {settings.NEWS_TIMEOUT_SECONDS}s — using cache")
            cached, _ = self.news_fetcher.get_cached()
            self.cache.news = cached
            self.cache.news_is_cached = True
        finally:
            self.cache.set_timing("news_fetch", int((time.time() - t) * 1000))

    async def _fetch_market_data(self, symbols):
        """Fetch funding rate, L/S ratio, fear & greed."""
        tasks = []
        for symbol in symbols:
            tasks.append(self._fetch_symbol_market_data(symbol))
        tasks.append(self._fetch_fear_greed())
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_symbol_market_data(self, symbol: str):
        """Fetch market data for a single symbol."""
        try:
            # Funding rate
            fr = await self.client.get_funding_rate(symbol)
            if fr and isinstance(fr, list) and len(fr) > 0:
                self.cache.funding_rates[symbol] = float(fr[0].get("fundingRate", 0))

            # Long/Short ratio
            ls = await self.client.get_long_short_ratio(symbol)
            if ls and isinstance(ls, list) and len(ls) > 0:
                self.cache.long_short_ratios[symbol] = float(ls[0].get("longShortRatio", 0))

            # 24h stats
            stats = await self.client.get_ticker_24h(symbol)
            if stats:
                self.cache.volume_24h[symbol] = float(stats.get("quoteVolume", 0))
                self.cache.price_changes[symbol] = {
                    "5m": 0,  # calculated from candles
                    "1h": 0,
                    "24h": float(stats.get("priceChangePercent", 0)),
                }
        except Exception as e:
            log.warning(f"Market data failed for {symbol}: {e}")

    async def _fetch_whale_data(self, symbols):
        """Fetch whale data (taker ratio, top traders, depth) for all symbols."""
        tasks = []
        for symbol in symbols:
            tasks.append(self._fetch_single_whale_data(symbol))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_single_whale_data(self, symbol: str):
        """Fetch all whale metrics for one symbol."""
        try:
            # Parallel fetch within symbol
            taker, accounts, positions, depth, oi = await asyncio.gather(
                self.client.get_taker_buy_sell_ratio(symbol),
                self.client.get_top_trader_account_ratio(symbol),
                self.client.get_top_trader_position_ratio(symbol),
                self.client.get_order_book_depth(symbol),
                self.client.get_open_interest(symbol),
                return_exceptions=True
            )
            
            # Store in cache
            if not isinstance(taker, Exception) and taker and isinstance(taker, list):
                 self.cache.taker_buy_sell[symbol] = taker[-1]

            if not isinstance(accounts, Exception) and accounts and isinstance(accounts, list):
                 self.cache.top_trader_accounts[symbol] = accounts[-1]

            if not isinstance(positions, Exception) and positions and isinstance(positions, list):
                 self.cache.top_trader_positions[symbol] = positions[-1]

            if not isinstance(depth, Exception) and depth:
                 self.cache.order_book_imbalance[symbol] = depth

            if not isinstance(oi, Exception) and oi:
                 val = oi.get("openInterest", 0)
                 self.cache.open_interest[symbol] = float(val)

        except Exception as e:
             log.warning(f"Whale data fetch failed for {symbol}: {e}")

    async def _fetch_fear_greed(self):
        """Fetch Fear & Greed Index."""
        self.cache.fear_greed = await self.fear_greed_fetcher.fetch()

    def _get_balance_tier(self, balance: float) -> str:
        """Get human-readable balance tier."""
        if balance < 50:
            return "<$50"
        elif balance < 100:
            return "$50-100"
        elif balance < 300:
            return "$100-300"
        elif balance < 1000:
            return "$300-1000"
        else:
            return ">$1000"
