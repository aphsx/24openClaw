import asyncio
from .models import DBManager, get_pool
from .exchange import BinanceClient


class ReconciliationService:
    def __init__(self, exchange: BinanceClient):
        self.exchange = exchange
        self.db = DBManager()

    async def run(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            # 1. DB open positions
            db_rows = await conn.fetch("SELECT symbol_a, symbol_b FROM trades WHERE status='open'")
            db_keys = set()
            for r in db_rows:
                db_keys.add(r['symbol_a'])
                db_keys.add(r['symbol_b'])

            # 2. Exchange open positions
            exch_positions = await self.exchange.get_all_positions()
            exch_keys = set(
                p['symbol'].split('/')[0]
                for p in exch_positions
                if abs(float(p.get('contracts') or 0)) > 0
            )

            # 3. Orphans: on exchange but not in DB
            orphans = [k for k in exch_keys if k not in db_keys]

            # 4. Ghosts: in DB but not on exchange
            ghosts = [k for k in db_keys if k not in exch_keys]

            if orphans:
                print(f"[RECON] ORPHAN POSITIONS (manual intervention required): {orphans}")

            if ghosts:
                print(f"[RECON] GHOST POSITIONS (DB says open, exchange closed): {ghosts}")
                # Auto-close ghost trades in DB
                ghost_rows = await conn.fetch(
                    "SELECT group_id, symbol_a, symbol_b FROM trades WHERE status='open'"
                )
                for row in ghost_rows:
                    if row['symbol_a'] in ghosts or row['symbol_b'] in ghosts:
                        await conn.execute(
                            "UPDATE trades SET status='closed', exit_reason='ghost_reconciled', closed_at=NOW() WHERE group_id=$1",
                            row['group_id'],
                        )
                        print(f"[RECON] Ghost reconciled: {row['symbol_a']}/{row['symbol_b']}")

            await self.db.log_reconciliation(
                len(db_keys), len(exch_keys), len(orphans),
                {'orphans': list(orphans), 'ghosts': list(ghosts)},
            )

            return {'orphans': orphans, 'ghosts': ghosts}
