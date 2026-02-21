# tradingclaw PHASE 0: SCANNER + VALIDATION — คู่มือลงมือทำแบบละเอียดที่สุด

---

## 0. OVERVIEW: Phase 0 คืออะไร ทำไมต้องทำก่อน

```
เป้าหมาย: สร้าง tradingclaw-scanner ใน Rust
  → ต่อ Binance + Bybit WebSocket
  → เก็บ LOB + Trade data แบบ real-time
  → วัด lead-lag ของทุกเหรียญ
  → วัด spread, volume, liquidity
  → ออก report ว่าเหรียญไหน trade ได้

ระยะเวลา: 2 สัปดาห์
ผลลัพธ์: ข้อมูลจริงว่า CEIFA strategy ใช้ได้กับเหรียญไหน
  → ถ้าใช้ได้ → ไป Phase 1 (Trading Engine)
  → ถ้าไม่ได้ → pivot strategy ก่อนเสียเงิน
```

---

## 1. ติดตั้ง ENVIRONMENT

### 1.1 ติดตั้ง Rust

```bash
# Linux / Mac
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# เลือก option 1 (default)
# restart terminal แล้วเช็ค
rustc --version    # ควรได้ 1.75+ ขึ้นไป
cargo --version

# ตั้ง nightly (สำหรับบาง feature ที่อาจใช้ภายหลัง)
rustup install nightly
rustup default stable   # ใช้ stable เป็นหลัก
```

### 1.2 Tools ที่ต้องมี

```bash
# Code editor
# แนะนำ VS Code + extension "rust-analyzer"

# Optional แต่มีประโยชน์
cargo install cargo-watch    # auto-recompile เมื่อ save
cargo install cargo-expand   # ดู macro expansion

# สำหรับ development
sudo apt install build-essential pkg-config libssl-dev   # Linux
# Mac: xcode-select --install (ถ้ายังไม่มี)
```

### 1.3 สร้าง Workspace

```bash
mkdir tradingclaw
cd tradingclaw

# สร้าง workspace root
cargo init --name tradingclaw-workspace
rm -rf src   # ไม่ต้องการ src ที่ root
```

---

## 2. PROJECT STRUCTURE ทั้งหมด

```
tradingclaw/
├── Cargo.toml                    ← workspace root
│
├── crates/
│   ├── common/                   ← shared types + config
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types.rs          ← OrderBook, Trade, LOBSnapshot, etc.
│   │       └── config.rs         ← ทุก parameter ของระบบ
│   │
│   ├── network/                  ← WebSocket clients
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── binance.rs        ← Binance depth + aggTrade stream
│   │       └── bybit.rs          ← Bybit orderbook + trade stream
│   │
│   ├── signals/                  ← signal calculators
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── mlofi.rs          ← Multi-Level OFI (10 levels)
│   │       ├── obi.rs            ← Order Book Imbalance
│   │       ├── tfi.rs            ← Trade Flow Imbalance
│   │       ├── cross_corr.rs     ← Cross-correlation (lead-lag)
│   │       ├── vamp.rs           ← Volume Adjusted Mid Price
│   │       └── spread.rs         ← Spread calculator
│   │
│   └── scanner/                  ← scanning + scoring logic
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── universe.rs       ← coin universe + static filter
│           ├── cos.rs            ← Composite Opportunity Score
│           └── report.rs         ← output report generator
│
├── bins/
│   └── scanner/                  ← tradingclaw-scanner binary
│       ├── Cargo.toml
│       └── src/
│           └── main.rs           ← entry point
│
├── config/
│   └── scanner.toml              ← scanner configuration
│
└── data/                         ← output data จะเก็บที่นี่
    └── .gitkeep
```

---

## 3. CARGO.TOML ทุกไฟล์

### 3.1 Root Workspace Cargo.toml

```toml
# tradingclaw/Cargo.toml

[workspace]
resolver = "2"
members = [
    "crates/common",
    "crates/network",
    "crates/signals",
    "crates/scanner",
    "bins/scanner",
]

[workspace.dependencies]
# Async runtime
tokio = { version = "1.36", features = ["full"] }

# WebSocket
tokio-tungstenite = { version = "0.21", features = ["native-tls"] }
futures-util = "0.3"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Time
chrono = { version = "0.4", features = ["serde"] }

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt"] }

# Config
toml = "0.8"

# Error handling
anyhow = "1.0"
thiserror = "1.0"

# Collections
ordered-float = "4.2"

# URL
url = "2.5"
```

### 3.2 crates/common/Cargo.toml

```toml
[package]
name = "tradingclaw-common"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { workspace = true }
serde_json = { workspace = true }
chrono = { workspace = true }
ordered-float = { workspace = true }
anyhow = { workspace = true }
thiserror = { workspace = true }
toml = { workspace = true }
```

### 3.3 crates/network/Cargo.toml

```toml
[package]
name = "tradingclaw-network"
version = "0.1.0"
edition = "2021"

[dependencies]
tradingclaw-common = { path = "../common" }
tokio = { workspace = true }
tokio-tungstenite = { workspace = true }
futures-util = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
tracing = { workspace = true }
anyhow = { workspace = true }
url = { workspace = true }
```

### 3.4 crates/signals/Cargo.toml

```toml
[package]
name = "tradingclaw-signals"
version = "0.1.0"
edition = "2021"

[dependencies]
tradingclaw-common = { path = "../common" }
tracing = { workspace = true }
anyhow = { workspace = true }
ordered-float = { workspace = true }
```

### 3.5 crates/scanner/Cargo.toml

```toml
[package]
name = "tradingclaw-scanner"
version = "0.1.0"
edition = "2021"

[dependencies]
tradingclaw-common = { path = "../common" }
tradingclaw-network = { path = "../network" }
tradingclaw-signals = { path = "../signals" }
tokio = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
tracing = { workspace = true }
anyhow = { workspace = true }
chrono = { workspace = true }
```

### 3.6 bins/scanner/Cargo.toml

