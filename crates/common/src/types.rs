use ordered_float::OrderedFloat;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

// ============================================================
// Price Level: 1 ระดับของ LOB (ราคา + ปริมาณ)
// ============================================================
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct PriceLevel {
    pub price: f64,
    pub quantity: f64,
}

// ============================================================
// OrderBook: LOB ทั้งหมดของ 1 exchange 1 เหรียญ
// BTreeMap เรียงลำดับราคาอัตโนมัติ
// ============================================================
#[derive(Debug, Clone)]
pub struct OrderBook {
    // key = price (OrderedFloat เพื่อใช้ใน BTreeMap ได้)
    // value = quantity
    pub bids: BTreeMap<OrderedFloat<f64>, f64>,  // ซื้อ: เรียงจากสูงไปต่ำ
    pub asks: BTreeMap<OrderedFloat<f64>, f64>,  // ขาย: เรียงจากต่ำไปสูง
    pub timestamp_us: u64,                        // microseconds
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

    // Best bid = ราคาซื้อสูงสุด
    pub fn best_bid(&self) -> Option<PriceLevel> {
        self.bids.iter().next_back().map(|(p, q)| PriceLevel {
            price: p.into_inner(),
            quantity: *q,
        })
    }

    // Best ask = ราคาขายต่ำสุด
    pub fn best_ask(&self) -> Option<PriceLevel> {
        self.asks.iter().next().map(|(p, q)| PriceLevel {
            price: p.into_inner(),
            quantity: *q,
        })
    }

    // Mid price = (best_bid + best_ask) / 2
    pub fn mid_price(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => Some((bid.price + ask.price) / 2.0),
            _ => None,
        }
    }

    // Spread = best_ask - best_bid
    pub fn spread(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => Some(ask.price - bid.price),
            _ => None,
        }
    }

    // Spread เป็น % ของ mid price
    pub fn spread_bps(&self) -> Option<f64> {
        match (self.spread(), self.mid_price()) {
            (Some(spread), Some(mid)) if mid > 0.0 => Some(spread / mid * 10000.0),
            _ => None,
        }
    }

    // ดึง top N levels ของ bid
    pub fn top_bids(&self, n: usize) -> Vec<PriceLevel> {
        self.bids
            .iter()
            .rev()  // BTreeMap เรียงจากน้อยไปมาก, rev = มากไปน้อย
            .take(n)
            .map(|(p, q)| PriceLevel {
                price: p.into_inner(),
                quantity: *q,
            })
            .collect()
    }

    // ดึง top N levels ของ ask
    pub fn top_asks(&self, n: usize) -> Vec<PriceLevel> {
        self.asks
            .iter()  // BTreeMap เรียงจากน้อยไปมาก = ask ต่ำสุดมาก่อน
            .take(n)
            .map(|(p, q)| PriceLevel {
                price: p.into_inner(),
                quantity: *q,
            })
            .collect()
    }

    // Total volume ของ bid N levels
    pub fn bid_depth(&self, n: usize) -> f64 {
        self.bids.iter().rev().take(n).map(|(_, q)| q).sum()
    }

    // Total volume ของ ask N levels
    pub fn ask_depth(&self, n: usize) -> f64 {
        self.asks.iter().take(n).map(|(_, q)| q).sum()
    }

    // Update จาก snapshot (ลบทั้งหมด แล้วใส่ใหม่)
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
                self.bids
                    .insert(OrderedFloat(level.price), level.quantity);
            }
        }
        for level in asks {
            if level.quantity > 0.0 {
                self.asks
                    .insert(OrderedFloat(level.price), level.quantity);
            }
        }
        self.timestamp_us = timestamp_us;
    }

    // Update single level (qty=0 = ลบ level นั้น)
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
// Trade Event: 1 trade ที่เกิดขึ้น
// ============================================================
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeEvent {
    pub timestamp_us: u64,      // microseconds
    pub price: f64,
    pub quantity: f64,
    pub is_buyer_maker: bool,   // true = seller took, false = buyer took
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
// LOB Snapshot: ภาพถ่ายของ LOB ณ จุดเวลาหนึ่ง
// เก็บสำหรับ cross-correlation calculation
// ============================================================
#[derive(Debug, Clone)]
pub struct LOBSnapshot {
    pub timestamp_us: u64,
    pub mid_price: f64,
    pub spread_bps: f64,
    pub bid_depth_5: f64,    // total bid volume top 5 levels
    pub ask_depth_5: f64,    // total ask volume top 5 levels
    pub exchange: Exchange,
    pub symbol: String,
}

// ============================================================
// Coin Metrics: ผลลัพธ์การวิเคราะห์ 1 เหรียญ
// ============================================================
#[derive(Debug, Clone, Serialize)]
pub struct CoinMetrics {
    pub symbol: String,
    pub lead_lag_ms: f64,           // optimal lag ในหน่วย ms
    pub lead_lag_correlation: f64,  // peak cross-correlation
    pub lead_lag_cv: f64,           // coefficient of variation ของ lag
    pub avg_spread_bps: f64,        // average spread in basis points
    pub avg_volume_24h_usd: f64,    // estimated 24h volume in USD
    pub bid_depth_usd: f64,         // average bid depth 5 levels in USD
    pub ask_depth_usd: f64,         // average ask depth 5 levels in USD
    pub obi_mean: f64,              // mean Order Book Imbalance
    pub obi_std: f64,               // std of OBI (ยิ่งสูง = มี signal)
    pub cos_score: f64,             // Composite Opportunity Score (0-100)
    pub verdict: String,            // "STRONG", "CANDIDATE", "REJECTED"
    pub rejection_reason: Option<String>,
}

// ============================================================
// Scanner Report: ผลลัพธ์รวมของ scanner
// ============================================================
#[derive(Debug, Clone, Serialize)]
pub struct ScannerReport {
    pub start_time: String,
    pub end_time: String,
    pub duration_hours: f64,
    pub coins_scanned: usize,
    pub coins_passed: usize,
    pub results: Vec<CoinMetrics>,  // เรียงตาม COS score จากมากไปน้อย
    pub recommendation: String,
}
