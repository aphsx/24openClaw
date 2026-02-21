use anyhow::Result;
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use tracing::{info, warn};
use tradingclaw_common::config::ScannerConfig;
use tradingclaw_common::types::*;
use tradingclaw_network::{binance, bybit};
use tradingclaw_signals::{
    cross_corr::CrossCorrCalculator,
    microprice,
    mlofi::MlofiCalculator,
    obi,
    spread::SpreadTracker,
    tfi::TfiCalculator,
    trade_intensity::TradeIntensityTracker,
    volatility::VolatilityTracker,
};
use tradingclaw_scanner::{cos, report};

/// Maximum rolling window for signal value storage (prevents unbounded growth)
const MAX_SIGNAL_WINDOW: usize = 50_000;

/// Per-coin state with ALL signal calculators and value storage.
struct CoinState {
    // Order books
    binance_book: OrderBook,
    bybit_book: OrderBook,

    // MLOFI calculators (both exchanges)
    mlofi_binance: MlofiCalculator,
    mlofi_bybit: MlofiCalculator,

    // TFI calculators (both exchanges)
    tfi_binance: TfiCalculator,
    tfi_bybit: TfiCalculator,

    // Cross-correlation (bidirectional)
    cross_corr: CrossCorrCalculator,

    // Spread tracker
    spread_tracker: SpreadTracker,

    // Volatility tracker
    volatility_tracker: VolatilityTracker,

    // Trade intensity trackers (both exchanges)
    trade_intensity_binance: TradeIntensityTracker,
    trade_intensity_bybit: TradeIntensityTracker,

    // Rolling signal value storage (bounded VecDeque)
    obi_values: VecDeque<f64>,
    mlofi_binance_values: VecDeque<f64>,
    mlofi_bybit_values: VecDeque<f64>,
    tfi_binance_values: VecDeque<f64>,
    tfi_bybit_values: VecDeque<f64>,
    microprice_divergences: VecDeque<f64>,

    // Lead-lag results history
    lead_lag_results: Vec<(f64, f64)>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // ===== Setup logging =====
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .with_target(false)
        .init();

    info!("=== TRADINGCLAW SCANNER v2.0 ===");
    info!("7-Criterion COS | Bidirectional Lead-Lag | Microprice | All Signals Active");

    // ===== Load config from TOML (fallback to defaults) =====
    let config = ScannerConfig::load("config/scanner.toml");
    let symbols = config.universe.clone();

    info!("Scanning {} coins: {:?}", symbols.len(), symbols);
    info!(
        "Config: duration={:.1}h, corr_interval={}s, min_corr={:.2}, min_lag={}ms",
        config.general.scan_duration_hours,
        config.general.cross_corr_interval_sec,
        config.validation.min_correlation,
        config.validation.min_lag_ms,
    );
    info!("Tracked symbols (case-sensitive): {:?}", symbols);

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
                    tfi_bybit: TfiCalculator::new(100),
                    cross_corr: CrossCorrCalculator::new(config.general.cross_corr_window),
                    spread_tracker: SpreadTracker::new(10000),
                    volatility_tracker: VolatilityTracker::new(5000),
                    trade_intensity_binance: TradeIntensityTracker::new(5.0, 60.0),
                    trade_intensity_bybit: TradeIntensityTracker::new(5.0, 60.0),
                    obi_values: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
                    mlofi_binance_values: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
                    mlofi_bybit_values: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
                    tfi_binance_values: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
                    tfi_bybit_values: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
                    microprice_divergences: VecDeque::with_capacity(MAX_SIGNAL_WINDOW),
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

