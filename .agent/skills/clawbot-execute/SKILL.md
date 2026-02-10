---
description: Execute trading orders on Binance Futures with safety SL/TP
---

# ClawBot Execute Skill

## Purpose
Execute AI trading decisions on Binance Futures. Open/close positions, set leverage, and attach safety SL/TP orders.

## Steps

1. **Execute AI Actions**:
   ```python
   from src.execution.order_manager import OrderManager
   from src.data.binance_rest import BinanceREST
   
   client = BinanceREST()
   manager = OrderManager(client)
   trades = await manager.execute_actions(ai_actions, balance)
   ```

2. **For OPEN_LONG / OPEN_SHORT**:
   - Set leverage (20x)
   - Set margin type (ISOLATED)
   - Calculate quantity: `(margin × leverage) / price`
   - Place MARKET order
   - Attach safety SL (-8%) and TP (+15%)

3. **For CLOSE**:
   - Cancel existing SL/TP orders
   - Place MARKET close order (reduce_only)
   - Calculate realized PnL
   - Record commission from Binance

## Safety SL/TP
| Type | Default | Purpose |
|------|---------|---------|
| Stop Loss | -8% from entry | Prevent flash crash loss between cycles |
| Take Profit | +15% from entry | Capture large spike between cycles |

> AI still manages positions every 5 minutes — safety orders are fallback only

## Order Types
- `MARKET` — instant fill for open/close
- `STOP_MARKET` — safety stop loss
- `TAKE_PROFIT_MARKET` — safety take profit
