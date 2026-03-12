import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socketio
from dotenv import load_dotenv

from engine.exchange import BinanceClient
from engine.scanner import PairsScanner
from engine.executor import TradeExecutor
from engine.monitor import PositionMonitor
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

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Global singletons
exchange_client = BinanceClient()
scanner_engine  = PairsScanner(exchange_client)
executor        = TradeExecutor(exchange_client)
monitor         = PositionMonitor(exchange_client, executor)
reconciler      = ReconciliationService(exchange_client)
db_manager      = DBManager()


@app.on_event("startup")
async def startup_event():
    print("TradingClaw Backend Starting (Binance USDT-M)...")
    await get_pool()
    asyncio.create_task(auto_scan_loop())
    asyncio.create_task(auto_monitor_loop())
    asyncio.create_task(auto_reconcile_loop())


async def auto_scan_loop():
    while True:
        try:
            interval = await db_manager.get_config('scan_interval_sec', 60.0)
            results  = await scanner_engine.scan()
            await sio.emit('pairs_update', [dict(r) for r in results])
            await asyncio.sleep(float(interval))
        except Exception as e:
            print(f"[AutoScan Error] {e}")
            await asyncio.sleep(60)


async def auto_monitor_loop():
    while True:
        try:
            interval = await db_manager.get_config('monitor_interval_sec', 30.0)
            await monitor.run_once()
            trades = await db_manager.get_open_trades()
            await sio.emit('positions_update', trades)
            await asyncio.sleep(float(interval))
        except Exception as e:
            print(f"[Monitor Error] {e}")
            await asyncio.sleep(30)


async def auto_reconcile_loop():
    while True:
        try:
            await reconciler.run()
            await asyncio.sleep(300)
        except Exception as e:
            print(f"[Reconcile Error] {e}")
            await asyncio.sleep(60)


@app.on_event("shutdown")
async def shutdown_event():
    await exchange_client.close()
    print("TradingClaw Backend Shutting down...")


# ═══ Market Data ═══

@app.get("/api/pairs")
async def get_pairs():
    async with (await get_db_conn()) as conn:
        rows = await conn.fetch("""
            SELECT symbol_a, symbol_b, correlation, hurst_exp, half_life,
                   hedge_ratio, zscore, zone, qualified, scanned_at,
                   cointegration_pvalue, validation_json
            FROM pairs
            ORDER BY CASE WHEN qualified THEN 0 ELSE 1 END, ABS(zscore) DESC
        """)
        return [dict(r) for r in rows]


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


# ═══ Portfolio & Account ═══

@app.get("/api/portfolio")
async def get_portfolio():
    balance = await exchange_client.get_balance()
    stats   = await db_manager.get_trade_stats()

    open_trades = await db_manager.get_open_trades()
    unrealized_pnl = 0.0
    enriched_positions = []
    for t in open_trades:
        pnl = await monitor._estimate_pnl(t)
        unrealized_pnl += pnl
        enriched_positions.append({
            'group_id':       str(t['group_id']),
            'symbol_a':       t['symbol_a'],
            'symbol_b':       t['symbol_b'],
            'leg_a_side':     t['leg_a_side'],
            'leg_b_side':     t['leg_b_side'],
            'size_a_usd':     float(t.get('leg_a_size_usd') or 0),
            'size_b_usd':     float(t.get('leg_b_size_usd') or 0),
            'entry_zscore':   float(t.get('entry_zscore') or 0),
            'current_zscore': float(t.get('current_zscore') or t.get('entry_zscore') or 0),
            'entry_corr':     float(t.get('entry_corr') or 0),
            'entry_zone':     t.get('entry_zone', ''),
            'unrealized_pnl': round(pnl, 4),
            'opened_at':      t['opened_at'].isoformat() if t.get('opened_at') else None,
            'status':         t['status'],
        })

    return {
        'balance':        balance,
        'unrealized_pnl': round(unrealized_pnl, 4),
        'realized_pnl':   float(stats.get('realized_pnl') or 0),
        'total_fees':     float(stats.get('total_fees') or 0),
        'total_trades':   int(stats.get('total_trades') or 0),
        'wins':           int(stats.get('wins') or 0),
        'losses':         int(stats.get('losses') or 0),
        'win_rate':       float(stats.get('win_rate') or 0),
        'avg_win':        float(stats.get('avg_win') or 0),
        'avg_loss':       float(stats.get('avg_loss') or 0),
        'best_trade':     float(stats.get('best_trade') or 0),
        'worst_trade':    float(stats.get('worst_trade') or 0),
        'open_pairs':     int(stats.get('open_pairs') or 0),
        'open_positions': enriched_positions,
    }


@app.get("/api/positions")
async def get_positions():
    open_trades = await db_manager.get_open_trades()
    result = []
    for t in open_trades:
        pnl = await monitor._estimate_pnl(t)
        result.append({
            'group_id':       str(t['group_id']),
            'symbol_a':       t['symbol_a'],
            'symbol_b':       t['symbol_b'],
            'leg_a_side':     t['leg_a_side'],
            'leg_b_side':     t['leg_b_side'],
            'entry_zscore':   float(t.get('entry_zscore') or 0),
            'current_zscore': float(t.get('current_zscore') or t.get('entry_zscore') or 0),
            'entry_corr':     float(t.get('entry_corr') or 0),
            'size_a_usd':     float(t.get('leg_a_size_usd') or 0),
            'size_b_usd':     float(t.get('leg_b_size_usd') or 0),
            'unrealized_pnl': round(pnl, 4),
            'opened_at':      t['opened_at'].isoformat() if t.get('opened_at') else None,
            'status':         t['status'],
        })
    return result


# ═══ Trade Execution ═══

@app.post("/api/trade/open")
async def open_trade(payload: dict):
    result = await executor.open_pair(payload)
    if result.get('success'):
        trades = await db_manager.get_open_trades()
        await sio.emit('positions_update', trades)
    return result


@app.post("/api/trade/close/{group_id}")
async def close_trade(group_id: str, payload: dict = {}):
    reason = payload.get('reason', 'manual') if payload else 'manual'
    result = await executor.close_pair(group_id, exit_reason=reason)
    if result.get('success'):
        trades = await db_manager.get_open_trades()
        await sio.emit('positions_update', trades)
    return result


# ═══ Config ═══

@app.get("/api/config")
async def get_all_configs():
    async with (await get_db_conn()) as conn:
        rows = await conn.fetch("SELECT key, value FROM config")
        return {r['key']: r['value'] for r in rows}


@app.put("/api/config/{key}")
async def update_config(key: str, data: dict):
    async with (await get_db_conn()) as conn:
        await conn.execute(
            "INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value=$2",
            key, str(data.get('value'))
        )
        return {"status": "ok"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0-binance",
        "dry_run": exchange_client.dry_run,
    }


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=3001)
