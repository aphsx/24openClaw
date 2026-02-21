# TradingClaw

[![Rust](https://img.shields.io/badge/Rust-1.75%2B-blue.svg)](https://www.rust-lang.org/)
[![Workspace](https://img.shields.io/badge/Workspace-TradingClaw-orange.svg)]()

**TradingClaw** is a high-performance cryptocurrency market microstructure scanning and validation system built in Rust. Currently in Phase 0, its primary goal is to gather real-time data from major exchanges like Binance and Bybit via WebSockets to compute key metrics that determine if a specific trading strategy (e.g., CEIFA) is viable for a given coin pair.

## Overview

The `tradingclaw-scanner` connects to Binance and Bybit WebSocket streams to collect real-time Limit Order Book (LOB) snapshots and aggregated trade data. It calculates quantitative trading metrics to validate strategy assumptions before moving to the initial Execution Engine phase.

Key functionalities:
- Real-time Order Book (LOB) & Trade data collection.
- Cross-correlation calculation to measure lead-lag effects between exchanges.
- Calculation of key metrics: Volume Adjusted Mid Price (VAMP), Spread, Order Book Imbalance (OBI), Trade Flow Imbalance (TFI), and Multi-Level Order Flow Imbalance (MLOFI).
- Generation of detailed reports on market liquidity, depth, and viability for trading strategies.

## Project Structure

The project is structured as a Rust Cargo Workspace containing multiple crates to maintain modularity:

```text
tradingclaw/
├── Cargo.toml                    # Workspace root
├── crates/
│   ├── common/                   # Shared types, configurations, and core data structures
│   ├── network/                  # WebSocket clients for Binance and Bybit streams
│   ├── signals/                  # Signal calculators (VAMP, OBI, TFI, MLOFI, Spread, Lead-lag)
│   └── scanner/                  # Main scanning logic, composite opportunity score (COS), and reports
├── bins/
│   └── scanner/                  # tradingclaw-scanner executable binary
├── config/                       # Configuration files (e.g., scanner.toml)
└── data/                         # Output data and generated reports
```

## Features

- **Multi-Exchange WebSocket:** Native TLS WebSocket connections to Binance combined streams and Bybit.
- **Microstructure Signals:** Highly optimized calculation of high-frequency trading signals.
- **Validation & Scoring:** Calculates a Composite Opportunity Score (COS) to output a verdict (e.g., "STRONG", "CANDIDATE", "REJECTED").
- **Asynchronous Architecture:** Utilizing `tokio` for massive concurrency and `tokio-tungstenite` for WebSocket connections.

## Requirements

- **Rust:** Version `1.75` or higher.
- **Build Tools:** `build-essential`, `pkg-config`, `libssl-dev` (Linux) / Xcode Command Line Tools (macOS) / appropriate build tools for Windows.

## Installation & Setup

1. **Install Rust:**
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```
   Ensure you have the latest stable version installed: `rustc --version`.

2. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd tradingclaw
   ```

3. **Build the Workspace:**
   ```bash
   cargo build --release
   ```

## Configuration

The main configuration file should be located at `config/scanner.toml`. You can configure scanning duration, snapshot intervals, validation thresholds, and the target universe of coins.

## Running the Scanner

To run the scanner and start gathering market data metrics:

```bash
cargo run --release --bin tradingclaw-scanner-bin
```

## Roadmap

- **Phase 0:** Market Scanner + Strategy Validation (Current focus)
  - Measuring lead-lag and gathering LOB metrics.
  - Ensuring the validity of the CEIFA strategy.
- **Phase 1:** Trading Engine implementation.
- **Phase 2:** Production deployment and live trading.

---

*Note: This system relies on high-frequency market data. Running it on servers closer to exchange endpoints (e.g., AWS Tokyo/AWS Singapore) will yield lower latency and more accurate cross-correlation measurements.*