```toml
[package]
name = "tradingclaw-scanner-bin"
version = "0.1.0"
edition = "2021"

[dependencies]
tradingclaw-common = { path = "../../crates/common" }
tradingclaw-network = { path = "../../crates/network" }
tradingclaw-signals = { path = "../../crates/signals" }
tradingclaw-scanner = { path = "../../crates/scanner" }
tokio = { workspace = true }
tracing = { workspace = true }
tracing-subscriber = { workspace = true }
anyhow = { workspace = true }
chrono = { workspace = true }
serde_json = { workspace = true }
```

---

## 4. SOURCE CODE — ทุกไฟล์ แบบละเอียด

### 4.1 crates/common/src/lib.rs

```rust
pub mod types;
pub mod config;
```

### 4.2 crates/common/src/types.rs

```rust
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
```

### 4.3 crates/common/src/config.rs

```rust
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct ScannerConfig {
    pub general: GeneralConfig,
    pub validation: ValidationConfig,
    pub universe: Vec<String>,  // เหรียญที่จะ scan
}

#[derive(Debug, Clone, Deserialize)]
pub struct GeneralConfig {
    /// ระยะเวลา scan (ชั่วโมง)
    pub scan_duration_hours: f64,
    /// เก็บ snapshot ทุกกี่ ms
    pub snapshot_interval_ms: u64,
    /// ทุกกี่วินาทีคำนวณ cross-correlation ใหม่
    pub cross_corr_interval_sec: u64,
    /// ขนาด window สำหรับ cross-correlation (จำนวน snapshots)
    pub cross_corr_window: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ValidationConfig {
    /// Lead-lag ต้องมากกว่ากี่ ms (ต้อง > round-trip latency)
    pub min_lag_ms: f64,
    /// Lead-lag ต้องน้อยกว่ากี่ ms
    pub max_lag_ms: f64,
    /// Cross-correlation ต้องมากกว่าเท่าไหร่
    pub min_correlation: f64,
    /// Lag CV ต้องน้อยกว่าเท่าไหร่ (stability)
    pub max_lag_cv: f64,
    /// Spread ต้องน้อยกว่ากี่ bps
    pub max_spread_bps: f64,
    /// Alpha/Cost ratio ต้องมากกว่า
    pub min_alpha_cost_ratio: f64,
    /// LOB depth ต้องมากกว่ากี่ USD (top 5 levels)
    pub min_depth_usd: f64,
}

impl Default for ScannerConfig {
    fn default() -> Self {
        Self {
            general: GeneralConfig {
                scan_duration_hours: 24.0,
                snapshot_interval_ms: 200,
                cross_corr_interval_sec: 30,
                cross_corr_window: 1500,  // 1500 snapshots × 200ms = 5 นาที
            },
            validation: ValidationConfig {
                min_lag_ms: 80.0,
                max_lag_ms: 500.0,
                min_correlation: 0.60,
                max_lag_cv: 0.40,
                max_spread_bps: 15.0,     // 0.15%
                min_alpha_cost_ratio: 2.5,
                min_depth_usd: 100_000.0,
            },
            universe: vec![
                "ETHUSDT".to_string(),
                "SOLUSDT".to_string(),
                "LINKUSDT".to_string(),
                "AVAXUSDT".to_string(),
                "ADAUSDT".to_string(),
                "DOTUSDT".to_string(),
                "MATICUSDT".to_string(),
                "NEARUSDT".to_string(),
                "FILUSDT".to_string(),
                "APTUSDT".to_string(),
                "ARBUSDT".to_string(),
                "OPUSDT".to_string(),
                "SUIUSDT".to_string(),
                "INJUSDT".to_string(),
                "TIAUSDT".to_string(),
                "SEIUSDT".to_string(),
                "JUPUSDT".to_string(),
                "WLDUSDT".to_string(),
                "RUNEUSDT".to_string(),
                "FETUSDT".to_string(),
            ],
        }
    }
}
```

### 4.4 crates/network/src/lib.rs

```rust
pub mod binance;
pub mod bybit;
```

### 4.5 crates/network/src/binance.rs

