-- =============================================
-- JARVIS v5 - Supabase Database Schema
-- Run this in Supabase SQL Editor
-- =============================================

-- 1. TRADING CYCLES TABLE
CREATE TABLE IF NOT EXISTS trading_cycles (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED
    decisions_count INTEGER DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_cycles_status ON trading_cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_started ON trading_cycles(started_at DESC);

-- =============================================
-- 2. RAW DATA TABLES
-- =============================================

CREATE TABLE IF NOT EXISTS raw_binance_data (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_news_data (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_onchain_data (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw data
CREATE INDEX IF NOT EXISTS idx_raw_binance_cycle ON raw_binance_data(cycle_id);
CREATE INDEX IF NOT EXISTS idx_raw_news_cycle ON raw_news_data(cycle_id);
CREATE INDEX IF NOT EXISTS idx_raw_onchain_cycle ON raw_onchain_data(cycle_id);

-- =============================================
-- 3. PROCESSED DATA TABLES
-- =============================================

CREATE TABLE IF NOT EXISTS processed_technical (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_sentiment (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aggregated_data (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_processed_tech_cycle ON processed_technical(cycle_id);
CREATE INDEX IF NOT EXISTS idx_processed_sent_cycle ON processed_sentiment(cycle_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_cycle ON aggregated_data(cycle_id);

-- =============================================
-- 4. AI DECISIONS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS ai_decisions (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    ai_model TEXT NOT NULL,
    confidence_score DECIMAL(5,4),
    market_assessment TEXT,
    decisions_json JSONB,
    raw_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_cycle ON ai_decisions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_model ON ai_decisions(ai_model);

-- =============================================
-- 5. TRADES TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id),
    action TEXT NOT NULL, -- OPEN_LONG, OPEN_SHORT, CLOSE
    symbol TEXT NOT NULL,
    side TEXT, -- LONG, SHORT
    entry_price DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    quantity DECIMAL(20,8),
    leverage INTEGER,
    margin DECIMAL(20,8),
    pnl_usdt DECIMAL(20,8),
    pnl_percent DECIMAL(10,4),
    reasoning TEXT,
    order_id TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_cycle ON trades(cycle_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_action ON trades(action);
CREATE INDEX IF NOT EXISTS idx_trades_executed ON trades(executed_at DESC);

-- =============================================
-- 6. ERROR LOGS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    cycle_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_errors_cycle ON error_logs(cycle_id);
CREATE INDEX IF NOT EXISTS idx_errors_type ON error_logs(error_type);

-- =============================================
-- 7. USEFUL VIEWS
-- =============================================

-- View for recent trades with PnL
CREATE OR REPLACE VIEW recent_trades_view AS
SELECT 
    t.id,
    t.cycle_id,
    t.action,
    t.symbol,
    t.side,
    t.entry_price,
    t.quantity,
    t.leverage,
    t.pnl_usdt,
    t.reasoning,
    t.success,
    t.executed_at
FROM trades t
ORDER BY t.executed_at DESC
LIMIT 100;

-- View for daily performance
CREATE OR REPLACE VIEW daily_performance_view AS
SELECT 
    DATE(executed_at) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl_usdt < 0 THEN 1 ELSE 0 END) as losses,
    SUM(pnl_usdt) as total_pnl,
    AVG(pnl_usdt) as avg_pnl
FROM trades
WHERE success = true
GROUP BY DATE(executed_at)
ORDER BY trade_date DESC;

-- =============================================
-- 8. DATA RETENTION POLICY (Optional)
-- Delete data older than 30 days
-- =============================================

-- CREATE OR REPLACE FUNCTION cleanup_old_data()
-- RETURNS void AS $$
-- BEGIN
--     DELETE FROM raw_binance_data WHERE created_at < NOW() - INTERVAL '30 days';
--     DELETE FROM raw_news_data WHERE created_at < NOW() - INTERVAL '30 days';
--     DELETE FROM raw_onchain_data WHERE created_at < NOW() - INTERVAL '30 days';
--     DELETE FROM processed_technical WHERE created_at < NOW() - INTERVAL '30 days';
--     DELETE FROM processed_sentiment WHERE created_at < NOW() - INTERVAL '30 days';
--     DELETE FROM aggregated_data WHERE created_at < NOW() - INTERVAL '30 days';
-- END;
-- $$ LANGUAGE plpgsql;

-- Schedule: Call this function daily via pg_cron or external scheduler

COMMENT ON TABLE trading_cycles IS 'Each 5-minute trading cycle';
COMMENT ON TABLE trades IS 'All executed trades with PnL tracking';
COMMENT ON TABLE ai_decisions IS 'AI analysis and decisions each cycle';