    // ===== Cross-correlation timer =====
    let state_clone = state.clone();
    let corr_interval = config.general.cross_corr_interval_sec;
    let min_lag = config.validation.min_lag_ms;
    let max_lag = config.validation.max_lag_ms;
    tokio::spawn(async move {
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
        info!("Starting cross-correlation calculations (bidirectional)...");

        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(corr_interval)).await;

            let mut s = state_clone.lock().unwrap();
            for (symbol, coin) in s.iter_mut() {
                if let Some(result) = coin.cross_corr.calculate(min_lag, max_lag, 10.0) {
                    coin.lead_lag_results.push((
                        result.optimal_lag_ms,
                        result.peak_correlation,
                    ));
                    info!(
                        "{}: lag={:.0}ms, corr={:.3}, dir={}",
                        symbol, result.optimal_lag_ms, result.peak_correlation, result.direction
                    );
                }
            }
        }
    });

    // ===== Message counters for diagnostics =====
    let binance_msg_count = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let bybit_msg_count = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let binance_count_clone = binance_msg_count.clone();
    let bybit_count_clone = bybit_msg_count.clone();

    // ===== Status printer =====
    let state_clone = state.clone();
    let config_clone = config.clone();
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(300)).await;
            let s = state_clone.lock().unwrap();
            let binance_msgs = binance_count_clone.load(std::sync::atomic::Ordering::Relaxed);
            let bybit_msgs = bybit_count_clone.load(std::sync::atomic::Ordering::Relaxed);
            info!("--- STATUS (Interim Scores) ---");
            info!("Messages received: Binance={}, Bybit={}", binance_msgs, bybit_msgs);
            for (symbol, coin) in s.iter() {
                let metrics = compute_coin_metrics(symbol, coin, &config_clone);
                info!(
                    "{}: COS={:.1}/100 [{}] | spread={:.1}bps, mlofi={:.3}, ll_samples={}, dir={}",
                    symbol,
                    metrics.cos_score,
                    metrics.verdict,
                    metrics.avg_spread_bps,
                    metrics.mlofi_signal_strength,
                    coin.lead_lag_results.len(),
                    metrics.lead_lag_direction,
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
            // ===== Process Binance messages =====
            Some(msg) = binance_rx.recv() => {
                binance_msg_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                let mut s = state.lock().unwrap();
                match msg {
                    binance::BinanceMessage::DepthUpdate { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.binance_book.update_from_snapshot(bids, asks, timestamp_us);

                            // MLOFI — store the normalized value
                            let (_raw, norm) = coin.mlofi_binance.update(&coin.binance_book);
                            push_bounded(&mut coin.mlofi_binance_values, norm.abs());

                            // OBI
                            let obi_val = obi::calculate_obi(&coin.binance_book, 5);
                            push_bounded(&mut coin.obi_values, obi_val);

                            // Microprice for cross-correlation (superior to mid-price)
                            if let Some(mp) = microprice::calculate_microprice(&coin.binance_book) {
                                coin.cross_corr.add_leader_price(timestamp_us, mp);
                                coin.volatility_tracker.update(timestamp_us, mp);
                            }

                            // Microprice divergence between exchanges
                            if let Some(div) = microprice::microprice_divergence_bps(
                                &coin.binance_book,
                                &coin.bybit_book,
                            ) {
                                push_bounded(&mut coin.microprice_divergences, div.abs());
                            }
                        }
                    }
                    binance::BinanceMessage::Trade(trade) => {
                        if let Some(coin) = s.get_mut(&trade.symbol) {
                            let tfi = coin.tfi_binance.update(&trade);
                            push_bounded(&mut coin.tfi_binance_values, tfi);

                            coin.trade_intensity_binance.add_trade(
                                trade.timestamp_us,
                                trade.price,
                                trade.quantity,
                            );
                        }
                    }
                }
            }

            // ===== Process Bybit messages =====
            Some(msg) = bybit_rx.recv() => {
                bybit_msg_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                let mut s = state.lock().unwrap();
                match msg {
                    bybit::BybitMessage::DepthSnapshot { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.bybit_book.update_from_snapshot(bids, asks, timestamp_us);

                            let (_raw, norm) = coin.mlofi_bybit.update(&coin.bybit_book);
                            push_bounded(&mut coin.mlofi_bybit_values, norm.abs());

                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            if let Some(mp) = microprice::calculate_microprice(&coin.bybit_book) {
                                coin.cross_corr.add_follower_price(timestamp_us, mp);
                            }

                            if let Some(div) = microprice::microprice_divergence_bps(
                                &coin.binance_book,
                                &coin.bybit_book,
                            ) {
                                push_bounded(&mut coin.microprice_divergences, div.abs());
                            }
                        } else {
                            warn!("Bybit DepthSnapshot: symbol '{}' not in tracked list (have: {:?})",
                                  symbol, s.keys().collect::<Vec<_>>());
                        }
                    }
                    bybit::BybitMessage::DepthDelta { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            for level in &bids {
                                coin.bybit_book.update_bid(level.price, level.quantity);
                            }
                            for level in &asks {
                                coin.bybit_book.update_ask(level.price, level.quantity);
                            }
                            coin.bybit_book.timestamp_us = timestamp_us;

                            let (_raw, norm) = coin.mlofi_bybit.update(&coin.bybit_book);
                            push_bounded(&mut coin.mlofi_bybit_values, norm.abs());

                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            if let Some(mp) = microprice::calculate_microprice(&coin.bybit_book) {
                                coin.cross_corr.add_follower_price(timestamp_us, mp);
                            }

                            if let Some(div) = microprice::microprice_divergence_bps(
                                &coin.binance_book,
                                &coin.bybit_book,
                            ) {
                                push_bounded(&mut coin.microprice_divergences, div.abs());
                            }
                        } else {
                            warn!("Bybit DepthDelta: symbol '{}' not in tracked list", symbol);
                        }
                    }
                    bybit::BybitMessage::Trade(trade) => {
                        if let Some(coin) = s.get_mut(&trade.symbol) {
                            // TFI — NOW PROCESSED (was ignored before)
                            let tfi = coin.tfi_bybit.update(&trade);
                            push_bounded(&mut coin.tfi_bybit_values, tfi);

                            coin.trade_intensity_bybit.add_trade(
                                trade.timestamp_us,
                                trade.price,
                                trade.quantity,
                            );
                        } else {
                            warn!("Bybit Trade: symbol '{}' not in tracked list", trade.symbol);
                        }
                    }
                }
            }

            // Scan duration expired
            _ = tokio::time::sleep_until(deadline) => {
                info!("Scan duration reached. Generating final report...");
                break;
            }
        }
    }

    // ===== Generate Report =====
    let end_time = chrono::Utc::now();
    let s = state.lock().unwrap();

    let mut results: Vec<CoinMetrics> = Vec::new();

    for (symbol, coin) in s.iter() {
        let metrics = compute_coin_metrics(symbol, coin, &config);
        results.push(metrics);
    }

    // Sort by COS score descending
    results.sort_by(|a, b| b.cos_score.partial_cmp(&a.cos_score).unwrap());

    let passed = results.iter().filter(|r| r.rejection_reason.is_none()).count();

    let recommendation = if passed >= 3 {
        format!(
            "PROCEED — {} coins passed validation.\n\
             Primary: {}\n\
             Standby: {}, {}\n\
             Recommendation: Start Phase 1 with primary coin.",
            passed,
            results.first().map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(1).map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(2).map(|r| r.symbol.as_str()).unwrap_or("?"),
        )
    } else if passed >= 1 {
        format!(
            "PROCEED WITH CAUTION — Only {} coin(s) passed.\n\
             Consider running scan again at different time of day.",
            passed
        )
    } else {
        "PIVOT STRATEGY — No coins passed validation.\n\
         CEIFA may not be viable. Consider Funding Rate Arbitrage."
            .to_string()
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

    let text_report = report::generate_text_report(&scanner_report);
    println!("{}", text_report);

    let json_report = serde_json::to_string_pretty(&scanner_report)?;
    std::fs::create_dir_all("data")?;
    std::fs::write("data/scanner_report.json", &json_report)?;
    std::fs::write("data/scanner_report.txt", &text_report)?;

    info!("Report saved to data/scanner_report.json and data/scanner_report.txt");

    Ok(())
}

