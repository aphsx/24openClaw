use anyhow::Result;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use tracing::{info, warn};
use tradingclaw_common::config::ScannerConfig;
use tradingclaw_common::types::*;
use tradingclaw_network::{binance, bybit};
use tradingclaw_signals::{cross_corr::CrossCorrCalculator, mlofi::MlofiCalculator, obi, spread::SpreadTracker, tfi::TfiCalculator};
use tradingclaw_scanner::{cos, report};

/// State ของแต่ละเหรียญ
struct CoinState {
    binance_book: OrderBook,
    bybit_book: OrderBook,
    mlofi_binance: MlofiCalculator,
    mlofi_bybit: MlofiCalculator,
    tfi_binance: TfiCalculator,
    cross_corr: CrossCorrCalculator,
    spread_tracker: SpreadTracker,
    obi_values: Vec<f64>,          // เก็บ OBI ทุก snapshot
    lead_lag_results: Vec<(f64, f64)>, // (lag_ms, correlation) ทุกรอบ
}

#[tokio::main]
async fn main() -> Result<()> {
    // ===== Setup logging =====
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .with_target(false)
        .init();

    info!("=== TRADINGCLAW SCANNER v0.1 ===");

    // ===== Load config =====
    let config = ScannerConfig::default();  // TODO: load from scanner.toml
    let symbols = config.universe.clone();

    info!("Scanning {} coins: {:?}", symbols.len(), symbols);

    // ===== Initialize per-coin state =====
    let state: Arc<Mutex<HashMap<String, CoinState>>> = Arc::new(Mutex::new(HashMap::new()));

    {
        let mut s = state.lock().unwrap();
        for symbol in &symbols {
            s.insert(
                symbol.clone(),
                CoinState {
                    binance_book: OrderBook::new(Exchange::Binance, symbol.clone()),
                    bybit_book: OrderBook::new(Exchange::Bybit, symbol.clone()),
                    mlofi_binance: MlofiCalculator::new(0.3, 10, 5000),
                    mlofi_bybit: MlofiCalculator::new(0.3, 10, 5000),
                    tfi_binance: TfiCalculator::new(100),
                    cross_corr: CrossCorrCalculator::new(config.general.cross_corr_window),
                    spread_tracker: SpreadTracker::new(10000),
                    obi_values: Vec::new(),
                    lead_lag_results: Vec::new(),
                },
            );
        }
    }

    // ===== Create channels =====
    let (binance_tx, mut binance_rx) = mpsc::unbounded_channel();
    let (bybit_tx, mut bybit_rx) = mpsc::unbounded_channel();

    // ===== Spawn WebSocket tasks =====
    let symbols_clone = symbols.clone();
    tokio::spawn(async move {
        if let Err(e) = binance::connect_binance(symbols_clone, binance_tx).await {
            tracing::error!("Binance connector failed: {:?}", e);
        }
    });

    let symbols_clone = symbols.clone();
    tokio::spawn(async move {
        if let Err(e) = bybit::connect_bybit(symbols_clone, bybit_tx).await {
            tracing::error!("Bybit connector failed: {:?}", e);
        }
    });

    // ===== Cross-correlation calculation timer =====
    let state_clone = state.clone();
    let corr_interval = config.general.cross_corr_interval_sec;
    tokio::spawn(async move {
        // รอให้เก็บ data สัก 60 วินาทีก่อน
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
        info!("Starting cross-correlation calculations...");

        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(corr_interval)).await;

            let mut s = state_clone.lock().unwrap();
            for (symbol, coin) in s.iter_mut() {
                if let Some(result) = coin.cross_corr.calculate(50.0, 500.0, 10.0) {
                    coin.lead_lag_results.push((
                        result.optimal_lag_ms,
                        result.peak_correlation,
                    ));
                    info!(
                        "{}: lag={:.0}ms, corr={:.3}",
                        symbol, result.optimal_lag_ms, result.peak_correlation
                    );
                }
            }
        }
    });

    // ===== Status printer =====
    let state_clone = state.clone();
    let config_clone = config.clone();
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(300)).await; // ทุก 5 นาที
            let s = state_clone.lock().unwrap();
            info!("--- STATUS (Interim Scores) ---");
            for (symbol, coin) in s.iter() {
                // คำนวณ lead-lag statistics เบื้องต้น
                let (avg_lag, avg_corr, lag_cv) = if !coin.lead_lag_results.is_empty() {
                    let lags: Vec<f64> = coin.lead_lag_results.iter().map(|(l, _)| *l).collect();
                    let corrs: Vec<f64> = coin.lead_lag_results.iter().map(|(_, c)| *c).collect();

                    let avg_lag = lags.iter().sum::<f64>() / lags.len() as f64;
                    let avg_corr = corrs.iter().sum::<f64>() / corrs.len() as f64;

                    let lag_std = if lags.len() > 1 {
                        let mean = avg_lag;
                        (lags.iter().map(|l| (l - mean).powi(2)).sum::<f64>() / (lags.len() - 1) as f64).sqrt()
                    } else {
                        0.0
                    };
                    let lag_cv = if avg_lag > 0.0 { lag_std / avg_lag } else { 1.0 };

                    (avg_lag, avg_corr, lag_cv)
                } else {
                    (0.0, 0.0, 1.0)
                };

                // OBI statistics เบื้องต้น
                let obi_mean = if !coin.obi_values.is_empty() {
                    coin.obi_values.iter().sum::<f64>() / coin.obi_values.len() as f64
                } else {
                    0.0
                };
                let obi_std = if coin.obi_values.len() > 1 {
                    let mean = obi_mean;
                    (coin.obi_values.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
                        / (coin.obi_values.len() - 1) as f64)
                        .sqrt()
                } else {
                    0.0
                };

                // Depth in USD (approximate) เบื้องต้น
                let mid = coin.bybit_book.mid_price().unwrap_or(1.0);
                let bid_depth_usd = coin.bybit_book.bid_depth(5) * mid;
                let ask_depth_usd = coin.bybit_book.ask_depth(5) * mid;

                // ไม่ต้อง clone เพราะ cross_corr.calculate() ใช้ &self ไม่ได้ขโมย ownership
                let current_result = coin.cross_corr.calculate(50.0, 500.0, 10.0);

                let metrics = cos::calculate_cos(
                    symbol,
                    &current_result,
                    lag_cv,
                    coin.spread_tracker.mean(),
                    0.0, // volume estimate
                    bid_depth_usd,
                    ask_depth_usd,
                    obi_mean,
                    obi_std,
                    &config_clone.validation,
                );

                let spread = coin.spread_tracker.mean();
                let ll_count = coin.lead_lag_results.len();

                info!(
                    "{}: SCORE={:.1}/100 | spread={:.1}bps, lead-lag samples={}",
                    symbol,
                    metrics.cos_score,
                    spread,
                    ll_count
                );
            }
        }
    });

    // ===== Main data processing loop =====
    let scan_duration = tokio::time::Duration::from_secs(
        (config.general.scan_duration_hours * 3600.0) as u64,
    );
    let start_time = chrono::Utc::now();
    let deadline = tokio::time::Instant::now() + scan_duration;

    info!("Scanning for {:.1} hours...", config.general.scan_duration_hours);

    loop {
        tokio::select! {
            // Process Binance messages
            Some(msg) = binance_rx.recv() => {
                let mut s = state.lock().unwrap();
                match msg {
                    binance::BinanceMessage::DepthUpdate { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.binance_book.update_from_snapshot(bids, asks, timestamp_us);

                            // คำนวณ MLOFI
                            let (_raw, _norm) = coin.mlofi_binance.update(&coin.binance_book);

                            // คำนวณ OBI
                            let obi_val = obi::calculate_obi(&coin.binance_book, 5);
                            coin.obi_values.push(obi_val);

                            // เก็บ mid price สำหรับ cross-correlation
                            if let Some(mid) = coin.binance_book.mid_price() {
                                coin.cross_corr.add_leader_price(timestamp_us, mid);
                            }
                        }
                    }
                    binance::BinanceMessage::Trade(trade) => {
                        if let Some(coin) = s.get_mut(&trade.symbol) {
                            let _tfi = coin.tfi_binance.update(&trade);
                        }
                    }
                }
            }

            // Process Bybit messages
            Some(msg) = bybit_rx.recv() => {
                let mut s = state.lock().unwrap();
                match msg {
                    bybit::BybitMessage::DepthSnapshot { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.bybit_book.update_from_snapshot(bids, asks, timestamp_us);

                            let (_raw, _norm) = coin.mlofi_bybit.update(&coin.bybit_book);

                            // เก็บ spread
                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            // เก็บ mid price สำหรับ cross-correlation (follower)
                            if let Some(mid) = coin.bybit_book.mid_price() {
                                coin.cross_corr.add_follower_price(timestamp_us, mid);
                            }
                        }
                    }
                    bybit::BybitMessage::DepthDelta { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            // Delta update: update individual levels
                            for level in &bids {
                                coin.bybit_book.update_bid(level.price, level.quantity);
                            }
                            for level in &asks {
                                coin.bybit_book.update_ask(level.price, level.quantity);
                            }
                            coin.bybit_book.timestamp_us = timestamp_us;

                            let (_raw, _norm) = coin.mlofi_bybit.update(&coin.bybit_book);

                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            if let Some(mid) = coin.bybit_book.mid_price() {
                                coin.cross_corr.add_follower_price(timestamp_us, mid);
                            }
                        }
                    }
                    bybit::BybitMessage::Trade(_trade) => {
                        // เก็บไว้ถ้าต้องการ
                    }
                }
            }

            // Scan duration expired
            _ = tokio::time::sleep_until(deadline) => {
                info!("Scan duration reached. Generating report...");
                break;
            }
        }
    }

    // ===== Generate Report =====
    let end_time = chrono::Utc::now();
    let s = state.lock().unwrap();

    let mut results: Vec<CoinMetrics> = Vec::new();

    for (symbol, coin) in s.iter() {
        // คำนวณ lead-lag statistics
        let (avg_lag, avg_corr, lag_cv) = if !coin.lead_lag_results.is_empty() {
            let lags: Vec<f64> = coin.lead_lag_results.iter().map(|(l, _)| *l).collect();
            let corrs: Vec<f64> = coin.lead_lag_results.iter().map(|(_, c)| *c).collect();

            let avg_lag = lags.iter().sum::<f64>() / lags.len() as f64;
            let avg_corr = corrs.iter().sum::<f64>() / corrs.len() as f64;

            let lag_std = if lags.len() > 1 {
                let mean = avg_lag;
                (lags.iter().map(|l| (l - mean).powi(2)).sum::<f64>() / (lags.len() - 1) as f64).sqrt()
            } else {
                0.0
            };
            let lag_cv = if avg_lag > 0.0 { lag_std / avg_lag } else { 1.0 };

            (avg_lag, avg_corr, lag_cv)
        } else {
            (0.0, 0.0, 1.0)
        };

        // OBI statistics
        let obi_mean = if !coin.obi_values.is_empty() {
            coin.obi_values.iter().sum::<f64>() / coin.obi_values.len() as f64
        } else {
            0.0
        };
        let obi_std = if coin.obi_values.len() > 1 {
            let mean = obi_mean;
            (coin.obi_values.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
                / (coin.obi_values.len() - 1) as f64)
                .sqrt()
        } else {
            0.0
        };

        // Depth in USD (approximate)
        let mid = coin.bybit_book.mid_price().unwrap_or(1.0);
        let bid_depth_usd = coin.bybit_book.bid_depth(5) * mid;
        let ask_depth_usd = coin.bybit_book.ask_depth(5) * mid;

        let lead_lag_result = coin.cross_corr.calculate(50.0, 500.0, 10.0);

        let metrics = cos::calculate_cos(
            symbol,
            &lead_lag_result,
            lag_cv,
            coin.spread_tracker.mean(),
            0.0, // volume estimate (TODO: calculate from trades)
            bid_depth_usd,
            ask_depth_usd,
            obi_mean,
            obi_std,
            &config.validation,
        );

        results.push(metrics);
    }

    // Sort by COS score descending
    results.sort_by(|a, b| b.cos_score.partial_cmp(&a.cos_score).unwrap());

    let passed = results.iter().filter(|r| r.rejection_reason.is_none()).count();

    let recommendation = if passed >= 3 {
        format!(
            "PROCEED — {} coins passed validation.\nPrimary: {}\nStandby: {}, {}\nRecommendation: Start Phase 1 with primary coin.",
            passed,
            results.get(0).map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(1).map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(2).map(|r| r.symbol.as_str()).unwrap_or("?"),
        )
    } else if passed >= 1 {
        format!(
            "PROCEED WITH CAUTION — Only {} coin(s) passed.\nConsider running scan again at different time of day.",
            passed
        )
    } else {
        "PIVOT STRATEGY — No coins passed validation.\nCEIFA may not be viable. Consider Funding Rate Arbitrage.".to_string()
    };

    let scanner_report = ScannerReport {
        start_time: start_time.to_rfc3339(),
        end_time: end_time.to_rfc3339(),
        duration_hours: (end_time - start_time).num_seconds() as f64 / 3600.0,
        coins_scanned: results.len(),
        coins_passed: passed,
        results,
        recommendation,
    };

    // Output
    let text_report = report::generate_text_report(&scanner_report);
    println!("{}", text_report);

    // Save to file
    let json_report = serde_json::to_string_pretty(&scanner_report)?;
    std::fs::create_dir_all("data")?;
    std::fs::write("data/scanner_report.json", &json_report)?;
    std::fs::write("data/scanner_report.txt", &text_report)?;

    info!("Report saved to data/scanner_report.json and data/scanner_report.txt");

    Ok(())
}
