import os
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socketio
from dotenv import load_dotenv

from engine.exchange import OKXClient
from engine.scanner import PairsScanner
from engine.reconciliation import ReconciliationService
from engine.models import DBManager, get_db_conn, get_pool

load_dotenv()

app = FastAPI(title="TradingClaw API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Global clients
exchange_client = OKXClient()
scanner_engine = PairsScanner(exchange_client)
reconciler = ReconciliationService(exchange_client)
db_manager = DBManager()

@app.on_event("startup")
async def startup_event():
    print("🚀 TradingClaw Backend Starting...")
    await get_pool() # Initialize DB Pool
    asyncio.create_task(auto_scan_loop())
    asyncio.create_task(auto_reconcile_loop())

async def auto_scan_loop():
    while True:
        try:
            interval = await db_manager.get_config('scan_interval_sec', 60.0)
            print(f"[AutoScan] Triggering scan... (Interval: {interval}s)")
            results = await scanner_engine.scan()
            await sio.emit('pairs_update', [dict(r) for r in results])
            await asyncio.sleep(float(interval))
        except Exception as e:
            print(f"[AutoScan Error] {e}")
            await asyncio.sleep(60)

async def auto_reconcile_loop():
    while True:
        try:
            print("[Reconcile] Running consistency check...")
            await reconciler.run()
            await asyncio.sleep(300) # Every 5 minutes
        except Exception as e:
            print(f"[Reconcile Error] {e}")
            await asyncio.sleep(60)

@app.on_event("shutdown")
async def shutdown_event():
    await exchange_client.close()
    print("🛑 TradingClaw Backend Shutting down...")

# ═══ Endpoints ═══

@app.get("/api/pairs")
async def get_pairs():
    async with (await get_db_conn()) as conn:
        rows = await conn.fetch("""
            SELECT symbol_a, symbol_b, correlation, hurst_exp, half_life,
                   hedge_ratio, zscore, zone, qualified, scanned_at, cointegration_pvalue
            FROM pairs
            ORDER BY CASE WHEN qualified THEN 0 ELSE 1 END, ABS(zscore) DESC
        """)
        return [dict(r) for r in rows]

@app.get("/api/positions")
async def get_positions():
    async with (await get_db_conn()) as conn:
        try:
            rows = await conn.fetch("SELECT * FROM trades WHERE status = 'open'")
            return [dict(r) for r in rows]
        except:
            return []

@app.post("/api/scan/trigger")
async def trigger_scan(background_tasks: BackgroundTasks):
    async def scan_task():
        try:
            results = await scanner_engine.scan()
            await sio.emit('pairs_update', [dict(r) for r in results])
        except Exception as e:
            print(f"[Scan Error] {e}")

    background_tasks.add_task(scan_task)
    return {"status": "triggered"}

@app.get("/api/config")
async def get_all_configs():
    async with (await get_db_conn()) as conn:
        rows = await conn.fetch("SELECT key, value FROM config")
        return {r['key']: r['value'] for r in rows}

@app.put("/api/config/{key}")
async def update_config(key: str, data: dict):
    async with (await get_db_conn()) as conn:
        await conn.execute("INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value=$2", key, str(data.get('value')))
        return {"status": "ok"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0-py"}

# Run with uvicorn
if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=3001)
