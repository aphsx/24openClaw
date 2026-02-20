use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct ScannerConfig {
    pub general: GeneralConfig,
    pub validation: ValidationConfig,
    pub universe: Vec<String>,  // เหรียญที่จะ scan
}

#[derive(Debug, Clone, Deserialize)]
pub struct GeneralConfig {
    /// ระยะเวลา scan (ชั่วโมง)
    pub scan_duration_hours: f64,
    /// เก็บ snapshot ทุกกี่ ms
    pub snapshot_interval_ms: u64,
    /// ทุกกี่วินาทีคำนวณ cross-correlation ใหม่
    pub cross_corr_interval_sec: u64,
    /// ขนาด window สำหรับ cross-correlation (จำนวน snapshots)
    pub cross_corr_window: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ValidationConfig {
    /// Lead-lag ต้องมากกว่ากี่ ms (ต้อง > round-trip latency)
    pub min_lag_ms: f64,
    /// Lead-lag ต้องน้อยกว่ากี่ ms
    pub max_lag_ms: f64,
    /// Cross-correlation ต้องมากกว่าเท่าไหร่
    pub min_correlation: f64,
    /// Lag CV ต้องน้อยกว่าเท่าไหร่ (stability)
    pub max_lag_cv: f64,
    /// Spread ต้องน้อยกว่ากี่ bps
    pub max_spread_bps: f64,
    /// Alpha/Cost ratio ต้องมากกว่า
    pub min_alpha_cost_ratio: f64,
    /// LOB depth ต้องมากกว่ากี่ USD (top 5 levels)
    pub min_depth_usd: f64,
}

impl Default for ScannerConfig {
    fn default() -> Self {
        Self {
            general: GeneralConfig {
                scan_duration_hours: 24.0,
                snapshot_interval_ms: 200,
                cross_corr_interval_sec: 30,
                cross_corr_window: 1500,  // 1500 snapshots × 200ms = 5 นาที
            },
            validation: ValidationConfig {
                min_lag_ms: 80.0,
                max_lag_ms: 500.0,
                min_correlation: 0.60,
                max_lag_cv: 0.40,
                max_spread_bps: 15.0,     // 0.15%
                min_alpha_cost_ratio: 2.5,
                min_depth_usd: 100_000.0,
            },
            universe: vec![
                "ETHUSDT".to_string(),
                "SOLUSDT".to_string(),
                "LINKUSDT".to_string(),
                "AVAXUSDT".to_string(),
                "ADAUSDT".to_string(),
                "DOTUSDT".to_string(),
                "MATICUSDT".to_string(),
                "NEARUSDT".to_string(),
                "FILUSDT".to_string(),
                "APTUSDT".to_string(),
                "ARBUSDT".to_string(),
                "OPUSDT".to_string(),
                "SUIUSDT".to_string(),
                "INJUSDT".to_string(),
                "TIAUSDT".to_string(),
                "SEIUSDT".to_string(),
                "JUPUSDT".to_string(),
                "WLDUSDT".to_string(),
                "RUNEUSDT".to_string(),
                "FETUSDT".to_string(),
            ],
        }
    }
}
