use tradingclaw_common::types::OrderBook;

/// MLOFI Calculator
/// คำนวณ Multi-Level Order Flow Imbalance จาก LOB snapshots ต่อเนื่อง
pub struct MlofiCalculator {
    _lambda: f64,           // decay parameter (default 0.3)
    levels: usize,         // จำนวน levels (default 10)
    weights: Vec<f64>,     // pre-computed weights per level
    prev_bids: Vec<(f64, f64)>,  // previous (price, qty) per level
    prev_asks: Vec<(f64, f64)>,
    ewm_mean: f64,         // exponentially weighted mean
    ewm_var: f64,          // exponentially weighted variance
    ewm_alpha: f64,        // EWM smoothing factor
    count: u64,            // จำนวน updates
}

impl MlofiCalculator {
    pub fn new(lambda: f64, levels: usize, ewm_span: usize) -> Self {
        // Pre-compute exponential decay weights
        let raw_weights: Vec<f64> = (0..levels)
            .map(|n| (-lambda * (n + 1) as f64).exp())
            .collect();
        let sum: f64 = raw_weights.iter().sum();
        let weights: Vec<f64> = raw_weights.iter().map(|w| w / sum).collect();

        Self {
            _lambda: lambda,
            levels,
            weights,
            prev_bids: Vec::new(),
            prev_asks: Vec::new(),
            ewm_mean: 0.0,
            ewm_var: 1.0,
            ewm_alpha: 2.0 / (ewm_span as f64 + 1.0),
            count: 0,
        }
    }

    /// Update with new OrderBook snapshot
    /// Returns (raw_mlofi, normalized_mlofi)
    pub fn update(&mut self, book: &OrderBook) -> (f64, f64) {
        let bids = book.top_bids(self.levels);
        let asks = book.top_asks(self.levels);

        // Current levels as (price, qty)
        let curr_bids: Vec<(f64, f64)> = bids.iter().map(|l| (l.price, l.quantity)).collect();
        let curr_asks: Vec<(f64, f64)> = asks.iter().map(|l| (l.price, l.quantity)).collect();

        if self.prev_bids.is_empty() || self.prev_asks.is_empty() {
            // First update, store and return 0
            self.prev_bids = curr_bids;
            self.prev_asks = curr_asks;
            return (0.0, 0.0);
        }

        // Calculate OFI per level
        let mut mlofi_raw = 0.0;

        for n in 0..self.levels.min(curr_bids.len()).min(self.prev_bids.len()) {
            let (curr_p, curr_q) = curr_bids[n];
            let (prev_p, prev_q) = self.prev_bids[n];

            let delta_bid = if curr_p > prev_p {
                curr_q  // new higher bid = bullish
            } else if curr_p == prev_p {
                curr_q - prev_q  // same price, qty change
            } else {
                -prev_q  // bid dropped = bearish
            };

            mlofi_raw += self.weights[n] * delta_bid;
        }

        for n in 0..self.levels.min(curr_asks.len()).min(self.prev_asks.len()) {
            let (curr_p, curr_q) = curr_asks[n];
            let (prev_p, prev_q) = self.prev_asks[n];

            let delta_ask = if curr_p < prev_p {
                curr_q  // new lower ask = bearish (more selling pressure)
            } else if curr_p == prev_p {
                curr_q - prev_q
            } else {
                -prev_q  // ask moved up = bullish (sellers retreating)
            };

            // Subtract ask delta (OFI = bid_pressure - ask_pressure)
            mlofi_raw -= self.weights[n] * delta_ask;
        }

        // Store for next update
        self.prev_bids = curr_bids;
        self.prev_asks = curr_asks;

        // EWM normalization
        self.count += 1;
        self.ewm_mean = self.ewm_alpha * mlofi_raw + (1.0 - self.ewm_alpha) * self.ewm_mean;
        let diff = mlofi_raw - self.ewm_mean;
        self.ewm_var = self.ewm_alpha * diff * diff + (1.0 - self.ewm_alpha) * self.ewm_var;

        let sigma = self.ewm_var.sqrt().max(1e-10);
        let mlofi_norm = if self.count > 100 {
            mlofi_raw / sigma
        } else {
            0.0  // ยังไม่มีข้อมูลพอ normalize
        };

        (mlofi_raw, mlofi_norm)
    }
}
