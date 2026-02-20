use zeroclaw_common::config::ValidationConfig;
use zeroclaw_common::types::CoinMetrics;
use zeroclaw_signals::cross_corr::LeadLagResult;

/// คำนวณ Composite Opportunity Score
pub fn calculate_cos(
    symbol: &str,
    lead_lag: &Option<LeadLagResult>,
    lead_lag_cv: f64,
    avg_spread_bps: f64,
    avg_volume_usd: f64,
    bid_depth_usd: f64,
    ask_depth_usd: f64,
    obi_mean: f64,
    obi_std: f64,
    config: &ValidationConfig,
) -> CoinMetrics {
    let mut cos_score = 0.0;
    let mut rejection_reason: Option<String> = None;

    // Extract lead-lag values
    let (lag_ms, correlation) = match lead_lag {
        Some(ll) => (ll.optimal_lag_ms, ll.peak_correlation),
        None => (0.0, 0.0),
    };

    // ---- Criterion 1: Lead-Lag Score (30%) ----
    let lls = if correlation >= config.min_correlation
        && lag_ms >= config.min_lag_ms
        && lag_ms <= config.max_lag_ms
    {
        // Scale: 0.60 correlation = 0, 1.0 correlation = 100
        let score = ((correlation - config.min_correlation) / (1.0 - config.min_correlation)) * 100.0;
        score.min(100.0)
    } else {
        if correlation < config.min_correlation {
            rejection_reason = Some(format!(
                "Correlation too low: {:.3} < {:.3}",
                correlation, config.min_correlation
            ));
        } else if lag_ms < config.min_lag_ms {
            rejection_reason = Some(format!(
                "Lag too short: {:.0}ms < {:.0}ms",
                lag_ms, config.min_lag_ms
            ));
        } else {
            rejection_reason = Some(format!(
                "Lag too long: {:.0}ms > {:.0}ms",
                lag_ms, config.max_lag_ms
            ));
        }
        0.0
    };
    cos_score += 0.30 * lls;

    // ---- Criterion 2: Spread Efficiency Score (25%) ----
    let maker_fee_bps = 1.0; // Bybit maker fee 0.01% = 1 bps
    let round_trip_cost = 2.0 * maker_fee_bps;
    let alpha_estimate = avg_spread_bps * 0.5; // conservative: capture half the spread
    let alpha_cost_ratio = if round_trip_cost > 0.0 {
        alpha_estimate / round_trip_cost
    } else {
        0.0
    };

    let ses = if avg_spread_bps <= config.max_spread_bps && alpha_cost_ratio >= config.min_alpha_cost_ratio {
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
    cos_score += 0.25 * ses;

    // ---- Criterion 3: OFI Signal Quality (20%) ----
    let ofsq = (obi_std * 100.0).min(100.0); // Higher OBI variance = more signal
    cos_score += 0.20 * ofsq;

    // ---- Criterion 4: Liquidity Depth (15%) ----
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
    cos_score += 0.15 * lds;

    // ---- Criterion 5: Lead-Lag Stability (10%) ----
    let stability = if lead_lag_cv <= config.max_lag_cv {
        ((1.0 - lead_lag_cv / config.max_lag_cv) * 100.0).max(0.0)
    } else {
        if rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Lag unstable: CV={:.2} > {:.2}",
                lead_lag_cv, config.max_lag_cv
            ));
        }
        0.0
    };
    cos_score += 0.10 * stability;

    // ---- Verdict ----
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
        avg_spread_bps,
        avg_volume_24h_usd: avg_volume_usd,
        bid_depth_usd,
        ask_depth_usd,
        obi_mean,
        obi_std,
        cos_score,
        verdict,
        rejection_reason,
    }
}
