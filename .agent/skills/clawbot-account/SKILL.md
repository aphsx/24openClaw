---
description: Fetch Binance account info, positions, and detect SL/TP triggers between cycles
---

# ClawBot Account Skill

## Purpose
Fetch account balance, open positions, and detect any SL/TP orders that triggered between cycles (during the 5 minutes the bot was inactive).

## Steps

1. **Get Balance & Positions**:
   ```python
   from src.data.binance_rest import BinanceREST
   from src.execution.position_tracker import PositionTracker
   
   client = BinanceREST()
   tracker = PositionTracker(client)
   positions, closed_between, balance, available = await tracker.update()
   ```

2. **Detect SL/TP Triggered Between Cycles**:
   - Compare current positions with last known positions
   - If a position disappeared → query Binance for order details
   - Determine close type: `STOP_LOSS`, `TAKE_PROFIT`, or `MARKET`
   - Record PnL and commission from Binance API

3. **Provide to AI**:
   ```python
   # Current positions (with unrealized PnL)
   positions = [{"symbol": "BTCUSDT", "side": "LONG", "unrealized_pnl_pct": 14.4, ...}]
   
   # Closed between cycles
   closed = [{"symbol": "ETHUSDT", "closed_by": "STOP_LOSS", "realized_pnl": -2.10, ...}]
   ```

## Important
- **Never skip a cycle** even if balance is low — still manage existing positions
- Positions can be closed by safety SL/TP between cycles
- All close details (PnL, fee, order ID) are fetched from Binance API
