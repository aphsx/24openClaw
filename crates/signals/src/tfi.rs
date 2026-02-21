use std::collections::VecDeque;
use tradingclaw_common::types::TradeEvent;

/// Trade Flow Imbalance (TFI)
/// วัดแรงกดจาก actual trades
pub struct TfiCalculator {
    window: usize,
    trades: VecDeque<(f64, bool)>, // (qty, is_buy)
}

impl TfiCalculator {
    pub fn new(window: usize) -> Self {
        Self {
            window,
            trades: VecDeque::with_capacity(window + 1),
        }
    }

    pub fn update(&mut self, trade: &TradeEvent) -> f64 {
        let is_buy = !trade.is_buyer_maker;
        self.trades.push_back((trade.quantity, is_buy));

        while self.trades.len() > self.window {
            self.trades.pop_front();
        }

        let mut buy_vol = 0.0;
        let mut sell_vol = 0.0;

        for (qty, is_b) in &self.trades {
            if *is_b {
                buy_vol += qty;
            } else {
                sell_vol += qty;
            }
        }

        let total = buy_vol + sell_vol;
        if total < 1e-10 {
            return 0.0;
        }

        (buy_vol - sell_vol) / total
    }
}
