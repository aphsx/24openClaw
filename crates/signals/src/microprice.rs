use tradingclaw_common::types::OrderBook;

/// Microprice (Stoikov 2018)
/// Superior short-term price predictor vs simple mid-price.
/// Incorporates order book imbalance into the fair price estimate.
///
/// Formula: microprice = (ask * bid_qty + bid * ask_qty) / (bid_qty + ask_qty)
///
/// When bid_qty >> ask_qty, microprice shifts toward the ask (price likely to rise).
/// When ask_qty >> bid_qty, microprice shifts toward the bid (price likely to fall).
pub fn calculate_microprice(book: &OrderBook) -> Option<f64> {
    let best_bid = book.best_bid()?;
    let best_ask = book.best_ask()?;

    let total_qty = best_bid.quantity + best_ask.quantity;
    if total_qty < 1e-15 {
        return None;
    }

    Some(
        (best_ask.price * best_bid.quantity + best_bid.price * best_ask.quantity) / total_qty,
    )
}

/// Multi-level microprice: uses top N levels for a more robust estimate.
/// Weights each level's contribution by its proximity to the top of book.
pub fn calculate_multilevel_microprice(book: &OrderBook, levels: usize) -> Option<f64> {
    let bids = book.top_bids(levels);
    let asks = book.top_asks(levels);

    if bids.is_empty() || asks.is_empty() {
        return None;
    }

    // Weighted by inverse level distance (level 0 = weight 1.0, level 1 = 0.5, etc.)
    let mut weighted_bid_vol = 0.0;
    let mut weighted_ask_vol = 0.0;

    for (i, bid) in bids.iter().enumerate() {
        let w = 1.0 / (i as f64 + 1.0);
        weighted_bid_vol += bid.quantity * w;
    }
    for (i, ask) in asks.iter().enumerate() {
        let w = 1.0 / (i as f64 + 1.0);
        weighted_ask_vol += ask.quantity * w;
    }

    let total = weighted_bid_vol + weighted_ask_vol;
    if total < 1e-15 {
        return None;
    }

    let best_bid_price = bids[0].price;
    let best_ask_price = asks[0].price;

    Some(
        (best_ask_price * weighted_bid_vol + best_bid_price * weighted_ask_vol) / total,
    )
}

/// Calculate microprice divergence between two order books in basis points.
/// Positive = exchange A microprice > exchange B microprice.
pub fn microprice_divergence_bps(book_a: &OrderBook, book_b: &OrderBook) -> Option<f64> {
    let mp_a = calculate_microprice(book_a)?;
    let mp_b = calculate_microprice(book_b)?;

    let mid = (mp_a + mp_b) / 2.0;
    if mid < 1e-15 {
        return None;
    }

    Some((mp_a - mp_b) / mid * 10_000.0)
}
