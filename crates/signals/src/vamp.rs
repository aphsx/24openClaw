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
