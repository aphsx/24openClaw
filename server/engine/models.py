import os
import json
from datetime import datetime
from typing import List, Optional
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
                """
                INSERT INTO ohlcv_daily (symbol, ts, close, volume)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (symbol, ts) DO NOTHING
                """,
                symbol, ts, close, volume
            )

    @staticmethod
    async def get_ohlcv(symbol: str, limit: int = 180) -> List[float]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT close FROM ohlcv_daily 
                WHERE symbol = $1 
                ORDER BY ts DESC LIMIT $2
                """,
                symbol, limit
            )
            return [float(r['close']) for r in reversed(rows)]

    @staticmethod
    async def upsert_pair(data: dict):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO pairs (
                    symbol_a, symbol_b, correlation, hurst_exp, half_life,
                    hedge_ratio, zscore, zone, qualified, validation_json, 
                    scanned_at, cointegration_pvalue
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), $11)
                ON CONFLICT (symbol_a, symbol_b) DO UPDATE SET
                    correlation=$3, hurst_exp=$4, half_life=$5, hedge_ratio=$6,
                    zscore=$7, zone=$8, qualified=$9, validation_json=$10, 
                    scanned_at=NOW(), cointegration_pvalue=$11
                """,
                data['symbol_a'], data['symbol_b'], data['correlation'], 
                data['hurst_exp'], data['half_life'], data['hedge_ratio'],
                data['zscore'], data['zone'], data['qualified'], 
                json.dumps(data['validation_json']), data['cointegration_pvalue']
            )

    @staticmethod
    async def save_scan_result(total: int, qualified: int, signals: int, blocked: int, duration: int, details: dict):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scan_results (total_pairs, qualified, signals, blocked, duration_ms, details)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                total, qualified, signals, blocked, duration, json.dumps(details)
            )

    @staticmethod
    async def get_config(key: str, default=None):
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM config WHERE key = $1", key)
            if row:
                val = row['value']
                try: return float(val)
                except: return val
            return default