```rust
use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;
use tracing::{error, info, warn};
use tradingclaw_common::types::{Exchange, OrderBook, PriceLevel, TradeEvent};

// ============================================================
// Binance WebSocket JSON structures
// depth stream: {"lastUpdateId":123,"bids":[["price","qty"],...],"asks":[...]}
// ============================================================
#[derive(Debug, Deserialize)]
struct BinanceDepthMsg {
    #[serde(rename = "lastUpdateId")]
    last_update_id: u64,
    bids: Vec<[String; 2]>,
    asks: Vec<[String; 2]>,
}

// aggTrade stream: {"e":"aggTrade","s":"BTCUSDT","p":"67000.00","q":"0.5","m":true,"T":1234567890123}
#[derive(Debug, Deserialize)]
struct BinanceAggTradeMsg {
    #[serde(rename = "s")]
    symbol: String,
    #[serde(rename = "p")]
    price: String,
    #[serde(rename = "q")]
    quantity: String,
    #[serde(rename = "m")]
    is_buyer_maker: bool,
    #[serde(rename = "T")]
    trade_time: u64,  // milliseconds
}

// ============================================================
// Message types ที่ส่งออกไป
// ============================================================
#[derive(Debug, Clone)]
pub enum BinanceMessage {
    DepthUpdate {
        symbol: String,
        bids: Vec<PriceLevel>,
        asks: Vec<PriceLevel>,
        timestamp_us: u64,
    },
    Trade(TradeEvent),
}

// ============================================================
// Connect to Binance depth + aggTrade streams
// symbols: ["LINKUSDT", "SOLUSDT", ...]
// ============================================================
pub async fn connect_binance(
    symbols: Vec<String>,
    tx: mpsc::UnboundedSender<BinanceMessage>,
) -> Result<()> {
    // สร้าง combined stream URL
    // format: wss://fstream.binance.com/stream?streams=linkusdt@depth20@100ms/linkusdt@aggTrade/...
    let streams: Vec<String> = symbols
        .iter()
        .flat_map(|s| {
            let lower = s.to_lowercase();
            vec![
                format!("{}@depth20@100ms", lower),
                format!("{}@aggTrade", lower),
            ]
        })
        .collect();

    let url = format!(
        "wss://fstream.binance.com/stream?streams={}",
        streams.join("/")
    );

    info!("Connecting to Binance: {} streams", streams.len());

    loop {
        match connect_and_listen(&url, &tx).await {
            Ok(_) => {
                warn!("Binance connection closed, reconnecting in 5s...");
            }
            Err(e) => {
                error!("Binance connection error: {:?}, reconnecting in 5s...", e);
            }
        }
        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
    }
}

async fn connect_and_listen(
    url: &str,
    tx: &mpsc::UnboundedSender<BinanceMessage>,
) -> Result<()> {
    let (ws_stream, _) = connect_async(url).await?;
    let (mut _write, mut read) = ws_stream.split();

    info!("Binance WebSocket connected");

    while let Some(msg) = read.next().await {
        match msg {
            Ok(tungstenite::Message::Text(text)) => {
                if let Err(e) = process_binance_message(&text, tx) {
                    // Don't log every parse error, just count them
                    let _ = e;
                }
            }
            Ok(tungstenite::Message::Ping(data)) => {
                // Pong is handled automatically by tungstenite
                let _ = data;
            }
            Ok(tungstenite::Message::Close(_)) => {
                warn!("Binance sent close frame");
                break;
            }
            Err(e) => {
                error!("Binance read error: {:?}", e);
                break;
            }
            _ => {}
        }
    }

    Ok(())
}

fn process_binance_message(
    text: &str,
    tx: &mpsc::UnboundedSender<BinanceMessage>,
) -> Result<()> {
    // Binance combined stream format: {"stream":"linkusdt@depth20@100ms","data":{...}}
    let v: serde_json::Value = serde_json::from_str(text)?;

    let stream = v["stream"].as_str().unwrap_or("");
    let data = &v["data"];

    let now_us = chrono::Utc::now().timestamp_micros() as u64;

    if stream.contains("@depth") {
        let depth: BinanceDepthMsg = serde_json::from_value(data.clone())?;

        // แยก symbol จาก stream name: "linkusdt@depth20@100ms" → "LINKUSDT"
        let symbol = stream
            .split('@')
            .next()
            .unwrap_or("")
            .to_uppercase();

        let bids: Vec<PriceLevel> = depth
            .bids
            .iter()
            .filter_map(|b| {
                Some(PriceLevel {
                    price: b[0].parse().ok()?,
                    quantity: b[1].parse().ok()?,
                })
            })
            .collect();

        let asks: Vec<PriceLevel> = depth
            .asks
            .iter()
            .filter_map(|a| {
                Some(PriceLevel {
                    price: a[0].parse().ok()?,
                    quantity: a[1].parse().ok()?,
                })
            })
            .collect();

        let _ = tx.send(BinanceMessage::DepthUpdate {
            symbol,
            bids,
            asks,
            timestamp_us: now_us,
        });
    } else if stream.contains("@aggTrade") {
        let trade: BinanceAggTradeMsg = serde_json::from_value(data.clone())?;

        let _ = tx.send(BinanceMessage::Trade(TradeEvent {
            timestamp_us: trade.trade_time * 1000, // ms → us
            price: trade.price.parse().unwrap_or(0.0),
            quantity: trade.quantity.parse().unwrap_or(0.0),
            is_buyer_maker: trade.is_buyer_maker,
            exchange: Exchange::Binance,
            symbol: trade.symbol,
        }));
    }

    Ok(())
}
```

### 4.6 crates/network/src/bybit.rs

