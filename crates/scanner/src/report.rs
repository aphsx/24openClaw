use tradingclaw_common::types::ScannerReport;

/// Generate a comprehensive readable text report with all signal metrics.
pub fn generate_text_report(report: &ScannerReport) -> String {
    let mut out = String::new();

    out.push_str("================================================================\n");
    out.push_str("         TRADINGCLAW SCANNER VALIDATION REPORT v2.0\n");
    out.push_str("       7-Criterion COS | Bidirectional Lead-Lag | Microprice\n");
    out.push_str("================================================================\n\n");
    out.push_str(&format!("Period: {} to {}\n", report.start_time, report.end_time));
    out.push_str(&format!("Duration: {:.1} hours\n", report.duration_hours));
    out.push_str(&format!("Coins Scanned: {}\n", report.coins_scanned));
    out.push_str(&format!("Coins Passed: {}\n\n", report.coins_passed));

    out.push_str("=== RESULTS (sorted by COS score) ===\n\n");

    for (i, coin) in report.results.iter().enumerate() {
        out.push_str(&format!(
            "#{} {} — COS: {:.1}/100 — {}\n",
            i + 1,
            coin.symbol,
            coin.cos_score,
            coin.verdict
        ));
        out.push_str("  ─────────────────────────────────────────\n");

        // Lead-Lag
        out.push_str(&format!(
            "  Lead-Lag: {:.0}ms (corr={:.3}, CV={:.2}) [{}]\n",
            coin.lead_lag_ms.abs(),
            coin.lead_lag_correlation,
            coin.lead_lag_cv,
            coin.lead_lag_direction,
        ));

        // Spread & Depth
        out.push_str(&format!(
            "  Spread: {:.1} bps | Depth: ${:.0}K bid / ${:.0}K ask\n",
            coin.avg_spread_bps,
            coin.bid_depth_usd / 1000.0,
            coin.ask_depth_usd / 1000.0,
        ));

        // MLOFI
        out.push_str(&format!(
            "  MLOFI: strength={:.3} (Binance={:.3}, Bybit={:.3})\n",
            coin.mlofi_signal_strength,
            coin.mlofi_binance_mean,
            coin.mlofi_bybit_mean,
        ));

        // TFI
        out.push_str(&format!(
            "  TFI: agreement={:.1}% (Binance={:.3}, Bybit={:.3})\n",
            coin.tfi_agreement_ratio * 100.0,
            coin.tfi_binance_mean,
            coin.tfi_bybit_mean,
        ));

        // Microprice
        out.push_str(&format!(
            "  Microprice Divergence: mean={:.2} bps, std={:.2} bps\n",
            coin.microprice_divergence_mean_bps,
            coin.microprice_divergence_std_bps,
        ));

        // Volatility & Intensity
        out.push_str(&format!(
            "  Volatility: {:.1}% ann. | Trade Intensity: ${:.0}/sec\n",
            coin.realized_volatility * 100.0,
            coin.trade_intensity_usd_per_sec,
        ));

        // OBI
        out.push_str(&format!(
            "  OBI: mean={:.3}, std={:.3}\n",
            coin.obi_mean, coin.obi_std
        ));

        if let Some(reason) = &coin.rejection_reason {
            out.push_str(&format!("  >> REJECTED: {}\n", reason));
        }
        out.push('\n');
    }

    out.push_str("=== SCORING WEIGHTS ===\n\n");
    out.push_str("  Lead-Lag Quality:        25%\n");
    out.push_str("  Spread Efficiency:       15%\n");
    out.push_str("  MLOFI Signal Strength:   15%\n");
    out.push_str("  Microprice Divergence:   15%\n");
    out.push_str("  Trade Flow Confirmation: 10%\n");
    out.push_str("  Liquidity Depth:         10%\n");
    out.push_str("  Lag Stability:           10%\n\n");

    out.push_str("=== RECOMMENDATION ===\n\n");
    out.push_str(&report.recommendation);
    out.push('\n');

    out
}
