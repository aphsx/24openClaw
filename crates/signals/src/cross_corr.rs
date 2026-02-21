use std::collections::VecDeque;

/// Cross-Correlation Calculator
/// Measures lead-lag between 2 exchanges with bidirectional detection.
/// Uses binary search for O(n log n) performance instead of O(n^2).
pub struct CrossCorrCalculator {
    /// Price snapshots from exchange A (e.g. Binance)
    leader_prices: VecDeque<(u64, f64)>,  // (timestamp_us, price)
    /// Price snapshots from exchange B (e.g. Bybit)
    follower_prices: VecDeque<(u64, f64)>,
    /// Max window size
    max_window: usize,
}

#[derive(Debug, Clone)]
pub struct LeadLagResult {
    /// Optimal lag in milliseconds (positive = A leads B, negative = B leads A)
    pub optimal_lag_ms: f64,
    /// Peak correlation at optimal lag
    pub peak_correlation: f64,
    /// All tested correlations: (lag_ms, correlation)
    pub all_correlations: Vec<(f64, f64)>,
    /// Which direction is dominant: "A_LEADS" or "B_LEADS"
    pub direction: String,
}

impl CrossCorrCalculator {
    pub fn new(max_window: usize) -> Self {
        Self {
            leader_prices: VecDeque::with_capacity(max_window),
            follower_prices: VecDeque::with_capacity(max_window),
            max_window,
        }
    }

    pub fn add_leader_price(&mut self, timestamp_us: u64, price: f64) {
        self.leader_prices.push_back((timestamp_us, price));
        while self.leader_prices.len() > self.max_window {
            self.leader_prices.pop_front();
        }
    }

    pub fn add_follower_price(&mut self, timestamp_us: u64, price: f64) {
        self.follower_prices.push_back((timestamp_us, price));
        while self.follower_prices.len() > self.max_window {
            self.follower_prices.pop_front();
        }
    }

    /// Compute cross-correlation at multiple lags, BIDIRECTIONALLY.
    /// Tests both A->B (positive lags) and B->A (negative lags).
    pub fn calculate(
        &self,
        min_lag_ms: f64,
        max_lag_ms: f64,
        step_ms: f64,
    ) -> Option<LeadLagResult> {
        if self.leader_prices.len() < 50 || self.follower_prices.len() < 50 {
            return None;
        }

        let leader_returns = Self::compute_returns(&self.leader_prices);
        let follower_returns = Self::compute_returns(&self.follower_prices);

        if leader_returns.len() < 20 || follower_returns.len() < 20 {
            return None;
        }

        let mut all_correlations = Vec::new();
        let mut best_lag = 0.0_f64;
        let mut best_corr = -2.0_f64;

        // ===== Forward direction: A leads B (positive lags) =====
        let mut lag_ms = min_lag_ms;
        while lag_ms <= max_lag_ms {
            let lag_us = (lag_ms * 1000.0) as i64;
            if let Some(c) = Self::compute_correlation_at_lag(
                &leader_returns,
                &follower_returns,
                lag_us,
            ) {
                all_correlations.push((lag_ms, c));
                if c > best_corr {
                    best_corr = c;
                    best_lag = lag_ms;
                }
            }
            lag_ms += step_ms;
        }

        // ===== Reverse direction: B leads A (negative lags) =====
        lag_ms = min_lag_ms;
        while lag_ms <= max_lag_ms {
            let lag_us = (lag_ms * 1000.0) as i64;
            if let Some(c) = Self::compute_correlation_at_lag(
                &follower_returns,
                &leader_returns,
                lag_us,
            ) {
                all_correlations.push((-lag_ms, c));
                if c > best_corr {
                    best_corr = c;
                    best_lag = -lag_ms;
                }
            }
            lag_ms += step_ms;
        }

        if all_correlations.is_empty() || best_corr < -1.0 {
            return None;
        }

        let direction = if best_lag >= 0.0 {
            "A_LEADS".to_string()
        } else {
            "B_LEADS".to_string()
        };

        Some(LeadLagResult {
            optimal_lag_ms: best_lag,
            peak_correlation: best_corr,
            all_correlations,
            direction,
        })
    }

    fn compute_returns(prices: &VecDeque<(u64, f64)>) -> Vec<(u64, f64)> {
        prices
            .iter()
            .zip(prices.iter().skip(1))
            .filter_map(|((_, p1), (t2, p2))| {
                if *p1 > 0.0 && *p2 > 0.0 {
                    Some((*t2, (*p2 / *p1).ln()))
                } else {
                    None
                }
            })
            .collect()
    }

    fn compute_correlation_at_lag(
        source_returns: &[(u64, f64)],
        target_returns: &[(u64, f64)],
        lag_us: i64,
    ) -> Option<f64> {
        let mut paired_source = Vec::new();
        let mut paired_target = Vec::new();

        let tolerance_us: u64 = 150_000; // 150ms tolerance

        for (t_ts, t_ret) in target_returns {
            let target_ts = (*t_ts as i64 - lag_us) as u64;

            if let Some(s_ret) = Self::binary_find_nearest(source_returns, target_ts, tolerance_us) {
                paired_source.push(s_ret);
                paired_target.push(*t_ret);
            }
        }

        if paired_source.len() < 20 {
            return None;
        }

        // Pearson correlation
        let n = paired_source.len() as f64;
        let mean_s: f64 = paired_source.iter().sum::<f64>() / n;
        let mean_t: f64 = paired_target.iter().sum::<f64>() / n;

        let mut cov = 0.0;
        let mut var_s = 0.0;
        let mut var_t = 0.0;

        for i in 0..paired_source.len() {
            let ds = paired_source[i] - mean_s;
            let dt = paired_target[i] - mean_t;
            cov += ds * dt;
            var_s += ds * ds;
            var_t += dt * dt;
        }

        let denom = (var_s * var_t).sqrt();
        if denom < 1e-15 {
            return None;
        }

        Some(cov / denom)
    }

    /// Binary search for nearest timestamp in a sorted array.
    fn binary_find_nearest(
        returns: &[(u64, f64)],
        target_ts: u64,
        tolerance_us: u64,
    ) -> Option<f64> {
        if returns.is_empty() {
            return None;
        }

        // Binary search for insertion point
        let mut lo = 0usize;
        let mut hi = returns.len();

        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            if returns[mid].0 < target_ts {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }

        // Check neighbors: lo-1 and lo
        let mut best_diff = u64::MAX;
        let mut best_ret = None;

        if lo > 0 {
            let diff = target_ts.saturating_sub(returns[lo - 1].0);
            if diff < best_diff {
                best_diff = diff;
                best_ret = Some(returns[lo - 1].1);
            }
        }

        if lo < returns.len() {
            let diff = returns[lo].0.saturating_sub(target_ts);
            if diff < best_diff {
                best_diff = diff;
                best_ret = Some(returns[lo].1);
            }
        }

        if best_diff <= tolerance_us {
            best_ret
        } else {
            None
        }
    }
}
