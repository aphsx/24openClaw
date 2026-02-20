use std::collections::VecDeque;

/// Spread Tracker: เก็บ rolling statistics ของ spread
pub struct SpreadTracker {
    spreads_bps: VecDeque<f64>,
    max_window: usize,
}

impl SpreadTracker {
    pub fn new(max_window: usize) -> Self {
        Self {
            spreads_bps: VecDeque::with_capacity(max_window),
            max_window,
        }
    }

    pub fn add(&mut self, spread_bps: f64) {
        self.spreads_bps.push_back(spread_bps);
        while self.spreads_bps.len() > self.max_window {
            self.spreads_bps.pop_front();
        }
    }

    pub fn mean(&self) -> f64 {
        if self.spreads_bps.is_empty() {
            return 0.0;
        }
        self.spreads_bps.iter().sum::<f64>() / self.spreads_bps.len() as f64
    }

    pub fn count(&self) -> usize {
        self.spreads_bps.len()
    }
}
