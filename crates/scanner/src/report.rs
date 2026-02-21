use tradingclaw_common::types::ScannerReport;

/// สร้าง readable text report
pub fn generate_text_report(report: &ScannerReport) -> String {
    let mut out = String::new();

    out.push_str("============================================================\n");
    out.push_str("           TRADINGCLAW SCANNER VALIDATION REPORT\n");
    out.push_str("==========================================================\n\n");
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
        out.push_str(&format!(
            "  Lead-Lag: {:.0}ms (corr={:.3}, CV={:.2})\n",
            coin.lead_lag_ms, coin.lead_lag_correlation, coin.lead_lag_cv
        ));
        out.push_str(&format!(
            "  Spread: {:.1} bps | Depth: ${:.0}K bid / ${:.0}K ask\n",
            coin.avg_spread_bps,
            coin.bid_depth_usd / 1000.0,
            coin.ask_depth_usd / 1000.0,
        ));
        out.push_str(&format!(
            "  OBI: mean={:.3}, std={:.3}\n",
            coin.obi_mean, coin.obi_std
        ));
        if let Some(reason) = &coin.rejection_reason {
            out.push_str(&format!("  REJECTED: {}\n", reason));
        }
        out.push_str("\n");
    }

    out.push_str("=== RECOMMENDATION ===\n\n");
    out.push_str(&report.recommendation);
    out.push_str("\n");

    out
}
