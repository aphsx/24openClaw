use ordered_float::OrderedFloat;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

// ============================================================
// Price Level: 1 level of LOB (price + quantity)
// ============================================================
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct PriceLevel {
    pub price: f64,
    pub quantity: f64,
}

// ============================================================
// OrderBook: Full LOB for 1 exchange 1 symbol
// ============================================================
#[derive(Debug, Clone)]
pub struct OrderBook {
    pub bids: BTreeMap<OrderedFloat<f64>, f64>,
    pub asks: BTreeMap<OrderedFloat<f64>, f64>,
    pub timestamp_us: u64,
    pub exchange: Exchange,
    pub symbol: String,
}

impl OrderBook {
    pub fn new(exchange: Exchange, symbol: String) -> Self {
        Self {
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
            timestamp_us: 0,
            exchange,
            symbol,
        }
    }

    pub fn best_bid(&self) -> Option<PriceLevel> {
        self.bids.iter().next_back().map(|(p, q)| PriceLevel {
            price: p.into_inner(),
            quantity: *q,
        })
    }

    pub fn best_ask(&self) -> Option<PriceLevel> {
        self.asks.iter().next().map(|(p, q)| PriceLevel {
            price: p.into_inner(),
            quantity: *q,
        })
    }

    pub fn mid_price(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => Some((bid.price + ask.price) / 2.0),
            _ => None,
        }
    }

    pub fn spread(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => Some(ask.price - bid.price),
            _ => None,
        }
    }

    pub fn spread_bps(&self) -> Option<f64> {
        match (self.spread(), self.mid_price()) {
            (Some(spread), Some(mid)) if mid > 0.0 => Some(spread / mid * 10000.0),
            _ => None,
        }
    }

    pub fn top_bids(&self, n: usize) -> Vec<PriceLevel> {
        self.bids
            .iter()
            .rev()
            .take(n)
            .map(|(p, q)| PriceLevel {
                price: p.into_inner(),
                quantity: *q,
            })
            .collect()
    }

    pub fn top_asks(&self, n: usize) -> Vec<PriceLevel> {
        self.asks
            .iter()
            .take(n)
            .map(|(p, q)| PriceLevel {
                price: p.into_inner(),
                quantity: *q,
            })
            .collect()
    }

    pub fn bid_depth(&self, n: usize) -> f64 {
        self.bids.iter().rev().take(n).map(|(_, q)| q).sum()
    }

    pub fn ask_depth(&self, n: usize) -> f64 {
        self.asks.iter().take(n).map(|(_, q)| q).sum()
    }

    pub fn update_from_snapshot(
        &mut self,
        bids: Vec<PriceLevel>,
        asks: Vec<PriceLevel>,
        timestamp_us: u64,
    ) {
        self.bids.clear();
        self.asks.clear();
        for level in bids {
            if level.quantity > 0.0 {
                self.bids.insert(OrderedFloat(level.price), level.quantity);
            }
        }
        for level in asks {
            if level.quantity > 0.0 {
                self.asks.insert(OrderedFloat(level.price), level.quantity);
            }
        }
        self.timestamp_us = timestamp_us;
    }

    pub fn update_bid(&mut self, price: f64, quantity: f64) {
        let key = OrderedFloat(price);
        if quantity <= 0.0 {
            self.bids.remove(&key);
        } else {
            self.bids.insert(key, quantity);
        }
    }

    pub fn update_ask(&mut self, price: f64, quantity: f64) {
        let key = OrderedFloat(price);
        if quantity <= 0.0 {
            self.asks.remove(&key);
        } else {
            self.asks.insert(key, quantity);
        }
    }
}

// ============================================================
// Trade Event
// ============================================================
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeEvent {
    pub timestamp_us: u64,
    pub price: f64,
    pub quantity: f64,
    pub is_buyer_maker: bool,
    pub exchange: Exchange,
    pub symbol: String,
}

// ============================================================
// Exchange enum
// ============================================================
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Exchange {
    Binance,
    Bybit,
    Okx,
}

impl std::fmt::Display for Exchange {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Exchange::Binance => write!(f, "Binance"),
            Exchange::Bybit => write!(f, "Bybit"),
            Exchange::Okx => write!(f, "OKX"),
        }
    }
}

// ============================================================
// LOB Snapshot
// ============================================================
#[derive(Debug, Clone)]
pub struct LOBSnapshot {
    pub timestamp_us: u64,
    pub mid_price: f64,
    pub spread_bps: f64,
    pub bid_depth_5: f64,
    pub ask_depth_5: f64,
    pub exchange: Exchange,
    pub symbol: String,
}

// ============================================================
// Coin Metrics: analysis result for 1 coin (expanded with all signals)
// ============================================================
#[derive(Debug, Clone, Serialize)]
pub struct CoinMetrics {
    pub symbol: String,

    // Lead-Lag
    pub lead_lag_ms: f64,
    pub lead_lag_correlation: f64,
    pub lead_lag_cv: f64,
    pub lead_lag_direction: String,

    // Spread
    pub avg_spread_bps: f64,

    // Volume
    pub avg_volume_24h_usd: f64,

    // Depth
    pub bid_depth_usd: f64,
    pub ask_depth_usd: f64,

    // OBI
    pub obi_mean: f64,
    pub obi_std: f64,

    // MLOFI
    pub mlofi_signal_strength: f64,
    pub mlofi_binance_mean: f64,
    pub mlofi_bybit_mean: f64,

    // TFI
    pub tfi_agreement_ratio: f64,
    pub tfi_binance_mean: f64,
    pub tfi_bybit_mean: f64,

    // Microprice
    pub microprice_divergence_mean_bps: f64,
    pub microprice_divergence_std_bps: f64,

    // Volatility
    pub realized_volatility: f64,

    // Trade Intensity
    pub trade_intensity_usd_per_sec: f64,

    // Scoring
    pub cos_score: f64,
    pub verdict: String,
    pub rejection_reason: Option<String>,
}

// ============================================================
// Scanner Report
// ============================================================
#[derive(Debug, Clone, Serialize)]
pub struct ScannerReport {
    pub start_time: String,
    pub end_time: String,
    pub duration_hours: f64,
    pub coins_scanned: usize,
    pub coins_passed: usize,
    pub results: Vec<CoinMetrics>,
    pub recommendation: String,
}