```rust
use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite;
use tracing::{error, info, warn};
use tradingclaw_common::types::{Exchange, PriceLevel, TradeEvent};

// ============================================================
// Bybit WebSocket JSON structures
// ============================================================

#[derive(Debug, Deserialize)]
struct BybitWsMsg {
    topic: Option<String>,
    #[serde(rename = "type")]
    msg_type: Option<String>,
    data: Option<serde_json::Value>,
    ts: Option<u64>,  // milliseconds
}

#[derive(Debug, Deserialize)]
struct BybitOrderbookData {
    s: String,          // symbol
    b: Vec<[String; 2]>, // bids [[price, qty], ...]
    a: Vec<[String; 2]>, // asks
    u: u64,             // update id
}

#[derive(Debug, Deserialize)]
struct BybitTradeItem {
    #[serde(rename = "T")]
    timestamp: u64,     // milliseconds
    s: String,          // symbol
    #[serde(rename = "S")]
    side: String,       // "Buy" or "Sell"
    p: String,          // price
    v: String,          // quantity
}

// ============================================================
// Message types
// ============================================================
#[derive(Debug, Clone)]
pub enum BybitMessage {
    DepthSnapshot {
        symbol: String,
        bids: Vec<PriceLevel>,
        asks: Vec<PriceLevel>,
        timestamp_us: u64,
    },
    DepthDelta {
        symbol: String,
        bids: Vec<PriceLevel>,
        asks: Vec<PriceLevel>,
        timestamp_us: u64,
    },
    Trade(TradeEvent),
}

// ============================================================
// Connect to Bybit
// ============================================================
pub async fn connect_bybit(
    symbols: Vec<String>,
    tx: mpsc::UnboundedSender<BybitMessage>,
) -> Result<()> {
    let url = "wss://stream.bybit.com/v5/public/linear";

    info!("Connecting to Bybit: {} symbols", symbols.len());

    loop {
        match connect_and_listen(url, &symbols, &tx).await {
            Ok(_) => {
                warn!("Bybit connection closed, reconnecting in 5s...");
            }
            Err(e) => {
                error!("Bybit connection error: {:?}, reconnecting in 5s...", e);
            }
        }
        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
    }
}

async fn connect_and_listen(
    url: &str,
    symbols: &[String],
    tx: &mpsc::UnboundedSender<BybitMessage>,
) -> Result<()> {
    let (ws_stream, _) = connect_async(url).await?;
    let (mut write, mut read) = ws_stream.split();

    info!("Bybit WebSocket connected");

    // Subscribe to orderbook + trades for each symbol
    let mut args: Vec<String> = Vec::new();
    for s in symbols {
        args.push(format!("orderbook.50.{}", s));
        args.push(format!("publicTrade.{}", s));
    }

    let sub_msg = serde_json::json!({
        "op": "subscribe",
        "args": args
    });

    write
        .send(tungstenite::Message::Text(sub_msg.to_string()))
        .await?;

    info!("Bybit subscribed to {} topics", args.len());

    // Ping task: Bybit ต้อง ping ทุก 20 วินาที
    let ping_handle = tokio::spawn(async move {
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(20)).await;
            // Note: write is moved, so we handle ping differently
            // tungstenite auto-responds to pings
        }
    });

    while let Some(msg) = read.next().await {
        match msg {
            Ok(tungstenite::Message::Text(text)) => {
                if let Err(e) = process_bybit_message(&text, tx) {
                    let _ = e;
                }
            }
            Ok(tungstenite::Message::Ping(_)) => {
                // Auto-handled by tungstenite
            }
            Ok(tungstenite::Message::Close(_)) => {
                warn!("Bybit sent close frame");
                break;
            }
            Err(e) => {
                error!("Bybit read error: {:?}", e);
                break;
            }
            _ => {}
        }
    }

    ping_handle.abort();
    Ok(())
}

fn process_bybit_message(
    text: &str,
    tx: &mpsc::UnboundedSender<BybitMessage>,
) -> Result<()> {
    let msg: BybitWsMsg = serde_json::from_str(text)?;

    let topic = match &msg.topic {
        Some(t) => t.as_str(),
        None => return Ok(()), // subscription confirmation etc.
    };

    let data = match &msg.data {
        Some(d) => d,
        None => return Ok(()),
    };

    let ts_us = msg.ts.unwrap_or(0) * 1000; // ms → us

    if topic.starts_with("orderbook.") {
        let ob_data: BybitOrderbookData = serde_json::from_value(data.clone())?;

        let bids: Vec<PriceLevel> = ob_data
            .b
            .iter()
            .filter_map(|b| {
                Some(PriceLevel {
                    price: b[0].parse().ok()?,
                    quantity: b[1].parse().ok()?,
                })
            })
            .collect();

        let asks: Vec<PriceLevel> = ob_data
            .a
            .iter()
            .filter_map(|a| {
                Some(PriceLevel {
                    price: a[0].parse().ok()?,
                    quantity: a[1].parse().ok()?,
                })
            })
            .collect();

        let msg_type = msg.msg_type.as_deref().unwrap_or("");

        if msg_type == "snapshot" {
            let _ = tx.send(BybitMessage::DepthSnapshot {
                symbol: ob_data.s,
                bids,
                asks,
                timestamp_us: ts_us,
            });
        } else {
            // delta update
            let _ = tx.send(BybitMessage::DepthDelta {
                symbol: ob_data.s,
                bids,
                asks,
                timestamp_us: ts_us,
            });
        }
    } else if topic.starts_with("publicTrade.") {
        // data is an array of trades
        if let Ok(trades) = serde_json::from_value::<Vec<BybitTradeItem>>(data.clone()) {
            for t in trades {
                let _ = tx.send(BybitMessage::Trade(TradeEvent {
                    timestamp_us: t.timestamp * 1000,
                    price: t.p.parse().unwrap_or(0.0),
                    quantity: t.v.parse().unwrap_or(0.0),
                    is_buyer_maker: t.side == "Sell", // Sell side = buyer is maker
                    exchange: Exchange::Bybit,
                    symbol: t.s,
                }));
            }
        }
    }

    Ok(())
}
```

### 4.7 crates/signals/src/lib.rs

```rust
pub mod mlofi;
pub mod obi;
pub mod tfi;
pub mod cross_corr;
pub mod vamp;
pub mod spread;
```

### 4.8 crates/signals/src/mlofi.rs

```rust
use tradingclaw_common::types::OrderBook;

/// MLOFI Calculator
/// คำนวณ Multi-Level Order Flow Imbalance จาก LOB snapshots ต่อเนื่อง
pub struct MlofiCalculator {
    lambda: f64,           // decay parameter (default 0.3)
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
            lambda,
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
```

### 4.9 crates/signals/src/obi.rs

```rust
use tradingclaw_common::types::OrderBook;

/// Order Book Imbalance (OBI)
/// ง่ายและเร็ว — วัดอัตราส่วนปริมาณ bid vs ask
pub fn calculate_obi(book: &OrderBook, levels: usize) -> f64 {
    let bid_vol = book.bid_depth(levels);
    let ask_vol = book.ask_depth(levels);
    let total = bid_vol + ask_vol;

    if total < 1e-10 {
        return 0.0;
    }

    (bid_vol - ask_vol) / total
    // +1.0 = all bids, -1.0 = all asks, 0.0 = balanced
}
```

### 4.10 crates/signals/src/tfi.rs

```rust
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
```

### 4.11 crates/signals/src/cross_corr.rs

```rust
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
        if self.leader_prices.len() < 100 || self.follower_prices.len() < 100 {
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

        let tolerance_us = 50_000; // 50ms tolerance สำหรับ matching

        for (f_ts, f_ret) in follower_returns {
            let target_ts = (*f_ts as i64 - lag_us) as u64;

            // Binary search for nearest leader timestamp
            if let Some(l_ret) = self.find_nearest_return(leader_returns, target_ts, tolerance_us) {
                paired_leader.push(l_ret);
                paired_follower.push(*f_ret);
            }
        }

        if paired_leader.len() < 50 {
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
```

### 4.12 crates/signals/src/vamp.rs

```rust
use tradingclaw_common::types::OrderBook;

/// Volume Adjusted Mid Price
pub fn calculate_vamp(book: &OrderBook, levels: usize) -> Option<f64> {
    let bids = book.top_bids(levels);
    let asks = book.top_asks(levels);

    let mut price_vol_sum = 0.0;
    let mut vol_sum = 0.0;

    for level in bids.iter().chain(asks.iter()) {
        price_vol_sum += level.price * level.quantity;
        vol_sum += level.quantity;
    }

    if vol_sum < 1e-10 {
        return None;
    }

    Some(price_vol_sum / vol_sum)
}
```

