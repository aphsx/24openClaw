"""
ClawBot AI — Supabase Repository
Async data insertion for historical analysis (NOT used during cycle for reads).
Insert only — after cycle completes.
"""
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.utils.config import settings
from src.utils.logger import log

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    log.warning("Supabase not installed — data will not be saved to database")


class Repository:
    """
    Async Supabase data layer.
    All inserts are fire-and-forget — never blocks the main cycle.
    Used for historical analysis/dashboard only.
    """

    def __init__(self):
        self._client: Optional[Any] = None

    def _get_client(self):
        if not SUPABASE_AVAILABLE:
            return None
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return None
        if self._client is None:
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self._client

    async def save_cycle(self, cycle_data: dict) -> Optional[str]:
        """Insert cycle record. Returns cycle ID."""
        client = self._get_client()
        if not client:
            return None
        try:
            result = client.table("cycles").insert(cycle_data).execute()
            if result.data:
                cycle_id = result.data[0].get("id")
                log.debug(f"Saved cycle: {cycle_id}")
                return cycle_id
        except Exception as e:
            log.error(f"Failed to save cycle: {e}")
        return None

    async def save_raw_data(self, raw_data_list: List[dict]):
        """Insert raw data records for a cycle."""
        client = self._get_client()
        if not client or not raw_data_list:
            return
        try:
            client.table("cycle_raw_data").insert(raw_data_list).execute()
            log.debug(f"Saved {len(raw_data_list)} raw data records")
        except Exception as e:
            log.error(f"Failed to save raw data: {e}")

    async def save_ai_decision(self, decision_data: dict):
        """Insert AI decision record."""
        client = self._get_client()
        if not client:
            return
        try:
            client.table("ai_decisions").insert(decision_data).execute()
            log.debug("Saved AI decision")
        except Exception as e:
            log.error(f"Failed to save AI decision: {e}")

    async def save_trades(self, trades: List[dict]):
        """Insert trade records."""
        client = self._get_client()
        if not client or not trades:
            return
        try:
            client.table("trades").insert(trades).execute()
            log.debug(f"Saved {len(trades)} trades")
        except Exception as e:
            log.error(f"Failed to save trades: {e}")

    async def save_daily_summary(self, summary: dict):
        """Insert or update daily summary."""
        client = self._get_client()
        if not client:
            return
        try:
            client.table("daily_summary").upsert(summary, on_conflict="date").execute()
            log.debug(f"Saved daily summary for {summary.get('date')}")
        except Exception as e:
            log.error(f"Failed to save daily summary: {e}")

    async def save_all(self, cache) -> Optional[str]:
        """
        Save everything from a completed cycle cache to Supabase.
        This is called AFTER the cycle completes — async, non-blocking.
        """
        from datetime import datetime, timezone
        import json

        # 1. Save cycle
        cycle_row = cache.to_supabase_cycle()
        cycle_id = await self.save_cycle(cycle_row)
        if not cycle_id:
            return None

        # 2. Save raw data
        raw_data = []
        now = datetime.now(timezone.utc).isoformat()

        # Indicators per symbol per TF
        for symbol, tf_data in cache.indicators.items():
            for tf, indicators in tf_data.items():
                raw_data.append({
                    "cycle_id": cycle_id,
                    "data_type": f"indicators_{tf}",
                    "symbol": symbol,
                    "raw_json": indicators,
                    "source": "binance",
                    "fetched_at": now,
                })

        # News
        if cache.news:
            raw_data.append({
                "cycle_id": cycle_id,
                "data_type": "news",
                "symbol": None,
                "raw_json": cache.news,
                "source": "multi",
                "fetched_at": now,
            })

        # Fear & Greed
        if cache.fear_greed:
            raw_data.append({
                "cycle_id": cycle_id,
                "data_type": "fear_greed",
                "symbol": None,
                "raw_json": cache.fear_greed,
                "source": "alternative.me",
                "fetched_at": now,
            })

        # Positions snapshot
        if cache.positions:
            raw_data.append({
                "cycle_id": cycle_id,
                "data_type": "positions",
                "symbol": None,
                "raw_json": cache.positions,
                "source": "binance",
                "fetched_at": now,
            })

        await self.save_raw_data(raw_data)

        # 3. Save AI decision
        if cache.ai_input_json:
            await self.save_ai_decision({
                "cycle_id": cycle_id,
                "model_used": cache.ai_model,
                "prompt_tokens": cache.ai_prompt_tokens,
                "completion_tokens": cache.ai_completion_tokens,
                "cost_usd": cache.ai_cost_usd,
                "input_json": cache.ai_input_json,
                "output_json": cache.ai_output_json,
                "analysis_text": cache.ai_analysis,
                "actions": cache.ai_actions,
                "latency_ms": cache.ai_latency_ms,
            })

        # 4. Save trades
        if cache.executed_trades:
            trade_rows = []
            for t in cache.executed_trades:
                t["cycle_id"] = cycle_id
                t["executed_at"] = now
                trade_rows.append(t)
            await self.save_trades(trade_rows)

        log.info(f"Saved cycle {cycle_id} to Supabase ({len(raw_data)} raw, {len(cache.executed_trades)} trades)")
        return cycle_id
