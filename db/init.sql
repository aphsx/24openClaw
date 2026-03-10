CREATE TABLE instruments (
    symbol      VARCHAR(20) PRIMARY KEY,
    has_futures BOOLEAN DEFAULT true,
    vol_24h     DECIMAL(20,2),
    last_price  DECIMAL(20,10),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ohlcv_daily (
    symbol VARCHAR(20) NOT NULL,
    ts     DATE NOT NULL,
    close  DECIMAL(20,10) NOT NULL,
    volume DECIMAL(20,4),
    PRIMARY KEY (symbol, ts)
);

CREATE TABLE pairs (
    id              SERIAL PRIMARY KEY,
    symbol_a        VARCHAR(20) NOT NULL,
    symbol_b        VARCHAR(20) NOT NULL,
    correlation     DECIMAL(6,4),
    hurst_exp       DECIMAL(6,4),
    half_life       DECIMAL(8,2),
    hedge_ratio     DECIMAL(10,6),
    zscore          DECIMAL(8,4),
    zone            VARCHAR(10),
    qualified       BOOLEAN DEFAULT false,
    validation_json JSONB,
    scanned_at           TIMESTAMPTZ,
    cointegration_pvalue DECIMAL(8,6),
    UNIQUE(symbol_a, symbol_b)
);

CREATE TABLE trades (
    id              SERIAL PRIMARY KEY,
    group_id        UUID NOT NULL UNIQUE,
    symbol_a        VARCHAR(20) NOT NULL,
    symbol_b        VARCHAR(20) NOT NULL,
    leg_a_side      VARCHAR(5) NOT NULL,
    leg_a_size_usd  DECIMAL(12,2),
    leg_a_order_id  VARCHAR(100),
    leg_b_side      VARCHAR(5) NOT NULL,
    leg_b_size_usd  DECIMAL(12,2),
    leg_b_order_id  VARCHAR(100),
    entry_zscore    DECIMAL(8,4),
    entry_corr      DECIMAL(6,4),
    entry_beta      DECIMAL(10,6),
    entry_zone      VARCHAR(10),
    exit_zscore     DECIMAL(8,4),
    exit_reason     VARCHAR(20),
    pnl_usd         DECIMAL(12,2),
    funding_paid    DECIMAL(12,4),
    fees_paid       DECIMAL(12,4),
    status          VARCHAR(20) DEFAULT 'open',
    validation_json JSONB,
    opened_at       TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);
CREATE INDEX idx_trades_status ON trades(status);

CREATE TABLE reconciliation_logs (
    id           SERIAL PRIMARY KEY,
    checked_at   TIMESTAMPTZ DEFAULT NOW(),
    db_count     INTEGER,
    exchange_count INTEGER,
    orphans      INTEGER DEFAULT 0,
    action       VARCHAR(20) DEFAULT 'alert_only',
    details      JSONB
);

CREATE TABLE scan_results (
    id          SERIAL PRIMARY KEY,
    scanned_at  TIMESTAMPTZ DEFAULT NOW(),
    total_pairs INTEGER,
    qualified   INTEGER,
    signals     INTEGER,
    blocked     INTEGER,
    duration_ms INTEGER,
    details     JSONB
);

CREATE TABLE config (
    key         VARCHAR(50) PRIMARY KEY,
    value       DECIMAL(12,6) NOT NULL,
    description TEXT,
    backtest_rank  INTEGER,
    backtest_total INTEGER,
    last_optimized TIMESTAMPTZ
);

INSERT INTO config (key, value, description) VALUES
('zscore_entry',      2.0,    'Z-Score entry threshold'),
('zscore_tp',         0.5,    'Z-Score take profit'),
('zscore_sl',         3.0,    'Z-Score stop loss'),
('corr_min',          0.80,   'Minimum correlation'),
('half_life_min',     5,      'Min half-life days'),
('half_life_max',     30,     'Max half-life days'),
('safe_buffer',       0.5,    'Buffer from SL for safe zone'),
('grace_period_sec',  300,    'Grace period seconds'),
('cooldown_sec',      3600,   'Cooldown after close'),
('max_same_coin',     2,      'Max pairs per coin'),
('position_size_usd', 500,    'USD per leg'),
('scan_interval_sec', 60,     'Scan interval'),
('pvalue_max',        0.05,   'Max cointegration p-value (ADF test)');
