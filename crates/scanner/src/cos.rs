use tradingclaw_common::config::ValidationConfig;
use tradingclaw_common::types::CoinMetrics;
use tradingclaw_signals::cross_corr::LeadLagResult;

/// Composite Opportunity Score — 7 weighted criteria using ALL available signals.
///
/// | Criterion               | Weight | Source                           |
/// |-------------------------|--------|----------------------------------|
/// | Lead-Lag Quality        | 25%    | Cross-correlation (bidirectional)|
/// | Spread Efficiency       | 15%    | Spread tracker                   |
/// | MLOFI Signal Strength   | 15%    | Avg |MLOFI_norm| across exchanges|
/// | Microprice Divergence   | 15%    | Cross-exchange microprice spread |
/// | Trade Flow Confirmation | 10%    | TFI agreement between exchanges  |
/// | Liquidity Depth         | 10%    | LOB depth in USD                 |
/// | Lag Stability           | 10%    | CV with min sample requirement   |
#[allow(clippy::too_many_arguments)]
pub fn calculate_cos(
    symbol: &str,
    lead_lag: &Option<LeadLagResult>,
    lead_lag_cv: f64,
    lead_lag_sample_count: usize,
    avg_spread_bps: f64,
    bid_depth_usd: f64,
    ask_depth_usd: f64,
    obi_mean: f64,
    obi_std: f64,
    mlofi_signal_strength: f64,
    mlofi_binance_mean: f64,
    mlofi_bybit_mean: f64,
    tfi_agreement_ratio: f64,
    tfi_binance_mean: f64,
    tfi_bybit_mean: f64,
    microprice_div_mean_bps: f64,
    microprice_div_std_bps: f64,
    realized_volatility: f64,
    trade_intensity: f64,
    config: &ValidationConfig,
) -> CoinMetrics {
    let mut cos_score = 0.0;
    let mut rejection_reason: Option<String> = None;

    // Extract lead-lag values
    let (lag_ms, correlation, direction) = match lead_lag {
        Some(ll) => (ll.optimal_lag_ms, ll.peak_correlation, ll.direction.clone()),
        None => (0.0, 0.0, "NONE".to_string()),
    };

    let abs_lag = lag_ms.abs();

    // ======== Criterion 1: Lead-Lag Quality (25%) ========
    let lls = if correlation >= config.min_correlation
        && abs_lag >= config.min_lag_ms
        && abs_lag <= config.max_lag_ms
    {
        ((correlation - config.min_correlation)
            / (1.0 - config.min_correlation)
            * 100.0)
            .min(100.0)
    } else {
        if correlation < config.min_correlation {
            rejection_reason = Some(format!(
                "Correlation too low: {:.3} < {:.3}",
                correlation, config.min_correlation
            ));
        } else if abs_lag < config.min_lag_ms {
            rejection_reason = Some(format!(
                "Lag too short: {:.0}ms < {:.0}ms",
                abs_lag, config.min_lag_ms
            ));
        } else {
            rejection_reason = Some(format!(
                "Lag too long: {:.0}ms > {:.0}ms",
                abs_lag, config.max_lag_ms
            ));
        }
        0.0
    };
    cos_score += 0.25 * lls;

    // ======== Criterion 2: Spread Efficiency (15%) ========
    let maker_fee_bps = 1.0;
    let round_trip_cost = 2.0 * maker_fee_bps;
    // Use microprice divergence as alpha estimate if available
    let alpha_estimate = if microprice_div_mean_bps > 0.0 {
        microprice_div_mean_bps
    } else {
        avg_spread_bps * 0.5
    };
    let alpha_cost_ratio = if round_trip_cost > 0.0 {
        alpha_estimate / round_trip_cost
    } else {
        0.0
    };

    let ses = if avg_spread_bps <= config.max_spread_bps
        && alpha_cost_ratio >= config.min_alpha_cost_ratio
    {
        ((alpha_cost_ratio - config.min_alpha_cost_ratio) / 5.0 * 100.0).min(100.0)
    } else {
        if avg_spread_bps > config.max_spread_bps && rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Spread too wide: {:.1} bps > {:.1} bps",
                avg_spread_bps, config.max_spread_bps
            ));
        }
        0.0
    };
    cos_score += 0.15 * ses;

    // ======== Criterion 3: MLOFI Signal Strength (15%) ========
    let mlofi_score = (mlofi_signal_strength * 20.0).min(100.0);
    cos_score += 0.15 * mlofi_score;

    // ======== Criterion 4: Microprice Divergence (15%) ========
    let mp_score = if microprice_div_mean_bps > 0.0 {
        let excess = microprice_div_mean_bps / round_trip_cost;
        (excess * 20.0).min(100.0)
    } else {
        0.0
    };
    cos_score += 0.15 * mp_score;

    // ======== Criterion 5: Trade Flow Confirmation (10%) ========
    let tfi_score = (tfi_agreement_ratio * 100.0).min(100.0);
    cos_score += 0.10 * tfi_score;

    // ======== Criterion 6: Liquidity Depth (10%) ========
    let avg_depth = (bid_depth_usd + ask_depth_usd) / 2.0;
    let lds = if avg_depth >= config.min_depth_usd {
        ((avg_depth / config.min_depth_usd).min(5.0) / 5.0 * 100.0).min(100.0)
    } else {
        if rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Depth too low: ${:.0} < ${:.0}",
                avg_depth, config.min_depth_usd
            ));
        }
        0.0
    };
    cos_score += 0.10 * lds;

    // ======== Criterion 7: Lag Stability (10%) ========
    let stability = if lead_lag_sample_count >= config.min_lead_lag_samples {
        if lead_lag_cv <= config.max_lag_cv {
            ((1.0 - lead_lag_cv / config.max_lag_cv) * 100.0).max(0.0)
        } else {
            if rejection_reason.is_none() {
                rejection_reason = Some(format!(
                    "Lag unstable: CV={:.2} > {:.2}",
                    lead_lag_cv, config.max_lag_cv
                ));
            }
            0.0
        }
    } else {
        25.0 // Not enough samples — partial score
    };
    cos_score += 0.10 * stability;

    // ======== Verdict ========
    let verdict = if rejection_reason.is_some() {
        "REJECTED".to_string()
    } else if cos_score >= 70.0 {
        "STRONG CANDIDATE".to_string()
    } else if cos_score >= 50.0 {
        "CANDIDATE".to_string()
    } else {
        "WEAK".to_string()
    };

    CoinMetrics {
        symbol: symbol.to_string(),
        lead_lag_ms: lag_ms,
        lead_lag_correlation: correlation,
        lead_lag_cv,
        lead_lag_direction: direction,
        avg_spread_bps,
        avg_volume_24h_usd: trade_intensity * 86400.0,
        bid_depth_usd,
        ask_depth_usd,
        obi_mean,
        obi_std,
        mlofi_signal_strength,
        mlofi_binance_mean,
        mlofi_bybit_mean,
        tfi_agreement_ratio,
        tfi_binance_mean,
        tfi_bybit_mean,
        microprice_divergence_mean_bps: microprice_div_mean_bps,
        microprice_divergence_std_bps: microprice_div_std_bps,
        realized_volatility,
        trade_intensity_usd_per_sec: trade_intensity,
        cos_score,
        verdict,
        rejection_reason,
    }
}