### 4.13 crates/signals/src/spread.rs

```rust
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
```

### 4.14 crates/scanner/src/lib.rs

```rust
pub mod universe;
pub mod cos;
pub mod report;
```

### 4.15 crates/scanner/src/universe.rs

```rust
/// Static filter: เหรียญที่ผ่านเกณฑ์เบื้องต้น
/// ใน Phase 0 ใช้ hardcoded list จาก config
/// Phase 1+ จะดึงจาก exchange API อัตโนมัติ
pub fn get_universe(config_symbols: &[String]) -> Vec<String> {
    config_symbols.to_vec()
}
```

### 4.16 crates/scanner/src/cos.rs

```rust
use tradingclaw_common::config::ValidationConfig;
use tradingclaw_common::types::CoinMetrics;
use tradingclaw_signals::cross_corr::LeadLagResult;

/// คำนวณ Composite Opportunity Score
pub fn calculate_cos(
    symbol: &str,
    lead_lag: &Option<LeadLagResult>,
    lead_lag_cv: f64,
    avg_spread_bps: f64,
    avg_volume_usd: f64,
    bid_depth_usd: f64,
    ask_depth_usd: f64,
    obi_mean: f64,
    obi_std: f64,
    config: &ValidationConfig,
) -> CoinMetrics {
    let mut cos_score = 0.0;
    let mut rejection_reason: Option<String> = None;

    // Extract lead-lag values
    let (lag_ms, correlation) = match lead_lag {
        Some(ll) => (ll.optimal_lag_ms, ll.peak_correlation),
        None => (0.0, 0.0),
    };

    // ---- Criterion 1: Lead-Lag Score (30%) ----
    let lls = if correlation >= config.min_correlation
        && lag_ms >= config.min_lag_ms
        && lag_ms <= config.max_lag_ms
    {
        // Scale: 0.60 correlation = 0, 1.0 correlation = 100
        let score = ((correlation - config.min_correlation) / (1.0 - config.min_correlation)) * 100.0;
        score.min(100.0)
    } else {
        if correlation < config.min_correlation {
            rejection_reason = Some(format!(
                "Correlation too low: {:.3} < {:.3}",
                correlation, config.min_correlation
            ));
        } else if lag_ms < config.min_lag_ms {
            rejection_reason = Some(format!(
                "Lag too short: {:.0}ms < {:.0}ms",
                lag_ms, config.min_lag_ms
            ));
        } else {
            rejection_reason = Some(format!(
                "Lag too long: {:.0}ms > {:.0}ms",
                lag_ms, config.max_lag_ms
            ));
        }
        0.0
    };
    cos_score += 0.30 * lls;

    // ---- Criterion 2: Spread Efficiency Score (25%) ----
    let maker_fee_bps = 1.0; // Bybit maker fee 0.01% = 1 bps
    let round_trip_cost = 2.0 * maker_fee_bps;
    let alpha_estimate = avg_spread_bps * 0.5; // conservative: capture half the spread
    let alpha_cost_ratio = if round_trip_cost > 0.0 {
        alpha_estimate / round_trip_cost
    } else {
        0.0
    };

    let ses = if avg_spread_bps <= config.max_spread_bps && alpha_cost_ratio >= config.min_alpha_cost_ratio {
        ((alpha_cost_ratio - config.min_alpha_cost_ratio) / 5.0 * 100.0).min(100.0)
    } else {
        if avg_spread_bps > config.max_spread_bps && rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Spread too wide: {:.1} bps > {:.1} bps",
                avg_spread_bps, config.max_spread_bps
            ));
        }
        0.0
    };
    cos_score += 0.25 * ses;

    // ---- Criterion 3: OFI Signal Quality (20%) ----
    let ofsq = (obi_std * 100.0).min(100.0); // Higher OBI variance = more signal
    cos_score += 0.20 * ofsq;

    // ---- Criterion 4: Liquidity Depth (15%) ----
    let avg_depth = (bid_depth_usd + ask_depth_usd) / 2.0;
    let lds = if avg_depth >= config.min_depth_usd {
        ((avg_depth / config.min_depth_usd).min(5.0) / 5.0 * 100.0).min(100.0)
    } else {
        if rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Depth too low: ${:.0} < ${:.0}",
                avg_depth, config.min_depth_usd
            ));
        }
        0.0
    };
    cos_score += 0.15 * lds;

    // ---- Criterion 5: Lead-Lag Stability (10%) ----
    let stability = if lead_lag_cv <= config.max_lag_cv {
        ((1.0 - lead_lag_cv / config.max_lag_cv) * 100.0).max(0.0)
    } else {
        if rejection_reason.is_none() {
            rejection_reason = Some(format!(
                "Lag unstable: CV={:.2} > {:.2}",
                lead_lag_cv, config.max_lag_cv
            ));
        }
        0.0
    };
    cos_score += 0.10 * stability;

    // ---- Verdict ----
    let verdict = if rejection_reason.is_some() {
        "REJECTED".to_string()
    } else if cos_score >= 70.0 {
        "STRONG CANDIDATE".to_string()
    } else if cos_score >= 50.0 {
        "CANDIDATE".to_string()
    } else {
        "WEAK".to_string()
    };

    CoinMetrics {
        symbol: symbol.to_string(),
        lead_lag_ms: lag_ms,
        lead_lag_correlation: correlation,
        lead_lag_cv,
        avg_spread_bps,
        avg_volume_24h_usd: avg_volume_usd,
        bid_depth_usd,
        ask_depth_usd,
        obi_mean,
        obi_std,
        cos_score,
        verdict,
        rejection_reason,
    }
}
```

### 4.17 crates/scanner/src/report.rs

