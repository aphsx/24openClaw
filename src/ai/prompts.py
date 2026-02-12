"""
ClawBot AI — AI Prompt Templates
Structured prompts for OpenClaw AI trading decisions.
"""


SYSTEM_PROMPT = """คุณคือ ClawBot — AI Crypto Scalper ที่เทรด Binance Futures 20x leverage
คุณวิเคราะห์ข้อมูลทั้งหมดแล้วตัดสินใจว่าจะเทรดอะไร ทำเงินได้ทั้งขาขึ้น (LONG) และขาลง (SHORT)

## กฎการตัดสินใจ:
1. วิเคราะห์ indicators ทุก TF (5m/15m/1h/4h) + ข่าว + sentiment + positions ปัจจุบัน + Whale Data
2. Whale Data คือกุญแจสำคัญ:
   - Taker Buy/Sell Ratio > 1.1 = Bullish, < 0.9 = Bearish
   - Top Trader Long/Short > 1.2 = Bullish, < 0.8 = Bearish
   - Whale Walls = แนวรับ/ต้านสำคัญ ถ้าราคาใกล้ wall อาจจะเด้ง
3. ดู positions ที่เปิดอยู่:
   - กำไร >12-16% → ดูว่ายังไปต่อไหวไหม (RSI, volume, trend) ถ้าอ่อนตัว → ปิด
   - ขาดทุน → ดูว่าจะกลับไหม ถ้ากลับ → ถือ / ถ้าไม่กลับ → cut loss เอาทุนไปเล่นไม้ใหม่
   - AI ต้องกำหนด SL/TP เอง (ราคาจริง) อย่าให้ลึกเกินไป
4. เปิด position ใหม่ → check balance พอไหม + Whale confirm ไหม
5. ขนาด position ตาม risk_config ที่ให้มา
6. ไม่มี daily loss limit → ดูสถานการณ์เอง
7. Counter-trend (เช่น short ตอนตลาดขึ้นหมด) → ต้องมั่นใจมากจริงๆ ถ้าไม่มั่นใจ → ข้าม
8. Crypto ขึ้นลงพร้อมกัน → ถ้า BTC+ETH ขึ้นพร้อม = ดี ทิศเดียวกัน

## ตอบเป็น JSON เท่านั้น (ห้ามมี text อื่นนอก JSON):
{
  "market_view": "สรุปภาพรวมตลาดสั้นๆ (BTC bullish, whale accumulating...)",
  "actions": [
    {
      "symbol": "BTCUSDT",
      "action": "OPEN_LONG | OPEN_SHORT | CLOSE | HOLD | SKIP",
      "margin_usdt": 10,
      "sl_price": 97500,
      "tp_price": 99800,
      "reason": "EMA cross + taker buy ratio 1.35 + top traders 62% long"
    }
  ]
}

action types:
- OPEN_LONG: เปิด position ซื้อ (คาดว่าราคาจะขึ้น)
- OPEN_SHORT: เปิด position ขาย (คาดว่าราคาจะลง)
- CLOSE: ปิด position ที่เปิดอยู่
- HOLD: ถือ position ต่อ ไม่ทำอะไร
- SKIP: ไม่มี signal ชัด ข้ามเหรียญนี้"""


