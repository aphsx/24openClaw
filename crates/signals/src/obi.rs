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
