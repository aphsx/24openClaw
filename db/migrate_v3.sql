-- Migration v3: Add missing fields for full trade lifecycle tracking

-- Add missing columns to trades table
ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_half_life  DECIMAL(8,2);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS grace_until      TIMESTAMPTZ;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS leg_a_entry_price DECIMAL(20,10);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS leg_b_entry_price DECIMAL(20,10);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS current_zscore   DECIMAL(8,4);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS last_monitored_at TIMESTAMPTZ;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS close_reason_detail TEXT;

-- Add new config params
INSERT INTO config (key, value, description) VALUES
  ('max_loss_pct',         5.0,    'Maximum loss per pair as % of allocated capital before SL'),
  ('max_drawdown_pct',    15.0,    'Total portfolio drawdown % to halt all trading'),
  ('funding_rate_max',     0.001,  'Max funding rate per 8h before emergency exit (0.001 = 0.1%)'),
  ('beta_drift_max_pct',  20.0,    'Max beta drift % from entry before flagging position'),
  ('monitor_interval_sec', 30.0,   'Position monitor check interval in seconds'),
  ('leverage',             2.0,    'Default leverage (informational — set on exchange)'),
  ('max_open_pairs',       5.0,    'Maximum number of simultaneously open pair trades'),
  ('corr_break_sl',        0.50,   'Correlation drop below this triggers stop loss')
ON CONFLICT (key) DO NOTHING;