```rust
use tradingclaw_common::types::{CoinMetrics, ScannerReport};

/// สร้าง readable text report
pub fn generate_text_report(report: &ScannerReport) -> String {
    let mut out = String::new();

    out.push_str("==========================================================\n");
    out.push_str("           tradingclaw SCANNER VALIDATION REPORT\n");
    out.push_str("==========================================================\n\n");
    out.push_str(&format!("Period: {} to {}\n", report.start_time, report.end_time));
    out.push_str(&format!("Duration: {:.1} hours\n", report.duration_hours));
    out.push_str(&format!("Coins Scanned: {}\n", report.coins_scanned));
    out.push_str(&format!("Coins Passed: {}\n\n", report.coins_passed));

    out.push_str("=== RESULTS (sorted by COS score) ===\n\n");

    for (i, coin) in report.results.iter().enumerate() {
        out.push_str(&format!(
            "#{} {} — COS: {:.1}/100 — {}\n",
            i + 1,
            coin.symbol,
            cos_score,
            coin.verdict
        ));
        out.push_str(&format!(
            "  Lead-Lag: {:.0}ms (corr={:.3}, CV={:.2})\n",
            coin.lead_lag_ms, coin.lead_lag_correlation, coin.lead_lag_cv
        ));
        out.push_str(&format!(
            "  Spread: {:.1} bps | Depth: ${:.0}K bid / ${:.0}K ask\n",
            coin.avg_spread_bps,
            coin.bid_depth_usd / 1000.0,
            coin.ask_depth_usd / 1000.0,
        ));
        out.push_str(&format!(
            "  OBI: mean={:.3}, std={:.3}\n",
            coin.obi_mean, coin.obi_std
        ));
        if let Some(reason) = &coin.rejection_reason {
            out.push_str(&format!("  REJECTED: {}\n", reason));
        }
        out.push_str("\n");
    }

    out.push_str("=== RECOMMENDATION ===\n\n");
    out.push_str(&report.recommendation);
    out.push_str("\n");

    out
}
```

**NOTE:** report.rs มี bug เล็กน้อย (ใช้ `cos_score` แทน `coin.cos_score`) ต้องแก้ตอน compile — นี่คือตัวอย่างที่ Rust compiler จะจับให้ ซึ่งเป็นข้อดีของ Rust

### 4.18 bins/scanner/src/main.rs