/// Compute all metrics for a coin from its accumulated state.
fn compute_coin_metrics(
    symbol: &str,
    coin: &CoinState,
    config: &ScannerConfig,
) -> CoinMetrics {
    // Lead-lag statistics with minimum sample requirement
    let (lag_cv, ll_count) = if coin.lead_lag_results.len() >= config.validation.min_lead_lag_samples {
        let lags: Vec<f64> = coin.lead_lag_results.iter().map(|(l, _)| l.abs()).collect();
        let avg_lag = lags.iter().sum::<f64>() / lags.len() as f64;

        let lag_std = if lags.len() > 1 {
            (lags.iter().map(|l| (l - avg_lag).powi(2)).sum::<f64>()
                / (lags.len() - 1) as f64)
                .sqrt()
        } else {
            0.0
        };
        let cv = if avg_lag > 0.0 { lag_std / avg_lag } else { 1.0 };
        (cv, coin.lead_lag_results.len())
    } else {
        (1.0, coin.lead_lag_results.len())
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

    // MLOFI signal strength
    let mlofi_bn_mean = vec_mean(&coin.mlofi_binance_values);
    let mlofi_bb_mean = vec_mean(&coin.mlofi_bybit_values);
    let mlofi_strength = (mlofi_bn_mean + mlofi_bb_mean) / 2.0;

    // TFI means
    let tfi_bn_mean = vec_mean(&coin.tfi_binance_values);
    let tfi_bb_mean = vec_mean(&coin.tfi_bybit_values);

    // TFI agreement ratio
    let min_len = coin.tfi_binance_values.len().min(coin.tfi_bybit_values.len());
    let tfi_agreement = if min_len > 0 {
        let sample_size = min_len.min(1000);
        let agree_count = coin.tfi_binance_values.iter().rev()
            .zip(coin.tfi_bybit_values.iter().rev())
            .take(sample_size)
            .filter(|(a, b)| {
                (a.is_sign_positive() && b.is_sign_positive())
                    || (a.is_sign_negative() && b.is_sign_negative())
            })
            .count();
        agree_count as f64 / sample_size as f64
    } else {
        0.5
    };

    // Microprice divergence
    let mp_div_mean = vec_mean(&coin.microprice_divergences);
    let mp_div_std = vec_std(&coin.microprice_divergences, mp_div_mean);

    // Depth in USD
    let mid = coin.bybit_book.mid_price()
        .or_else(|| coin.binance_book.mid_price())
        .unwrap_or(0.0);
    let bid_depth_usd = coin.bybit_book.bid_depth(5) * mid;
    let ask_depth_usd = coin.bybit_book.ask_depth(5) * mid;

    // Realized volatility
    let rv = coin.volatility_tracker.short_term_vol().unwrap_or(0.0);

    // Trade intensity (combined)
    let intensity = coin.trade_intensity_binance.long_intensity()
        + coin.trade_intensity_bybit.long_intensity();

    // Cross-correlation
    let lead_lag_result = coin.cross_corr.calculate(
        config.validation.min_lag_ms,
        config.validation.max_lag_ms,
        10.0,
    );

    cos::calculate_cos(
        symbol,
        &lead_lag_result,
        lag_cv,
        ll_count,
        coin.spread_tracker.mean(),
        bid_depth_usd,
        ask_depth_usd,
        obi_mean,
        obi_std,
        mlofi_strength,
        mlofi_bn_mean,
        mlofi_bb_mean,
        tfi_agreement,
        tfi_bn_mean,
        tfi_bb_mean,
        mp_div_mean,
        mp_div_std,
        rv,
        intensity,
        &config.validation,
    )
}

fn vec_mean(v: &VecDeque<f64>) -> f64 {
    if v.is_empty() {
        return 0.0;
    }
    v.iter().sum::<f64>() / v.len() as f64
}

fn vec_std(v: &VecDeque<f64>, mean: f64) -> f64 {
    if v.len() < 2 {
        return 0.0;
    }
    (v.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (v.len() - 1) as f64).sqrt()
}

/// Push a value to a bounded VecDeque, evicting oldest if full.
fn push_bounded(deque: &mut VecDeque<f64>, value: f64) {
    if deque.len() >= MAX_SIGNAL_WINDOW {
        deque.pop_front();
    }
    deque.push_back(value);
}
