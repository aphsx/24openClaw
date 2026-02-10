-- =============================================
-- ClawBot AI — Complete Database Schema
-- Supabase PostgreSQL
-- Run this in Supabase SQL Editor
-- =============================================

-- =============================================
-- 1. TRADING CYCLES (รอบการเทรดทุก 2 นาที)
-- =============================================
CREATE TABLE IF NOT EXISTS trading_cycles (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'RUNNING',           -- RUNNING, COMPLETED, FAILED
    
    -- Timing
    collection_ms INTEGER,                    -- เวลาเก็บข้อมูล (ms)
    processing_ms INTEGER,                    -- เวลาประมวลผล (ms)
    ai_decision_ms INTEGER,                   -- เวลา AI คิด (ms)
    total_cycle_ms INTEGER,                   -- เวลารวมทั้ง cycle
    
    -- Snapshot ตอนเริ่ม cycle
    balance_usdt NUMERIC(20, 8),              -- ยอดเงินรวม
    available_margin NUMERIC(20, 8),          -- margin ว่าง
    open_positions_count INTEGER DEFAULT 0,   -- จำนวน positions ที่เปิดอยู่
    
    -- Results
    decisions_count INTEGER DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    ai_model TEXT,                             -- model ที่ใช้ (groq/claude/fallback)
    ai_confidence NUMERIC(5, 4),              -- ความมั่นใจ AI
    market_outlook TEXT,                       -- BULLISH/BEARISH/NEUTRAL
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cycles_status ON trading_cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_started ON trading_cycles(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cycles_model ON trading_cycles(ai_model);


-- =============================================
-- 2. MARKET SNAPSHOTS (ข้อมูลตลาดต่อเหรียญต่อ cycle)
--    ใช้แท่งเทียน 5 นาที เป็นหลัก
-- =============================================
CREATE TABLE IF NOT EXISTS market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    
    -- ราคา
    current_price NUMERIC(20, 10) NOT NULL,
    
    -- EMA (จากแท่ง 5 นาที)
    ema9 NUMERIC(20, 10),                     -- EMA 9 (scalping fast)
    ema21 NUMERIC(20, 10),                    -- EMA 21 (scalping medium)
    ema20 NUMERIC(20, 10),                    -- EMA 20 (standard)
    ema50 NUMERIC(20, 10),                    -- EMA 50
    ema55 NUMERIC(20, 10),                    -- EMA 55
    ema200 NUMERIC(20, 10),                   -- EMA 200 (long-term)
    
    -- RSI
    rsi NUMERIC(5, 2),                        -- RSI-14
    rsi_7 NUMERIC(5, 2),                      -- RSI-7 (fast scalping)
    rsi_ema NUMERIC(5, 2),                    -- RSI smoothed ด้วย EMA-9
    
    -- MACD
    macd NUMERIC(12, 6),                      -- MACD line
    macd_signal NUMERIC(12, 6),               -- MACD signal line
    macd_histogram NUMERIC(12, 6),             -- MACD histogram
    
    -- ATR (Volatility)
    atr NUMERIC(12, 6),                       -- ATR-14
    atr_percent NUMERIC(6, 4),                -- ATR เป็น % ของราคา
    volatility VARCHAR(10),                   -- HIGH / MEDIUM / LOW
    
    -- Bollinger Bands
    bb_upper NUMERIC(20, 10),
    bb_middle NUMERIC(20, 10),
    bb_lower NUMERIC(20, 10),
    
    -- Price Range
    recent_high NUMERIC(20, 10),              -- High ใน 20 แท่ง (~100 นาที)
    recent_low NUMERIC(20, 10),               -- Low ใน 20 แท่ง (~100 นาที)
    day_high NUMERIC(20, 10),                 -- High 24 ชม. (จาก Binance)
    day_low NUMERIC(20, 10),                  -- Low 24 ชม. (จาก Binance)
    
    -- Volume
    volume_24h NUMERIC(30, 8),                -- Volume 24 ชม.
    quote_volume_24h NUMERIC(30, 8),          -- Quote volume (USDT)
    volume_ratio NUMERIC(6, 2),               -- Current / Avg volume
    price_change_24h NUMERIC(8, 4),           -- % เปลี่ยนแปลง 24 ชม.
    
    -- Order Book
    best_bid NUMERIC(20, 10),
    best_ask NUMERIC(20, 10),
    spread NUMERIC(20, 10),
    
    -- Futures Data  
    funding_rate NUMERIC(10, 8),              -- ค่าธรรมเนียม funding
    long_ratio NUMERIC(6, 4),                 -- สัดส่วน long
    short_ratio NUMERIC(6, 4),                -- สัดส่วน short
    long_short_ratio NUMERIC(6, 4),           -- อัตราส่วน L/S
    
    -- Signals & Scoring
    trend VARCHAR(20),                        -- STRONG_BULLISH, BULLISH, NEUTRAL, etc.
    momentum VARCHAR(20),                     -- BULLISH, BEARISH, OVERBOUGHT, etc.
    combined_score NUMERIC(5, 2),             -- คะแนนรวม 0-100
    combined_signal VARCHAR(20),              -- สัญญาณรวม
    signal_agreement VARCHAR(20),             -- 2/3 ALIGNED, MIXED, etc.
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_cycle ON market_snapshots(cycle_id);
CREATE INDEX IF NOT EXISTS idx_market_symbol ON market_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_market_time ON market_snapshots(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_market_cycle_symbol ON market_snapshots(cycle_id, symbol);


-- =============================================
-- 3. ORDERS (คำสั่งซื้อขาย — raw จาก Binance)
-- =============================================
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE SET NULL,
    trade_id BIGINT,                          -- link ไป trades table
    
    -- Binance Order Data
    order_id BIGINT,                          -- Binance orderId
    client_order_id TEXT,                     -- clientOrderId
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                        -- BUY / SELL
    order_type TEXT DEFAULT 'MARKET',         -- MARKET / LIMIT
    position_side TEXT DEFAULT 'BOTH',        -- BOTH / LONG / SHORT
    
    -- Fill Data
    quantity NUMERIC(20, 8),                  -- จำนวนที่สั่ง
    executed_qty NUMERIC(20, 8),              -- จำนวนที่เติม (filled)
    avg_price NUMERIC(20, 10),                -- ราคาเฉลี่ยที่ได้
    cum_quote NUMERIC(20, 8),                 -- Quote volume (USDT value)
    
    -- Fees
    commission NUMERIC(20, 10),               -- ค่าธรรมเนียม
    commission_asset TEXT DEFAULT 'USDT',     -- สกุลค่าธรรมเนียม (USDT/BNB)
    
    -- Status
    status TEXT DEFAULT 'FILLED',             -- NEW, FILLED, CANCELED, EXPIRED
    reduce_only BOOLEAN DEFAULT FALSE,        -- ปิด position เท่านั้น
    
    -- Timing
    order_time TIMESTAMPTZ,                   -- เวลาสั่ง order
    update_time TIMESTAMPTZ,                  -- เวลา fill
    
    -- Raw Response
    raw_response JSONB,                       -- raw JSON จาก Binance
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_cycle ON orders(cycle_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_binance ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_time ON orders(created_at DESC);


-- =============================================
-- 4. TRADES (เทรดที่จับคู่แล้ว open+close)
-- =============================================
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    cycle_id_open TEXT REFERENCES trading_cycles(id) ON DELETE SET NULL,
    cycle_id_close TEXT REFERENCES trading_cycles(id) ON DELETE SET NULL,
    
    -- Position Info
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                        -- LONG / SHORT
    leverage INTEGER DEFAULT 20,
    margin_usdt NUMERIC(20, 8),               -- margin ที่ใช้
    
    -- Entry
    entry_price NUMERIC(20, 10),              -- ราคาเข้า
    entry_qty NUMERIC(20, 8),                 -- จำนวนเข้า
    entry_value NUMERIC(20, 8),               -- มูลค่า entry (qty * price)
    order_id_open BIGINT,                     -- Binance orderId เปิด
    opened_at TIMESTAMPTZ,                    -- เวลาเปิด
    
    -- Exit (null ถ้ายังเปิดอยู่)
    exit_price NUMERIC(20, 10),               -- ราคาออก
    exit_qty NUMERIC(20, 8),                  -- จำนวนออก
    exit_value NUMERIC(20, 8),                -- มูลค่า exit
    order_id_close BIGINT,                    -- Binance orderId ปิด
    closed_at TIMESTAMPTZ,                    -- เวลาปิด
    
    -- PnL
    gross_pnl NUMERIC(20, 8),                 -- กำไร/ขาดทุน ก่อนหักค่าธรรมเนียม
    
    -- Fees (รวมทั้ง open + close)
    commission_open NUMERIC(20, 10),          -- ค่าธรรมเนียมตอนเปิด
    commission_close NUMERIC(20, 10),         -- ค่าธรรมเนียมตอนปิด
    total_commission NUMERIC(20, 10),         -- ค่าธรรมเนียมรวม
    commission_asset TEXT DEFAULT 'USDT',
    
    -- Funding Cost (ถ้าถือข้ามรอบ 8 ชม.)
    funding_fee NUMERIC(20, 10) DEFAULT 0,    -- ค่า funding ที่จ่าย/ได้รับ
    
    -- Net PnL
    net_pnl NUMERIC(20, 8),                   -- กำไรสุทธิ (gross - commission - funding)
    net_pnl_percent NUMERIC(10, 4),           -- กำไรสุทธิ %
    roi_on_margin NUMERIC(10, 4),             -- ROI บน margin (%): net_pnl / margin * 100
    
    -- Duration
    duration_seconds INTEGER,                 -- ถือนานกี่วินาที
    
    -- AI Decision
    reasoning_open TEXT,                      -- เหตุผลที่เปิด
    reasoning_close TEXT,                     -- เหตุผลที่ปิด
    ai_conviction_open NUMERIC(5, 4),         -- ความมั่นใจ AI ตอนเปิด
    ai_conviction_close NUMERIC(5, 4),        -- ความมั่นใจ AI ตอนปิด
    
    -- Market Context ตอนเปิด
    entry_rsi NUMERIC(5, 2),
    entry_ema9 NUMERIC(20, 10),
    entry_trend VARCHAR(20),
    entry_funding_rate NUMERIC(10, 8),
    
    -- Status
    status TEXT DEFAULT 'OPEN',               -- OPEN / CLOSED / LIQUIDATED
    is_winner BOOLEAN,                        -- true = net_pnl > 0
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_closed ON trades(closed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_winner ON trades(is_winner);


-- =============================================
-- 5. POSITIONS HISTORY (snapshot positions ทุก cycle)
-- =============================================
CREATE TABLE IF NOT EXISTS positions_history (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                        -- LONG / SHORT
    position_amt NUMERIC(20, 8),              -- จำนวน position
    entry_price NUMERIC(20, 10),
    mark_price NUMERIC(20, 10),               -- ราคาตลาดปัจจุบัน
    liquidation_price NUMERIC(20, 10),        -- ราคา liquidation
    leverage INTEGER,
    margin_type TEXT DEFAULT 'CROSS',         -- CROSS / ISOLATED
    initial_margin NUMERIC(20, 8),
    maintenance_margin NUMERIC(20, 8),
    
    -- PnL
    unrealized_pnl NUMERIC(20, 8),            -- กำไร/ขาดทุนที่ยังไม่ปิด
    unrealized_pnl_percent NUMERIC(10, 4),
    
    -- Accumulated
    notional_value NUMERIC(20, 8),            -- มูลค่ารวม position
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pos_hist_cycle ON positions_history(cycle_id);
CREATE INDEX IF NOT EXISTS idx_pos_hist_symbol ON positions_history(symbol);
CREATE INDEX IF NOT EXISTS idx_pos_hist_time ON positions_history(created_at DESC);


-- =============================================
-- 6. ACCOUNT SNAPSHOTS (equity curve)
-- =============================================
CREATE TABLE IF NOT EXISTS account_snapshots (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    
    -- Balances
    total_balance NUMERIC(20, 8),             -- ยอดเงินรวม
    available_balance NUMERIC(20, 8),         -- margin ว่าง
    total_margin_used NUMERIC(20, 8),         -- margin ที่ใช้
    
    -- Positions
    total_unrealized_pnl NUMERIC(20, 8),      -- unrealized PnL รวม
    total_position_value NUMERIC(20, 8),      -- มูลค่า position รวม
    open_positions_count INTEGER DEFAULT 0,
    
    -- Equity
    equity NUMERIC(20, 8),                    -- balance + unrealized PnL
    margin_ratio NUMERIC(10, 4),              -- margin used / equity (%)
    
    -- Daily PnL Tracking
    realized_pnl_today NUMERIC(20, 8) DEFAULT 0,   -- กำไรที่ปิดแล้ววันนี้
    total_commission_today NUMERIC(20, 8) DEFAULT 0, -- ค่าธรรมเนียมวันนี้
    trades_today INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_account_cycle ON account_snapshots(cycle_id);
CREATE INDEX IF NOT EXISTS idx_account_time ON account_snapshots(created_at DESC);


-- =============================================
-- 7. AI DECISIONS
-- =============================================
CREATE TABLE IF NOT EXISTS ai_decisions (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    
    ai_model TEXT NOT NULL,                   -- groq / claude / kimi / fallback
    confidence_score NUMERIC(5, 4),
    market_assessment TEXT,
    
    -- คำสั่ง AI
    decisions_json JSONB,                     -- [{action, symbol, reasoning, ...}]
    
    -- Key Observations
    key_observations JSONB,                   -- ["obs1", "obs2"]
    risk_warnings JSONB,                      -- ["warning1"]
    
    -- Performance Tracking
    prompt_tokens INTEGER,                    -- tokens ใช้
    completion_tokens INTEGER,
    latency_ms INTEGER,                       -- เวลาตอบ (ms)
    
    raw_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_cycle ON ai_decisions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_ai_model ON ai_decisions(ai_model);


-- =============================================
-- 8. NEWS & SENTIMENT
-- =============================================
CREATE TABLE IF NOT EXISTS news_articles (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    
    title TEXT NOT NULL,
    source TEXT,                               -- CoinDesk, Cointelegraph, etc.
    url TEXT,
    published_at TIMESTAMPTZ,
    
    -- Sentiment (จาก AI)
    sentiment_score NUMERIC(5, 2),            -- 0-100
    sentiment_label VARCHAR(20),              -- BULLISH / BEARISH / NEUTRAL
    
    collection_method VARCHAR(10),            -- rss / scrape
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_cycle ON news_articles(cycle_id);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_time ON news_articles(published_at DESC);


-- =============================================
-- 9. ERROR LOGS
-- =============================================
CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT,
    error_type TEXT NOT NULL,                  -- COLLECTION_ERROR, AI_ERROR, TRADE_ERROR
    error_message TEXT NOT NULL,
    component TEXT,                             -- binance_collector, ai_brain, etc.
    stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_errors_cycle ON error_logs(cycle_id);
CREATE INDEX IF NOT EXISTS idx_errors_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_time ON error_logs(created_at DESC);


-- =============================================
-- 10. RAW DATA STORAGE (JSONB — auto-cleanup หลัง 30 วัน)
-- =============================================
CREATE TABLE IF NOT EXISTS raw_binance_data (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_news_data (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_onchain_data (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_technical (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_sentiment (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aggregated_data (
    id BIGSERIAL PRIMARY KEY,
    cycle_id TEXT REFERENCES trading_cycles(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw data indexes
CREATE INDEX IF NOT EXISTS idx_raw_binance_cycle ON raw_binance_data(cycle_id);
CREATE INDEX IF NOT EXISTS idx_raw_news_cycle ON raw_news_data(cycle_id);
CREATE INDEX IF NOT EXISTS idx_raw_onchain_cycle ON raw_onchain_data(cycle_id);
CREATE INDEX IF NOT EXISTS idx_processed_tech_cycle ON processed_technical(cycle_id);
CREATE INDEX IF NOT EXISTS idx_processed_sent_cycle ON processed_sentiment(cycle_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_cycle ON aggregated_data(cycle_id);


-- =============================================
-- 11. VIEWS — Dashboard queries
-- =============================================

-- ดูเทรดล่าสุด
CREATE OR REPLACE VIEW v_recent_trades AS
SELECT 
    t.id,
    t.symbol,
    t.side,
    t.leverage || 'x' as lev,
    t.entry_price,
    t.exit_price,
    t.margin_usdt,
    t.gross_pnl,
    t.total_commission,
    t.funding_fee,
    t.net_pnl,
    t.net_pnl_percent,
    t.roi_on_margin,
    t.duration_seconds,
    t.is_winner,
    t.reasoning_open,
    t.reasoning_close,
    t.opened_at,
    t.closed_at,
    t.status
FROM trades t
ORDER BY COALESCE(t.closed_at, t.opened_at) DESC
LIMIT 100;


-- สรุปรายวัน
CREATE OR REPLACE VIEW v_daily_performance AS
SELECT 
    DATE(closed_at) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN is_winner = false THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END)::NUMERIC / 
          NULLIF(COUNT(*), 0) * 100, 1) as win_rate,
    SUM(gross_pnl) as total_gross_pnl,
    SUM(total_commission) as total_fees,
    SUM(funding_fee) as total_funding,
    SUM(net_pnl) as total_net_pnl,
    AVG(net_pnl) as avg_net_pnl,
    MAX(net_pnl) as best_trade,
    MIN(net_pnl) as worst_trade,
    AVG(duration_seconds) as avg_hold_seconds
FROM trades
WHERE status = 'CLOSED'
GROUP BY DATE(closed_at)
ORDER BY trade_date DESC;


-- สรุปรายเหรียญ
CREATE OR REPLACE VIEW v_symbol_performance AS
SELECT 
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END)::NUMERIC / 
          NULLIF(COUNT(*), 0) * 100, 1) as win_rate,
    SUM(net_pnl) as total_net_pnl,
    SUM(total_commission) as total_fees,
    AVG(roi_on_margin) as avg_roi
FROM trades
WHERE status = 'CLOSED'
GROUP BY symbol
ORDER BY total_net_pnl DESC;


-- Equity Curve (ใช้สร้างกราฟ)
CREATE OR REPLACE VIEW v_equity_curve AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    AVG(equity) as avg_equity,
    MIN(equity) as min_equity,
    MAX(equity) as max_equity,
    AVG(total_unrealized_pnl) as avg_unrealized_pnl,
    MAX(open_positions_count) as max_open_positions
FROM account_snapshots
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;


-- AI Model Performance (เปรียบเทียบ model)
CREATE OR REPLACE VIEW v_ai_model_stats AS
SELECT 
    tc.ai_model,
    COUNT(*) as total_cycles,
    AVG(tc.ai_confidence) as avg_confidence,
    SUM(tc.trades_executed) as total_trades,
    AVG(tc.total_cycle_ms) as avg_cycle_ms
FROM trading_cycles tc
WHERE tc.status = 'COMPLETED' AND tc.ai_model IS NOT NULL
GROUP BY tc.ai_model
ORDER BY total_cycles DESC;


-- =============================================
-- 12. DATA RETENTION (ฟังก์ชัน cleanup)
-- =============================================
CREATE OR REPLACE FUNCTION fn_cleanup_old_data(retention_days INTEGER DEFAULT 30)
RETURNS TABLE(table_name TEXT, rows_deleted BIGINT) AS $$
DECLARE
    cutoff TIMESTAMPTZ := NOW() - (retention_days || ' days')::INTERVAL;
    _count BIGINT;
BEGIN
    -- Raw data (ลบหลัง 30 วัน)
    DELETE FROM raw_binance_data WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'raw_binance_data'; rows_deleted := _count; RETURN NEXT;
    
    DELETE FROM raw_news_data WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'raw_news_data'; rows_deleted := _count; RETURN NEXT;
    
    DELETE FROM raw_onchain_data WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'raw_onchain_data'; rows_deleted := _count; RETURN NEXT;
    
    DELETE FROM processed_technical WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'processed_technical'; rows_deleted := _count; RETURN NEXT;
    
    DELETE FROM processed_sentiment WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'processed_sentiment'; rows_deleted := _count; RETURN NEXT;
    
    DELETE FROM aggregated_data WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'aggregated_data'; rows_deleted := _count; RETURN NEXT;
    
    -- Error logs (ลบหลัง 7 วัน)
    DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'error_logs'; rows_deleted := _count; RETURN NEXT;
    
    -- Market snapshots เก็บ 7 วัน (จำนวนเยอะ)
    DELETE FROM market_snapshots WHERE created_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'market_snapshots'; rows_deleted := _count; RETURN NEXT;
    
    -- Account snapshots เก็บ 90 วัน
    DELETE FROM account_snapshots WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'account_snapshots'; rows_deleted := _count; RETURN NEXT;
    
    -- Positions history เก็บ 30 วัน
    DELETE FROM positions_history WHERE created_at < cutoff;
    GET DIAGNOSTICS _count = ROW_COUNT;
    table_name := 'positions_history'; rows_deleted := _count; RETURN NEXT;
    
    -- trades, orders, ai_decisions, news_articles — เก็บถาวร
END;
$$ LANGUAGE plpgsql;


-- =============================================
-- 13. TABLE COMMENTS
-- =============================================
COMMENT ON TABLE trading_cycles IS 'รอบการเทรดทุก 2 นาที พร้อม cycle timing และ balance snapshot';
COMMENT ON TABLE market_snapshots IS 'ข้อมูลตลาดต่อเหรียญต่อ cycle: ราคา, EMA, RSI, MACD, ATR, funding rate — ใช้แท่ง 5 นาที';
COMMENT ON TABLE orders IS 'Raw order data จาก Binance: fill price, qty, commission';
COMMENT ON TABLE trades IS 'เทรดที่จับคู่ open+close: gross PnL, fees, funding, net PnL';
COMMENT ON TABLE positions_history IS 'Snapshot ของ positions ที่เปิดอยู่ทุก cycle';
COMMENT ON TABLE account_snapshots IS 'Balance + equity snapshot ทุก cycle สำหรับ equity curve';
COMMENT ON TABLE ai_decisions IS 'ผลการตัดสินใจ AI ทุก cycle';
COMMENT ON TABLE news_articles IS 'ข่าวที่รวบรวมจาก RSS + scraping';
COMMENT ON TABLE error_logs IS 'Error logs ทั้งหมด';
COMMENT ON FUNCTION fn_cleanup_old_data IS 'ลบข้อมูลเก่าตาม retention policy — เรียกทุกวัน';
