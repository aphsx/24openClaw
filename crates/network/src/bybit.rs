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
    _ts: Option<u64>,  // milliseconds
}

#[derive(Debug, Deserialize)]
struct BybitOrderbookData {
    s: String,          // symbol
    b: Vec<[String; 2]>, // bids [[price, qty], ...]
    a: Vec<[String; 2]>, // asks
    _u: u64,             // update id
}

#[derive(Debug, Deserialize)]
struct BybitTradeItem {
    #[serde(rename = "T")]
    _timestamp: u64,     // milliseconds
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

    // ใช้ local time (เวลาเครื่องเรา) เพื่อให้ sync กับ Binance ได้แบบเป๊ะๆ ไม่มีปัญหาความเหลื่อมล้ำนาฬิกา
    let ts_us = chrono::Utc::now().timestamp_micros() as u64;

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
            let now_us = chrono::Utc::now().timestamp_micros() as u64;
            for t in trades {
                let _ = tx.send(BybitMessage::Trade(TradeEvent {
                    timestamp_us: now_us,
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
