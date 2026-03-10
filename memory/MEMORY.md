# TradingClaw Memory

## Project Overview
Full-stack Pairs Trading Scanner (OKX Perp Futures, no real execution yet)
- Backend: Python FastAPI + asyncpg + CCXT (port 3001)
- Frontend: React + Vite + TypeScript + React Query + Socket.IO (port 5173)
- DB: PostgreSQL 16 (port 5433), Redis 7 (unused)
- Docker Compose orchestrates all services

## Key Files
- `server/app.py` - FastAPI entry, Socket.IO, auto-scan loop (60s)
- `server/engine/scanner.py` - Core scan: top-25 coins → OHLCV → stats → DB
- `server/engine/stats.py` - corr, hedge_ratio, half_life, hurst, zscore, p_value
- `server/engine/models.py` - asyncpg CRUD
- `server/engine/exchange.py` - CCXT OKX wrapper (dry-run if no API key)
- `server/engine/executor.py` - Trade executor (NOT wired up, stub)
- `db/init.sql` - Schema + config defaults
- `db/migrate_v2.sql` - Migration: adds cointegration_pvalue column + pvalue_max config
- `frontend/src/features/scanner/components/ScannerTable.tsx` - Main scanner UI

## Bugs Fixed (Session 1)
1. `init.sql` missing `cointegration_pvalue` column in `pairs` table → crashes every scan
2. `init.sql` missing `pvalue_max` config entry
3. `scanner.py` line 103: qualified count used `corr >= corr_min` instead of `p['qualified']`
4. `app.py` GET /api/pairs: missing `hedge_ratio` in SELECT

## Known Remaining Issues (Scanner)
- Sparklines in ScannerTable use random mock data (cosmetic, not functional)
- Config tab in frontend shows hardcoded values (should call /api/config)
- History/Logs tabs are placeholder UI
- First 3 validation checks in ScannerTable are hardcoded `pass: true`

## Architecture Notes
- Scanner: top 25 coins by volume ≥ $20M → ~300 pairs combinations → filter by stats
- Stats thresholds: corr ≥ 0.8, half_life 5-30d, hurst < 0.5, pvalue ≤ 0.05, zscore ≥ 2.0
- Zone: safe(2.0-3.5), caution(1.8-2.0), neutral(<1.8), danger(≥3.5)
- Executor.py exists but NOT integrated. No trade endpoints. Execute buttons have no onClick.
- Redis declared in compose but unused in code

## If DB Already Exists
Run migration: `psql -U trader -d pairs_trading -f db/migrate_v2.sql`
Or reset volume: `docker compose down -v && docker compose up -d`
