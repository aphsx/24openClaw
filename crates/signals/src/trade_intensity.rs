use std::collections::VecDeque;

/// Trade Intensity Tracker
/// Measures volume-weighted trade arrival rate in rolling windows.
/// Spikes indicate informed trader activity.
/// Uses ratio of short/long window as "urgency" signal.
pub struct TradeIntensityTracker {
    /// Recent trades: (timestamp_us, dollar_volume)
    trades: VecDeque<(u64, f64)>,
    /// Short window in microseconds (e.g., 5 seconds)
    short_window_us: u64,
    /// Long window in microseconds (e.g., 60 seconds)
    long_window_us: u64,
}

impl TradeIntensityTracker {
    /// Create tracker with short and long windows in seconds.
    pub fn new(short_window_sec: f64, long_window_sec: f64) -> Self {
        Self {
            trades: VecDeque::with_capacity(10000),
            short_window_us: (short_window_sec * 1_000_000.0) as u64,
            long_window_us: (long_window_sec * 1_000_000.0) as u64,
        }
    }

    /// Add a trade observation.
    pub fn add_trade(&mut self, timestamp_us: u64, price: f64, quantity: f64) {
        let dollar_vol = price * quantity;
        self.trades.push_back((timestamp_us, dollar_vol));

        // Prune trades older than long window
        let cutoff = timestamp_us.saturating_sub(self.long_window_us);
        while let Some(&(ts, _)) = self.trades.front() {
            if ts < cutoff {
                self.trades.pop_front();
            } else {
                break;
            }
        }
    }

    /// Dollar volume per second in the short window.
    pub fn short_intensity(&self) -> f64 {
        if self.trades.is_empty() {
            return 0.0;
        }
        let now = self.trades.back().unwrap().0;
        let cutoff = now.saturating_sub(self.short_window_us);
        let vol: f64 = self.trades.iter()
            .filter(|(ts, _)| *ts >= cutoff)
            .map(|(_, v)| v)
            .sum();
        vol / (self.short_window_us as f64 / 1_000_000.0)
    }

    /// Dollar volume per second in the long window.
    pub fn long_intensity(&self) -> f64 {
        if self.trades.is_empty() {
            return 0.0;
        }
        let vol: f64 = self.trades.iter().map(|(_, v)| v).sum();
        vol / (self.long_window_us as f64 / 1_000_000.0)
    }

    /// Urgency ratio = short_intensity / long_intensity.
    /// > 1.0 means trading is intensifying (possible informed activity).
    /// < 1.0 means trading is quieting down.
    pub fn urgency_ratio(&self) -> f64 {
        let long = self.long_intensity();
        if long < 1e-10 {
            return 1.0;
        }
        self.short_intensity() / long
    }

    /// Total number of trades in the long window.
    pub fn trade_count(&self) -> usize {
        self.trades.len()
    }
}
