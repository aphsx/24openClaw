use std::collections::VecDeque;

/// Cross-Correlation Calculator
/// วัด lead-lag ระหว่าง 2 exchanges
pub struct CrossCorrCalculator {
    /// mid price snapshots จาก exchange A (leader, e.g. Binance)
    leader_prices: VecDeque<(u64, f64)>,  // (timestamp_us, mid_price)
    /// mid price snapshots จาก exchange B (follower, e.g. Bybit)
    follower_prices: VecDeque<(u64, f64)>,
    /// max window size
    max_window: usize,
}

#[derive(Debug, Clone)]
pub struct LeadLagResult {
    pub optimal_lag_ms: f64,
    pub peak_correlation: f64,
    pub all_correlations: Vec<(f64, f64)>,  // (lag_ms, correlation)
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

    /// คำนวณ cross-correlation ที่ lag ต่างๆ
    /// lag_range: ลองตั้งแต่ min_lag_ms ถึง max_lag_ms, step step_ms
    pub fn calculate(
        &self,
        min_lag_ms: f64,
        max_lag_ms: f64,
        step_ms: f64,
    ) -> Option<LeadLagResult> {
        // ลดเกณฑ์จาก 100 เหลือ 50 เพื่อรองรับเหรียญที่ LOB update ไม่บ่อย
        if self.leader_prices.len() < 50 || self.follower_prices.len() < 50 {
            return None; // ข้อมูลไม่พอ
        }

        // คำนวณ log returns ของ leader
        let leader_returns: Vec<(u64, f64)> = self.leader_prices
            .iter()
            .zip(self.leader_prices.iter().skip(1))
            .map(|((_, p1), (t2, p2))| (*t2, (p2 / p1).ln()))
            .collect();

        // คำนวณ log returns ของ follower
        let follower_returns: Vec<(u64, f64)> = self.follower_prices
            .iter()
            .zip(self.follower_prices.iter().skip(1))
            .map(|((_, p1), (t2, p2))| (*t2, (p2 / p1).ln()))
            .collect();

        if leader_returns.is_empty() || follower_returns.is_empty() {
            return None;
        }

        let mut all_correlations = Vec::new();
        let mut best_lag = 0.0_f64;
        let mut best_corr = -1.0_f64;

        // ทดสอบทุก lag
        let mut lag_ms = min_lag_ms;
        while lag_ms <= max_lag_ms {
            let lag_us = (lag_ms * 1000.0) as i64;

            // สำหรับแต่ละ follower return, หา leader return ที่ lag_us ก่อนหน้า
            let corr = self.compute_correlation_at_lag(
                &leader_returns,
                &follower_returns,
                lag_us,
            );

            if let Some(c) = corr {
                all_correlations.push((lag_ms, c));
                if c > best_corr {
                    best_corr = c;
                    best_lag = lag_ms;
                }
            }

            lag_ms += step_ms;
        }

        if all_correlations.is_empty() {
            return None;
        }

        Some(LeadLagResult {
            optimal_lag_ms: best_lag,
            peak_correlation: best_corr,
            all_correlations,
        })
    }

    fn compute_correlation_at_lag(
        &self,
        leader_returns: &[(u64, f64)],
        follower_returns: &[(u64, f64)],
        lag_us: i64,
    ) -> Option<f64> {
        // จับคู่: leader return ที่เวลา (t - lag) กับ follower return ที่เวลา t
        // ใช้ nearest timestamp matching

        let mut paired_leader = Vec::new();
        let mut paired_follower = Vec::new();

        let tolerance_us = 200_000; // เพิ่มเป็น 200ms เพื่อชดเชย network jitter

        for (f_ts, f_ret) in follower_returns {
            let target_ts = (*f_ts as i64 - lag_us) as u64;

            // Binary search for nearest leader timestamp
            if let Some(l_ret) = self.find_nearest_return(leader_returns, target_ts, tolerance_us) {
                paired_leader.push(l_ret);
                paired_follower.push(*f_ret);
            }
        }

        // ลดเกณฑ์จาก 50 เหลือ 20
        if paired_leader.len() < 20 {
            return None; // ข้อมูลจับคู่ไม่พอ
        }

        // Pearson correlation
        let n = paired_leader.len() as f64;
        let mean_l: f64 = paired_leader.iter().sum::<f64>() / n;
        let mean_f: f64 = paired_follower.iter().sum::<f64>() / n;

        let mut cov = 0.0;
        let mut var_l = 0.0;
        let mut var_f = 0.0;

        for i in 0..paired_leader.len() {
            let dl = paired_leader[i] - mean_l;
            let df = paired_follower[i] - mean_f;
            cov += dl * df;
            var_l += dl * dl;
            var_f += df * df;
        }

        let denom = (var_l * var_f).sqrt();
        if denom < 1e-15 {
            return None;
        }

        Some(cov / denom)
    }

    fn find_nearest_return(
        &self,
        returns: &[(u64, f64)],
        target_ts: u64,
        tolerance_us: u64,
    ) -> Option<f64> {
        // Simple linear search (สำหรับ Phase 0 พอแล้ว)
        // Phase 1+ เปลี่ยนเป็น binary search
        let mut best_diff = u64::MAX;
        let mut best_ret = None;

        for (ts, ret) in returns {
            let diff = if *ts > target_ts {
                *ts - target_ts
            } else {
                target_ts - *ts
            };

            if diff < best_diff {
                best_diff = diff;
                best_ret = Some(*ret);
            }
        }

        if best_diff <= tolerance_us {
            best_ret
        } else {
            None
        }
    }
}