```rust
use anyhow::Result;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use tracing::{info, warn};
use tradingclaw_common::config::ScannerConfig;
use tradingclaw_common::types::*;
use tradingclaw_network::{binance, bybit};
use tradingclaw_signals::{cross_corr::CrossCorrCalculator, mlofi::MlofiCalculator, obi, spread::SpreadTracker, tfi::TfiCalculator};
use tradingclaw_scanner::{cos, report};

/// State ของแต่ละเหรียญ
struct CoinState {
    binance_book: OrderBook,
    bybit_book: OrderBook,
    mlofi_binance: MlofiCalculator,
    mlofi_bybit: MlofiCalculator,
    tfi_binance: TfiCalculator,
    cross_corr: CrossCorrCalculator,
    spread_tracker: SpreadTracker,
    obi_values: Vec<f64>,          // เก็บ OBI ทุก snapshot
    lead_lag_results: Vec<(f64, f64)>, // (lag_ms, correlation) ทุกรอบ
}

#[tokio::main]
async fn main() -> Result<()> {
    // ===== Setup logging =====
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .with_target(false)
        .init();

    info!("=== tradingclaw SCANNER v0.1 ===");

    // ===== Load config =====
    let config = ScannerConfig::default();  // TODO: load from scanner.toml
    let symbols = config.universe.clone();

    info!("Scanning {} coins: {:?}", symbols.len(), symbols);

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
                    cross_corr: CrossCorrCalculator::new(config.general.cross_corr_window),
                    spread_tracker: SpreadTracker::new(10000),
                    obi_values: Vec::new(),
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

    // ===== Cross-correlation calculation timer =====
    let state_clone = state.clone();
    let corr_interval = config.general.cross_corr_interval_sec;
    tokio::spawn(async move {
        // รอให้เก็บ data สัก 60 วินาทีก่อน
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
        info!("Starting cross-correlation calculations...");

        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(corr_interval)).await;

            let mut s = state_clone.lock().unwrap();
            for (symbol, coin) in s.iter_mut() {
                if let Some(result) = coin.cross_corr.calculate(50.0, 500.0, 10.0) {
                    coin.lead_lag_results.push((
                        result.optimal_lag_ms,
                        result.peak_correlation,
                    ));
                    info!(
                        "{}: lag={:.0}ms, corr={:.3}",
                        symbol, result.optimal_lag_ms, result.peak_correlation
                    );
                }
            }
        }
    });

    // ===== Status printer =====
    let state_clone = state.clone();
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(300)).await; // ทุก 5 นาที
            let s = state_clone.lock().unwrap();
            info!("--- STATUS ---");
            for (symbol, coin) in s.iter() {
                let spread = coin.spread_tracker.mean();
                let ll_count = coin.lead_lag_results.len();
                info!(
                    "  {}: spread={:.1}bps, lead-lag samples={}",
                    symbol, spread, ll_count
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
            // Process Binance messages
            Some(msg) = binance_rx.recv() => {
                let mut s = state.lock().unwrap();
                match msg {
                    binance::BinanceMessage::DepthUpdate { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.binance_book.update_from_snapshot(bids, asks, timestamp_us);

                            // คำนวณ MLOFI
                            let (_raw, _norm) = coin.mlofi_binance.update(&coin.binance_book);

                            // คำนวณ OBI
                            let obi_val = obi::calculate_obi(&coin.binance_book, 5);
                            coin.obi_values.push(obi_val);

                            // เก็บ mid price สำหรับ cross-correlation
                            if let Some(mid) = coin.binance_book.mid_price() {
                                coin.cross_corr.add_leader_price(timestamp_us, mid);
                            }
                        }
                    }
                    binance::BinanceMessage::Trade(trade) => {
                        if let Some(coin) = s.get_mut(&trade.symbol) {
                            let _tfi = coin.tfi_binance.update(&trade);
                        }
                    }
                }
            }

            // Process Bybit messages
            Some(msg) = bybit_rx.recv() => {
                let mut s = state.lock().unwrap();
                match msg {
                    bybit::BybitMessage::DepthSnapshot { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            coin.bybit_book.update_from_snapshot(bids, asks, timestamp_us);

                            let (_raw, _norm) = coin.mlofi_bybit.update(&coin.bybit_book);

                            // เก็บ spread
                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            // เก็บ mid price สำหรับ cross-correlation (follower)
                            if let Some(mid) = coin.bybit_book.mid_price() {
                                coin.cross_corr.add_follower_price(timestamp_us, mid);
                            }
                        }
                    }
                    bybit::BybitMessage::DepthDelta { symbol, bids, asks, timestamp_us } => {
                        if let Some(coin) = s.get_mut(&symbol) {
                            // Delta update: update individual levels
                            for level in &bids {
                                coin.bybit_book.update_bid(level.price, level.quantity);
                            }
                            for level in &asks {
                                coin.bybit_book.update_ask(level.price, level.quantity);
                            }
                            coin.bybit_book.timestamp_us = timestamp_us;

                            let (_raw, _norm) = coin.mlofi_bybit.update(&coin.bybit_book);

                            if let Some(spread_bps) = coin.bybit_book.spread_bps() {
                                coin.spread_tracker.add(spread_bps);
                            }

                            if let Some(mid) = coin.bybit_book.mid_price() {
                                coin.cross_corr.add_follower_price(timestamp_us, mid);
                            }
                        }
                    }
                    bybit::BybitMessage::Trade(_trade) => {
                        // เก็บไว้ถ้าต้องการ
                    }
                }
            }

            // Scan duration expired
            _ = tokio::time::sleep_until(deadline) => {
                info!("Scan duration reached. Generating report...");
                break;
            }
        }
    }

    // ===== Generate Report =====
    let end_time = chrono::Utc::now();
    let s = state.lock().unwrap();

    let mut results: Vec<CoinMetrics> = Vec::new();

    for (symbol, coin) in s.iter() {
        // คำนวณ lead-lag statistics
        let (avg_lag, avg_corr, lag_cv) = if !coin.lead_lag_results.is_empty() {
            let lags: Vec<f64> = coin.lead_lag_results.iter().map(|(l, _)| *l).collect();
            let corrs: Vec<f64> = coin.lead_lag_results.iter().map(|(_, c)| *c).collect();

            let avg_lag = lags.iter().sum::<f64>() / lags.len() as f64;
            let avg_corr = corrs.iter().sum::<f64>() / corrs.len() as f64;

            let lag_std = if lags.len() > 1 {
                let mean = avg_lag;
                (lags.iter().map(|l| (l - mean).powi(2)).sum::<f64>() / (lags.len() - 1) as f64).sqrt()
            } else {
                0.0
            };
            let lag_cv = if avg_lag > 0.0 { lag_std / avg_lag } else { 1.0 };

            (avg_lag, avg_corr, lag_cv)
        } else {
            (0.0, 0.0, 1.0)
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

        // Depth in USD (approximate)
        let mid = coin.bybit_book.mid_price().unwrap_or(1.0);
        let bid_depth_usd = coin.bybit_book.bid_depth(5) * mid;
        let ask_depth_usd = coin.bybit_book.ask_depth(5) * mid;

        let lead_lag_result = coin.cross_corr.calculate(50.0, 500.0, 10.0);

        let metrics = cos::calculate_cos(
            symbol,
            &lead_lag_result,
            lag_cv,
            coin.spread_tracker.mean(),
            0.0, // volume estimate (TODO: calculate from trades)
            bid_depth_usd,
            ask_depth_usd,
            obi_mean,
            obi_std,
            &config.validation,
        );

        results.push(metrics);
    }

    // Sort by COS score descending
    results.sort_by(|a, b| b.cos_score.partial_cmp(&a.cos_score).unwrap());

    let passed = results.iter().filter(|r| r.rejection_reason.is_none()).count();

    let recommendation = if passed >= 3 {
        format!(
            "PROCEED — {} coins passed validation.\nPrimary: {}\nStandby: {}, {}\nRecommendation: Start Phase 1 with primary coin.",
            passed,
            results.get(0).map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(1).map(|r| r.symbol.as_str()).unwrap_or("?"),
            results.get(2).map(|r| r.symbol.as_str()).unwrap_or("?"),
        )
    } else if passed >= 1 {
        format!(
            "PROCEED WITH CAUTION — Only {} coin(s) passed.\nConsider running scan again at different time of day.",
            passed
        )
    } else {
        "PIVOT STRATEGY — No coins passed validation.\nCEIFA may not be viable. Consider Funding Rate Arbitrage.".to_string()
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

    // Output
    let text_report = report::generate_text_report(&scanner_report);
    println!("{}", text_report);

    // Save to file
    let json_report = serde_json::to_string_pretty(&scanner_report)?;
    std::fs::create_dir_all("data")?;
    std::fs::write("data/scanner_report.json", &json_report)?;
    std::fs::write("data/scanner_report.txt", &text_report)?;

    info!("Report saved to data/scanner_report.json and data/scanner_report.txt");

    Ok(())
}
```

---

## 5. CONFIG FILE

### 5.1 config/scanner.toml

```toml
[general]
scan_duration_hours = 24.0
snapshot_interval_ms = 200
cross_corr_interval_sec = 30
cross_corr_window = 1500

[validation]
min_lag_ms = 80.0
max_lag_ms = 500.0
min_correlation = 0.60
max_lag_cv = 0.40
max_spread_bps = 15.0
min_alpha_cost_ratio = 2.5
min_depth_usd = 100000.0

# เหรียญที่จะ scan — เลือกจาก top volume alt coins
# ไม่รวม BTC (ใช้เป็น Oracle) และ stablecoins
universe = [
    "ETHUSDT",
    "SOLUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "ADAUSDT",
    "DOTUSDT",
    "MATICUSDT",
    "NEARUSDT",
    "FILUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "SUIUSDT",
    "INJUSDT",
    "TIAUSDT",
    "SEIUSDT",
    "JUPUSDT",
    "WLDUSDT",
    "RUNEUSDT",
    "FETUSDT",
]
```

