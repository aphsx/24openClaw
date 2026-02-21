use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct ScannerConfig {
    pub general: GeneralConfig,
    pub validation: ValidationConfig,
    pub universe: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GeneralConfig {
    pub scan_duration_hours: f64,
    pub snapshot_interval_ms: u64,
    pub cross_corr_interval_sec: u64,
    pub cross_corr_window: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ValidationConfig {
    pub min_lag_ms: f64,
    pub max_lag_ms: f64,
    pub min_correlation: f64,
    pub max_lag_cv: f64,
    pub max_spread_bps: f64,
    pub min_alpha_cost_ratio: f64,
    pub min_depth_usd: f64,
    /// Minimum lead-lag samples before using CV (prevent false positives)
    #[serde(default = "default_min_ll_samples")]
    pub min_lead_lag_samples: usize,
}

fn default_min_ll_samples() -> usize {
    10
}

impl Default for ScannerConfig {
    fn default() -> Self {
        Self {
            general: GeneralConfig {
                scan_duration_hours: 24.0,
                snapshot_interval_ms: 200,
                cross_corr_interval_sec: 30,
                cross_corr_window: 1500,
            },
            validation: ValidationConfig {
                min_lag_ms: 80.0,
                max_lag_ms: 500.0,
                min_correlation: 0.60,
                max_lag_cv: 0.40,
                max_spread_bps: 15.0,
                min_alpha_cost_ratio: 2.5,
                min_depth_usd: 100_000.0,
                min_lead_lag_samples: 10,
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

impl ScannerConfig {
    /// Load config from TOML file, fallback to defaults if file doesn't exist.
    pub fn load(path: &str) -> Self {
        match std::fs::read_to_string(path) {
            Ok(content) => {
                match toml::from_str::<ScannerConfig>(&content) {
                    Ok(config) => config,
                    Err(e) => {
                        eprintln!("Warning: Failed to parse {}: {}. Using defaults.", path, e);
                        Self::default()
                    }
                }
            }
            Err(_) => {
                eprintln!("Warning: Config file {} not found. Using defaults.", path);
                Self::default()
            }
        }
    }
}
