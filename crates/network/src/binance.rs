use anyhow::Result;
use futures_util::StreamExt;
use serde::Deserialize;
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite};
use tracing::{error, info, warn};
use tradingclaw_common::types::{Exchange, PriceLevel, TradeEvent};

// ============================================================
// Binance WebSocket JSON structures
// depth stream: {"lastUpdateId":123,"bids":[["price","qty"],...],"asks":[...]}
// ============================================================
#[derive(Debug, Deserialize)]
struct BinanceDepthMsg {
    #[serde(rename = "lastUpdateId")]
    _last_update_id: u64,
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
