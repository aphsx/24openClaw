use std::collections::VecDeque;

/// Realized Volatility Tracker
/// Rolling realized volatility using log returns.
/// Critical for dynamic threshold adjustment:
/// - High vol → wider profitable spreads but more risk
/// - Low vol → tighter spreads, need faster execution
pub struct VolatilityTracker {
    /// Recent prices for computing returns
    prices: VecDeque<(u64, f64)>, // (timestamp_us, price)
    /// Recent squared log returns
    squared_returns: VecDeque<f64>,
    /// Max window size for returns
    max_window: usize,
    /// Update interval assumed (microseconds) for annualization
    assumed_interval_us: f64,
}

impl VolatilityTracker {
    /// Create a new volatility tracker.
    /// `max_window`: number of returns to keep (e.g., 5000 = ~8 minutes at 100ms)
    pub fn new(max_window: usize) -> Self {
        Self {
            prices: VecDeque::with_capacity(max_window + 1),
            squared_returns: VecDeque::with_capacity(max_window),
            max_window,
            assumed_interval_us: 0.0,
        }
    }

    /// Add a new price observation.
    /// Returns the current realized volatility (annualized), or None if not enough data.
    pub fn update(&mut self, timestamp_us: u64, price: f64) -> Option<f64> {
        if let Some((_prev_ts, prev_price)) = self.prices.back() {
            if *prev_price > 0.0 && price > 0.0 {
                let log_ret = (price / prev_price).ln();
                self.squared_returns.push_back(log_ret * log_ret);

                while self.squared_returns.len() > self.max_window {
                    self.squared_returns.pop_front();
                }
            }
        }

        // Track interval for annualization
        if self.prices.len() >= 2 {
            let first_ts = self.prices.front().unwrap().0;
            let last_ts = timestamp_us;
            let n = self.prices.len() as f64;
            self.assumed_interval_us = (last_ts - first_ts) as f64 / n;
        }

        self.prices.push_back((timestamp_us, price));
        while self.prices.len() > self.max_window + 1 {
            self.prices.pop_front();
        }

        self.realized_volatility()
    }

    /// Current realized volatility (annualized).
    /// RV = sqrt(mean(r^2)) * sqrt(periods_per_year)
    pub fn realized_volatility(&self) -> Option<f64> {
        if self.squared_returns.len() < 30 {
            return None; // Need minimum sample
        }

        let n = self.squared_returns.len() as f64;
        let mean_sq_ret: f64 = self.squared_returns.iter().sum::<f64>() / n;

        // Annualize: assume crypto trades 365 days, 24 hours
        let seconds_per_year = 365.25 * 86400.0;
        let interval_sec = if self.assumed_interval_us > 0.0 {
            self.assumed_interval_us / 1_000_000.0
        } else {
            0.1 // default 100ms
        };

        let periods_per_year = seconds_per_year / interval_sec;
        let rv = mean_sq_ret.sqrt() * periods_per_year.sqrt();

        Some(rv)
    }

    /// Short-term volatility (not annualized, raw per-period stdev).
    /// Useful for comparing current vs historical vol.
    pub fn short_term_vol(&self) -> Option<f64> {
        if self.squared_returns.len() < 30 {
            return None;
        }
        let n = self.squared_returns.len() as f64;
        let mean_sq_ret: f64 = self.squared_returns.iter().sum::<f64>() / n;
        Some(mean_sq_ret.sqrt())
    }
}
