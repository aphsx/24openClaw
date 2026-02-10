-- ============================================================
-- ClawBot AI — Supabase Schema
-- Run this in Supabase SQL Editor to create all tables
-- ============================================================

-- Cycles: every 5-minute loop
CREATE TABLE IF NOT EXISTS cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_number BIGINT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INT,
    
    -- Account snapshot
    balance_usdt DECIMAL(18,4),
    available_margin DECIMAL(18,4),
    positions_count INT DEFAULT 0,
    
    -- Actions summary
    actions_taken INT DEFAULT 0,
    orders_opened INT DEFAULT 0,
    orders_closed INT DEFAULT 0,
    sl_tp_triggered INT DEFAULT 0,
    
    -- AI info
    ai_model TEXT,
    ai_latency_ms INT,
    ai_cost_usd DECIMAL(10,6),
    
    -- News
    news_count INT DEFAULT 0,
    news_is_cached BOOLEAN DEFAULT false,
    fear_greed_value INT,
    
    status TEXT DEFAULT 'running',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cycles_started ON cycles(started_at DESC);
CREATE INDEX idx_cycles_status ON cycles(status);

-- Raw data per cycle (indicators, news, market, positions)
CREATE TABLE IF NOT EXISTS cycle_raw_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID REFERENCES cycles(id) ON DELETE CASCADE,
    data_type TEXT NOT NULL,  -- 'indicators_5m', 'indicators_15m', 'indicators_1h', 'news', 'market', 'positions', 'fear_greed'
    symbol TEXT,
    raw_json JSONB NOT NULL,
    processed_json JSONB,
    source TEXT NOT NULL,
    source_timestamp TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_raw_data_cycle ON cycle_raw_data(cycle_id);
CREATE INDEX idx_raw_data_type ON cycle_raw_data(data_type);

-- AI decisions: prompt, response, and parsed actions
CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID REFERENCES cycles(id) ON DELETE CASCADE,
    model_used TEXT NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    cost_usd DECIMAL(10,6),
    input_json JSONB,
    output_json JSONB,
    analysis_text TEXT,
    actions JSONB,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ai_decisions_cycle ON ai_decisions(cycle_id);

-- Trades: every order with Binance data
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID REFERENCES cycles(id) ON DELETE CASCADE,
    
    -- Binance data
    binance_order_id TEXT,
    binance_client_order_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,         -- 'LONG' / 'SHORT'
    position_side TEXT,
    order_type TEXT,            -- 'MARKET' / 'LIMIT'
    
    -- Price
    entry_price DECIMAL(18,8),
    exit_price DECIMAL(18,8),
    quantity DECIMAL(18,8),
    margin_usdt DECIMAL(18,4),
    leverage INT DEFAULT 20,
    
    -- PnL from Binance
    realized_pnl DECIMAL(18,4),
    realized_pnl_pct DECIMAL(8,4),
    commission DECIMAL(18,8),
    commission_asset TEXT,
    
    -- AI context
    ai_confidence INT,
    ai_reason TEXT,
    regime TEXT,
    counter_trend BOOLEAN DEFAULT false,
    
    -- Close info
    closed_by TEXT,             -- 'AI' / 'STOP_LOSS' / 'TAKE_PROFIT'
    hold_duration_min INT,
    
    -- Safety SL/TP
    sl_price DECIMAL(18,8),
    tp_price DECIMAL(18,8),
    
    action TEXT NOT NULL,       -- 'OPEN' / 'CLOSE'
    executed_at TIMESTAMPTZ NOT NULL,
    balance_after DECIMAL(18,4),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trades_cycle ON trades(cycle_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_executed ON trades(executed_at DESC);

-- Daily summary
CREATE TABLE IF NOT EXISTS daily_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    total_cycles INT,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DECIMAL(5,2),
    total_pnl DECIMAL(18,4),
    total_commission DECIMAL(18,4),
    net_pnl DECIMAL(18,4),
    best_trade DECIMAL(18,4),
    worst_trade DECIMAL(18,4),
    avg_hold_min INT,
    avg_confidence INT,
    ai_cost_usd DECIMAL(10,4),
    balance_start DECIMAL(18,4),
    balance_end DECIMAL(18,4),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_daily_date ON daily_summary(date DESC);