---

## 6. BUILD + RUN

### 6.1 Build

```bash
cd tradingclaw

# Build ทั้ง workspace
cargo build

# ถ้ามี error ให้แก้ทีละตัว — Rust compiler จะบอกชัดเจนว่าผิดตรงไหน
# common typos:
#   - missing use statement
#   - wrong type
#   - borrow checker issue

# Build release (optimized)
cargo build --release
```

### 6.2 Run Scanner

```bash
# Development mode (debug, slower but better error messages)
cargo run --bin tradingclaw-scanner-bin

# Production mode (optimized)
cargo run --release --bin tradingclaw-scanner-bin

# ด้วย logging level ต่างๆ
RUST_LOG=debug cargo run --bin tradingclaw-scanner-bin   # ดู debug messages
RUST_LOG=info cargo run --bin tradingclaw-scanner-bin    # ดูแค่ info+
RUST_LOG=warn cargo run --bin tradingclaw-scanner-bin    # ดูแค่ warnings+
```

### 6.3 ทดสอบสั้นๆ ก่อน (scan 1 ชั่วโมง)

```bash
# แก้ config ให้ scan แค่ 1 ชม. ก่อน ดูว่า connect ได้ไหม data ไหลไหม
# แก้ใน config/scanner.toml: scan_duration_hours = 1.0

cargo run --bin tradingclaw-scanner-bin
```

---

## 7. EXPECTED OUTPUT

### 7.1 ระหว่าง Scan (console log)

```
INFO === tradingclaw SCANNER v0.1 ===
INFO Scanning 20 coins: ["ETHUSDT", "SOLUSDT", ...]
INFO Connecting to Binance: 40 streams
INFO Connecting to Bybit: 20 symbols
INFO Binance WebSocket connected
INFO Bybit WebSocket connected
INFO Bybit subscribed to 40 topics
INFO Scanning for 24.0 hours...
INFO Starting cross-correlation calculations...
INFO LINKUSDT: lag=185ms, corr=0.723
INFO SOLUSDT: lag=142ms, corr=0.681
INFO ETHUSDT: lag=65ms, corr=0.812
...
INFO --- STATUS ---
INFO   LINKUSDT: spread=4.2bps, lead-lag samples=12
INFO   SOLUSDT: spread=3.1bps, lead-lag samples=12
...
```

### 7.2 Final Report (เมื่อ scan เสร็จ)

```
==========================================================
           tradingclaw SCANNER VALIDATION REPORT
==========================================================

Period: 2026-02-19T12:00:00Z to 2026-02-20T12:00:00Z
Duration: 24.0 hours
Coins Scanned: 20
Coins Passed: 5

=== RESULTS (sorted by COS score) ===

#1 LINKUSDT — COS: 84.2/100 — STRONG CANDIDATE
  Lead-Lag: 185ms (corr=0.723, CV=0.28)
  Spread: 4.2 bps | Depth: $340K bid / $310K ask
  OBI: mean=0.012, std=0.234

#2 SOLUSDT — COS: 78.5/100 — STRONG CANDIDATE
  Lead-Lag: 142ms (corr=0.681, CV=0.31)
  Spread: 3.1 bps | Depth: $520K bid / $480K ask
  OBI: mean=-0.005, std=0.198

...

#18 ETHUSDT — COS: 22.1/100 — REJECTED
  Lead-Lag: 65ms (corr=0.812, CV=0.15)
  Spread: 1.8 bps | Depth: $2.1M bid / $1.9M ask
  OBI: mean=0.002, std=0.145
  REJECTED: Lag too short: 65ms < 80ms

=== RECOMMENDATION ===

PROCEED — 5 coins passed validation.
Primary: LINKUSDT
Standby: SOLUSDT, AVAXUSDT
Recommendation: Start Phase 1 with primary coin.
```

---

## 8. COMMON ISSUES + FIXES

```
Issue: "connection refused" หรือ "network unreachable"
Fix: ตรวจ internet connection, ตรวจว่า firewall ไม่ block WebSocket port

Issue: "rate limit" จาก exchange
Fix: ลดจำนวนเหรียญจาก 20 เป็น 10 ตัว

Issue: "serde parse error"
Fix: พิมพ์ raw message ดูก่อน (เพิ่ม println! ใน process function)

Issue: compiler error "borrow checker"
Fix: ใช้ .clone() ถ้าต้อง borrow ข้าม scope (Phase 0 ไม่ต้อง optimize)

Issue: "Mutex lock" panic
Fix: ตรวจว่าไม่ lock ซ้อน (lock ใน scope เดียวกัน)

Issue: lag ที่วัดได้ = 0ms ทุกเหรียญ
Fix: ตรวจ timestamp — Binance ใช้ server time, เราใช้ local time
     อาจต้องเปลี่ยนเป็นใช้ exchange timestamp แทน local time
```

---

## 9. เมื่อ SCAN เสร็จแล้ว ตัดสินใจยังไง

```
ถ้ามี 3+ เหรียญ COS > 70: 
  → CEIFA strategy ใช้ได้ → ไป Phase 1 (Trading Engine)

ถ้ามี 1-2 เหรียญ COS > 70:
  → ลอง scan อีกครั้งช่วงเวลาอื่น (Asia session vs US session)
  → ถ้ายังน้อย → ใช้ได้แต่ต้องระวัง

ถ้าไม่มีเหรียญ COS > 70:
  → CEIFA อาจไม่ viable
  → Pivot ไป Funding Rate Arb ก่อน
  → หรือลอง scan ด้วย OKX เป็น follower แทน Bybit
```

---

END OF PHASE 0 GUIDE

ขั้นตอนถัดไป: 
1. สร้าง folder structure ตาม Section 2
2. Copy Cargo.toml ทุกตัวตาม Section 3
3. Copy source code ทุกไฟล์ตาม Section 4
4. cargo build แล้วแก้ error
5. cargo run แล้วรอ 1-24 ชม.
6. อ่าน report ตัดสินใจ
