import asyncio
import json
from .models import get_db_conn
from .exchange import OKXClient

class ReconciliationService:
    def __init__(self, exchange: OKXClient):
        self.exchange = exchange

    async def run(self):
        conn = await get_db_conn()
        try:
            # 1. Get Positions from DB (Status is 'open')
            db_rows = await conn.fetch("SELECT symbol_a, symbol_b FROM trades WHERE status = 'open'")
            db_keys = set()
            for r in db_rows:
                db_keys.add(r['symbol_a'])
                db_keys.add(r['symbol_b'])

            # 2. Get Open Positions from Exchange
            # Note: CCXT async fetch_positions
            # We assume a helper in exchange.py or direct call
            exch_positions = await self.exchange.exchange.fetch_positions()
            # OKX symbols are often 'BTC/USDT:USDT'
            exch_keys = set([p['symbol'].split('/')[0] for p in exch_positions if float(p.get('contracts') or 0) != 0])

            # 3. Compute orphans: Exist in Exchange, but not in DB 'open' trades
            orphans = [k for k in exch_keys if k not in db_keys]
            
            # 4. Compute ghosts: Exist in DB 'open' trades, but not in Exchange
            # (This is more complex because one trade has two symbols)
            # For simplicity, we just log symbol-level mismatches
            ghosts = [k for k in db_keys if k not in exch_keys]

            if orphans:
                print(f"🔴 [RECON] ORPHANS FOUND: {orphans} (Manual intervention required)")
            
            if ghosts:
                print(f"🟠 [RECON] GHOSTS FOUND: {ghosts} (DB says open, Exchange says closed)")

            # 5. Log results
            await conn.execute(
                """
                INSERT INTO reconciliation_logs (db_count, exchange_count, orphans, action, details)
                VALUES ($1, $2, $3, 'alert_only', $4)
                """,
                len(db_keys), len(exch_keys), len(orphans),
                json.dumps({'orphans': list(orphans), 'ghosts': list(ghosts)})
            )

            return {'orphans': list(orphans), 'ghosts': list(ghosts)}
        finally:
            await conn.close()