def build_cycle_prompt(ai_input: dict) -> str:
    """Build the main cycle prompt from structured data."""
    import json

    account = ai_input.get("account", {})
    coins = ai_input.get("coins", {})
    news = ai_input.get("news", [])
    fear_greed = ai_input.get("fear_greed", {})
    risk_config = ai_input.get("risk_config", {})

    # Format positions
    positions_text = "ไม่มี position เปิดอยู่"
    positions = account.get("positions", [])
    if positions:
        pos_lines = []
        for p in positions:
            pnl_pct = p.get("unrealized_pnl_pct", 0)
            emoji = "🟢" if pnl_pct >= 0 else "🔴"
            pos_lines.append(
                f"  {emoji} {p['symbol']} {p['side']} | entry:{p.get('entry_price',0)} "
                f"| now:{p.get('current_price',0)} | PnL: {pnl_pct:+.1f}% "
                f"| hold: {p.get('hold_duration_min',0)}min"
            )
        positions_text = "\n".join(pos_lines)

    # Format SL/TP triggered between cycles
    closed_text = ""
    closed = account.get("closed_since_last_cycle", [])
    if closed:
        closed_lines = ["⚠️ ปิดระหว่างรอบ:"]
        for c in closed:
            closed_lines.append(
                f"  {c['symbol']} {c['side']} closed_by:{c.get('closed_by','?')} "
                f"PnL:{c.get('realized_pnl',0):+.2f} USDT"
            )
        closed_text = "\n".join(closed_lines)

    # Format coins
    coins_text_parts = []
    for symbol, data in coins.items():
        ind_5m = data.get("indicators_5m", {})
        ind_15m = data.get("indicators_15m", {})
        ind_1h = data.get("indicators_1h", {})
        ind_4h = data.get("indicators_4h", {})
        regime = data.get("regime", "unknown")
        
        # Whale data
        whale = data.get("whale_activity", {})
        whale_text = ""
        if whale:
            walls = ", ".join(whale.get("whale_walls", [])[:2])
            whale_text = (f"Whale: TakerRatio={whale.get('taker_buy_sell_ratio', 0):.2f} "
                          f"| TopTraderLong={whale.get('top_trader_long_pct', 0):.1f}% "
                          f"| OI={whale.get('open_interest_usdt', 0)/1e6:.1f}M "
                          f"| Wall: {walls}")

        coins_text_parts.append(f"""
### {symbol} (regime: {regime})
Price: {data.get('price', 0)} | 5m: {data.get('price_change_5m_pct', 0):+.2f}% | 1h: {data.get('price_change_1h_pct', 0):+.2f}% | 24h: {data.get('price_change_24h_pct', 0):+.2f}%
Volume 24h: {data.get('volume_24h_usdt', 0):,.0f} USDT | Funding: {data.get('funding_rate', 0):.4f} | L/S: {data.get('long_short_ratio', 0):.2f}
{whale_text}
5m: EMA9={ind_5m.get('ema9',0)} EMA21={ind_5m.get('ema21',0)} EMA55={ind_5m.get('ema55',0)} RSI={ind_5m.get('rsi14',0)} ADX={ind_5m.get('adx',0)} MACD_hist={ind_5m.get('macd',{}).get('histogram',0)} StochRSI_K={ind_5m.get('stoch_rsi_k',0)} BB_width={ind_5m.get('bb',{}).get('width',0)} ATR%={ind_5m.get('atr14_pct',0)} VWAP={ind_5m.get('vwap',0)} OBV_trend={ind_5m.get('obv_trend','?')} Supertrend={ind_5m.get('supertrend',{}).get('direction','?')} VolRatio={ind_5m.get('volume_ratio',1)}
15m: EMA9={ind_15m.get('ema9',0)} EMA21={ind_15m.get('ema21',0)} RSI={ind_15m.get('rsi14',0)} ADX={ind_15m.get('adx',0)} MACD_hist={ind_15m.get('macd_histogram',0)}
1h: EMA9={ind_1h.get('ema9',0)} EMA21={ind_1h.get('ema21',0)} EMA200={ind_1h.get('ema200',0)} RSI={ind_1h.get('rsi14',0)} Supertrend={ind_1h.get('supertrend_dir','?')}
4h: EMA9={ind_4h.get('ema9',0)} EMA21={ind_4h.get('ema21',0)} RSI={ind_4h.get('rsi14',0)} Supertrend={ind_4h.get('supertrend_dir','?')}""")

    coins_text = "\n".join(coins_text_parts)

    # Format news
    news_text = "ไม่มีข่าว"
    if news:
        news_lines = []
        for n in news[:10]:
            desc = n.get('description', '')
            if len(desc) > 100:
                desc = desc[:100] + "..."
            news_lines.append(f"  [{n.get('source','?')}] {n.get('title','')} ({n.get('timestamp','')}) - {desc}")
        news_text = "\n".join(news_lines)

    prompt = f"""## Cycle: {ai_input.get('cycle_id', '')} | {ai_input.get('timestamp', '')}

## Account
Balance: {account.get('balance_usdt', 0):.2f} USDT | Available Margin: {account.get('available_margin', 0):.2f} USDT
Risk tier: {risk_config.get('balance_tier', '?')} → suggested {risk_config.get('suggested_risk_pct', '?')}% per trade | Min order: {risk_config.get('min_order_usdt', 5)} USDT

## Positions ปัจจุบัน
{positions_text}
{closed_text}

## เหรียญ (8 coins x 3 TF)
{coins_text}

## ข่าว (20 ล่าสุด)
{news_text}

## Fear & Greed Index: {fear_greed.get('value', 50)}/100 ({fear_greed.get('label', 'Neutral')})

วิเคราะห์ข้อมูลทั้งหมด แล้วตอบเป็น JSON ตาม format ที่กำหนด"""

    return prompt
