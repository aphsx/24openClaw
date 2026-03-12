import os
import json
from typing import List, Optional, Dict, Any
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def get_db_conn():
    pool = await get_pool()
    return pool.acquire()


class DBManager:

    @staticmethod
    async def save_ohlcv(symbol: str, ts: str, close: float, volume: float):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ohlcv_daily (symbol, ts, close, volume) VALUES ($1,$2,$3,$4) ON CONFLICT (symbol, ts) DO NOTHING",
                symbol, ts, close, volume,
            )

    @staticmethod
    async def get_ohlcv(symbol: str, limit: int = 180) -> List[float]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT close FROM ohlcv_daily WHERE symbol=$1 ORDER BY ts DESC LIMIT $2",
                symbol, limit,
            )
            return [float(r['close']) for r in reversed(rows)]

    @staticmethod
    async def upsert_pair(data: dict):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO pairs (symbol_a, symbol_b, correlation, hurst_exp, half_life,
                    hedge_ratio, zscore, zone, qualified, validation_json, scanned_at, cointegration_pvalue)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW(),$11)
                ON CONFLICT (symbol_a, symbol_b) DO UPDATE SET
                    correlation=$3, hurst_exp=$4, half_life=$5, hedge_ratio=$6,
                    zscore=$7, zone=$8, qualified=$9, validation_json=$10,
                    scanned_at=NOW(), cointegration_pvalue=$11
                """,
                data['symbol_a'], data['symbol_b'],
                data['correlation'], data['hurst_exp'], data['half_life'],
                data['hedge_ratio'], data['zscore'], data['zone'],
                data['qualified'], json.dumps(data['validation_json']),
                data['cointegration_pvalue'],
            )

    @staticmethod
    async def get_pair_stats(symbol_a: str, symbol_b: str) -> Optional[Dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM pairs WHERE symbol_a=$1 AND symbol_b=$2",
                symbol_a, symbol_b,
            )
            return dict(row) if row else None

    @staticmethod
    async def save_scan_result(total, qualified, signals, blocked, duration, details):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO scan_results (total_pairs, qualified, signals, blocked, duration_ms, details) VALUES ($1,$2,$3,$4,$5,$6)",
                total, qualified, signals, blocked, duration, json.dumps(details),
            )

    @staticmethod
    async def get_config(key: str, default=None):
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM config WHERE key=$1", key)
            if row:
                try:
                    return float(row['value'])
                except Exception:
                    return row['value']
            return default

    @staticmethod
    async def get_all_config() -> Dict[str, Any]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM config")
            result = {}
            for r in rows:
                try:
                    result[r['key']] = float(r['value'])
                except Exception:
                    result[r['key']] = r['value']
            return result

    @staticmethod
    async def open_trade(data: dict) -> str:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO trades (
                    group_id, symbol_a, symbol_b,
                    leg_a_side, leg_a_size_usd, leg_a_order_id, leg_a_entry_price,
                    leg_b_side, leg_b_size_usd, leg_b_order_id, leg_b_entry_price,
                    entry_zscore, entry_corr, entry_beta, entry_half_life, entry_zone,
                    validation_json, grace_until, status, opened_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,'open',NOW())
                """,
                data['group_id'], data['symbol_a'], data['symbol_b'],
                data['leg_a_side'], data['leg_a_size_usd'], data['leg_a_order_id'], data.get('leg_a_entry_price'),
                data['leg_b_side'], data['leg_b_size_usd'], data['leg_b_order_id'], data.get('leg_b_entry_price'),
                data['entry_zscore'], data['entry_corr'], data['entry_beta'],
                data.get('entry_half_life'), data['entry_zone'],
                json.dumps(data.get('validation_json', {})),
                data.get('grace_until'),
            )
        return data['group_id']

    @staticmethod
    async def close_trade(group_id: str, exit_zscore: float, exit_reason: str, pnl_usd: float):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE trades SET status='closed', exit_zscore=$2, exit_reason=$3, pnl_usd=$4, closed_at=NOW() WHERE group_id=$1",
                group_id, exit_zscore, exit_reason, pnl_usd,
            )

    @staticmethod
    async def update_trade_zscore(group_id: str, current_zscore: float):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE trades SET current_zscore=$2, last_monitored_at=NOW() WHERE group_id=$1",
                group_id, current_zscore,
            )

    @staticmethod
    async def get_open_trades() -> List[Dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM trades WHERE status='open' ORDER BY opened_at ASC")
            return [dict(r) for r in rows]

    @staticmethod
    async def get_trade_by_group(group_id: str) -> Optional[Dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM trades WHERE group_id=$1", group_id)
            return dict(row) if row else None

    @staticmethod
    async def is_pair_open(symbol_a: str, symbol_b: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM trades WHERE symbol_a=$1 AND symbol_b=$2 AND status='open'",
                symbol_a, symbol_b,
            )
            return row is not None

    @staticmethod
    async def is_in_cooldown(symbol_a: str, symbol_b: str, cooldown_sec: float) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id FROM trades
                WHERE symbol_a=$1 AND symbol_b=$2 AND status='closed'
                  AND closed_at > NOW() - ($3 || ' seconds')::INTERVAL
                ORDER BY closed_at DESC LIMIT 1
                """,
                symbol_a, symbol_b, str(int(cooldown_sec)),
            )
            return row is not None

    @staticmethod
    async def get_coin_open_count(symbol: str) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM trades WHERE status='open' AND (symbol_a=$1 OR symbol_b=$1)",
                symbol,
            )
            return int(val or 0)

    @staticmethod
    async def get_trade_stats() -> Dict[str, Any]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_trades,
                    COUNT(*) FILTER (WHERE pnl_usd > 0) AS wins,
                    COUNT(*) FILTER (WHERE pnl_usd <= 0) AS losses,
                    COALESCE(SUM(pnl_usd), 0) AS realized_pnl,
                    COALESCE(SUM(fees_paid), 0) AS total_fees,
                    COALESCE(AVG(pnl_usd) FILTER (WHERE pnl_usd > 0), 0) AS avg_win,
                    COALESCE(AVG(pnl_usd) FILTER (WHERE pnl_usd <= 0), 0) AS avg_loss,
                    COALESCE(MAX(pnl_usd), 0) AS best_trade,
                    COALESCE(MIN(pnl_usd), 0) AS worst_trade
                FROM trades WHERE status='closed'
                """
            )
            d = dict(row) if row else {}
            total = int(d.get('total_trades', 0))
            wins  = int(d.get('wins', 0))
            d['win_rate'] = round((wins / total * 100) if total > 0 else 0, 1)
            d['open_pairs'] = await conn.fetchval("SELECT COUNT(*) FROM trades WHERE status='open'")
            return d

    @staticmethod
    async def log_reconciliation(db_count: int, exchange_count: int, orphans: int, details: dict):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reconciliation_logs (db_count, exchange_count, orphans, action, details) VALUES ($1,$2,$3,'alert_only',$4)",
                db_count, exchange_count, orphans, json.dumps(details),
            )
