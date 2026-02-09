# 🗄️ Database Schema Documentation

## Overview

Supabase PostgreSQL database with 9 tables for storing trading data.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     trading_cycles                           │
│  (Master table - one record per 5-minute cycle)             │
├─────────────────────────────────────────────────────────────┤
│  id (PK)                    TEXT                            │
│  started_at                 TIMESTAMPTZ                     │
│  completed_at               TIMESTAMPTZ                     │
│  status                     TEXT (RUNNING/COMPLETED/FAILED) │
│  decisions_count            INTEGER                         │
│  trades_executed            INTEGER                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ raw_binance_data │ │  raw_news_data   │ │ raw_onchain_data │
│   (JSONB)        │ │   (JSONB)        │ │   (JSONB)        │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│              processed_technical / processed_sentiment       │
│                       aggregated_data                        │
│                         (JSONB)                              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      ai_decisions                            │
│  ai_model, confidence_score, market_assessment, decisions   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                         trades                               │
│  action, symbol, side, price, quantity, pnl, reasoning      │
└─────────────────────────────────────────────────────────────┘

         +
┌─────────────────────────────────────────────────────────────┐
│                       error_logs                             │
│  (Independent - for debugging)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Table Details

### 1. trading_cycles (Master)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | cycle_20240210_001234_abc12345 |
| started_at | TIMESTAMPTZ | Cycle start time |
| completed_at | TIMESTAMPTZ | Cycle end time |
| status | TEXT | RUNNING, COMPLETED, FAILED |
| decisions_count | INTEGER | Number of AI decisions |
| trades_executed | INTEGER | Number of trades made |

---

### 2-4. Raw Data Tables

All have same structure:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL (PK) | Auto increment |
| cycle_id | TEXT (FK) | Reference to trading_cycles |
| data | JSONB | Raw JSON from collector |
| created_at | TIMESTAMPTZ | Insert time |

---

### 5-7. Processed Data Tables

Same structure as raw data, but with processed results.

---

### 8. ai_decisions

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL (PK) | Auto increment |
| cycle_id | TEXT (FK) | Reference to trading_cycles |
| ai_model | TEXT | claude, kimi, fallback |
| confidence_score | DECIMAL | 0.0 - 1.0 |
| market_assessment | TEXT | One-line summary |
| decisions_json | JSONB | Array of decisions |
| raw_response | JSONB | Full AI response |

---

### 9. trades

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL (PK) | Auto increment |
| cycle_id | TEXT (FK) | Reference to trading_cycles |
| action | TEXT | OPEN_LONG, OPEN_SHORT, CLOSE |
| symbol | TEXT | BTCUSDT, ETHUSDT, etc. |
| side | TEXT | LONG, SHORT |
| entry_price | DECIMAL | Entry price |
| exit_price | DECIMAL | Exit price (for close) |
| quantity | DECIMAL | Trade size |
| leverage | INTEGER | 1-125x |
| margin | DECIMAL | Margin used |
| pnl_usdt | DECIMAL | Realized PnL |
| pnl_percent | DECIMAL | PnL % |
| reasoning | TEXT | AI reasoning |
| order_id | TEXT | Binance order ID |
| success | BOOLEAN | Trade success |
| error_message | TEXT | Error if failed |
| executed_at | TIMESTAMPTZ | Execution time |

---

### 10. error_logs

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL (PK) | Auto increment |
| cycle_id | TEXT | May be null |
| error_type | TEXT | CYCLE_ERROR, API_ERROR, etc. |
| error_message | TEXT | Error description |
| stack_trace | TEXT | Python traceback |
| created_at | TIMESTAMPTZ | Error time |

---

## Useful Queries

### Daily Performance
```sql
SELECT 
    DATE(executed_at) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    SUM(pnl_usdt) as total_pnl
FROM trades
WHERE success = true
GROUP BY DATE(executed_at)
ORDER BY trade_date DESC;
```

### Win Rate by Symbol
```sql
SELECT 
    symbol,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(pnl_usdt), 4) as avg_pnl
FROM trades
WHERE success = true
GROUP BY symbol
ORDER BY trades DESC;
```

### AI Model Performance
```sql
SELECT 
    d.ai_model,
    COUNT(*) as decisions,
    AVG(d.confidence_score) as avg_confidence,
    SUM(t.pnl_usdt) as total_pnl
FROM ai_decisions d
LEFT JOIN trades t ON d.cycle_id = t.cycle_id
GROUP BY d.ai_model;
```

---

## Data Retention

For Supabase Free Tier (500MB limit):

```sql
-- Delete data older than 30 days
DELETE FROM raw_binance_data WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM raw_news_data WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM raw_onchain_data WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM processed_technical WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM processed_sentiment WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM aggregated_data WHERE created_at < NOW() - INTERVAL '30 days';

-- Keep trades and ai_decisions forever
-- (Much smaller data, valuable for analysis)
```
