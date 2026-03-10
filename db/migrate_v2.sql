-- Migration v2: Add missing cointegration_pvalue column and pvalue_max config
ALTER TABLE pairs ADD COLUMN IF NOT EXISTS cointegration_pvalue DECIMAL(8,6);

INSERT INTO config (key, value, description)
VALUES ('pvalue_max', 0.05, 'Max cointegration p-value (ADF test)')
ON CONFLICT (key) DO NOTHING;
