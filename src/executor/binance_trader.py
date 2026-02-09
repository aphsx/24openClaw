"""
Binance Trade Executor
Executes trades on Binance Futures
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET

from src.utils.config import config
from src.utils.logger import logger


class BinanceTrader:
    """Executes trades on Binance Futures"""
    
    def __init__(self):
        self.client = Client(
            config.BINANCE_API_KEY,
            config.BINANCE_API_SECRET
        )
        self.default_leverage = config.DEFAULT_LEVERAGE
        self.default_margin = config.DEFAULT_MARGIN
        
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        try:
            loop = asyncio.get_event_loop()
            account = await loop.run_in_executor(
                None, self.client.futures_account_balance
            )
            
            # Find USDT balance
            usdt = next((a for a in account if a['asset'] == 'USDT'), None)
            
            if usdt:
                return {
                    "total": float(usdt['balance']),
                    "free": float(usdt['availableBalance']),
                    "used": float(usdt['balance']) - float(usdt['availableBalance'])
                }
            
            return {"total": 0, "free": 0, "used": 0}
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {"total": 0, "free": 0, "used": 0, "error": str(e)}
    
    async def get_positions(self) -> list:
        """Get all open positions"""
        try:
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(
                None, self.client.futures_position_information
            )
            
            # Filter for only open positions
            open_positions = []
            for pos in positions:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    entry = float(pos['entryPrice'])
                    mark = float(pos['markPrice'])
                    pnl = float(pos['unRealizedProfit'])
                    
                    # Calculate PnL percentage
                    if entry > 0:
                        if amt > 0:  # Long
                            pnl_pct = ((mark - entry) / entry) * 100
                        else:  # Short
                            pnl_pct = ((entry - mark) / entry) * 100
                    else:
                        pnl_pct = 0
                    
                    open_positions.append({
                        "symbol": pos['symbol'],
                        "side": "long" if amt > 0 else "short",
                        "positionAmt": abs(amt),
                        "entryPrice": entry,
                        "markPrice": mark,
                        "unrealizedPnl": pnl,
                        "percentage": pnl_pct,
                        "leverage": int(pos['leverage']),
                        "initialMargin": float(pos.get('initialMargin', 0))
                    })
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def execute_decision(self, decision: Dict) -> Dict[str, Any]:
        """Execute a single trading decision"""
        action = decision.get('action', '')
        symbol = decision.get('symbol', '')
        leverage = decision.get('leverage', self.default_leverage)
        margin = decision.get('margin', self.default_margin)
        
        result = {
            "action": action,
            "symbol": symbol,
            "success": False,
            "message": "",
            "order_id": None,
            "executed_at": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            if action == "OPEN_LONG":
                result = await self._open_position(symbol, "BUY", leverage, margin)
                result['action'] = action
                
            elif action == "OPEN_SHORT":
                result = await self._open_position(symbol, "SELL", leverage, margin)
                result['action'] = action
                
            elif action == "CLOSE":
                result = await self._close_position(symbol)
                result['action'] = action
                
            elif action == "HOLD":
                result['success'] = True
                result['message'] = "Position held, no action taken"
                
            else:
                result['message'] = f"Unknown action: {action}"
                
        except Exception as e:
            result['success'] = False
            result['message'] = str(e)
            logger.error(f"Execute failed: {e}")
        
        return result
    
    async def _open_position(
        self, 
        symbol: str, 
        side: str, 
        leverage: int,
        margin: float
    ) -> Dict[str, Any]:
        """Open a new position"""
        loop = asyncio.get_event_loop()
        
        try:
            # Set leverage
            await loop.run_in_executor(
                None,
                lambda: self.client.futures_change_leverage(
                    symbol=symbol, 
                    leverage=leverage
                )
            )
            
            # Get current price
            ticker = await loop.run_in_executor(
                None,
                lambda: self.client.futures_symbol_ticker(symbol=symbol)
            )
            price = float(ticker['price'])
            
            # Calculate quantity
            quantity = self._calculate_quantity(symbol, margin, leverage, price)
            
            if quantity <= 0:
                return {
                    "success": False,
                    "message": "Invalid quantity calculated",
                    "symbol": symbol
                }
            
            # Place market order
            order = await loop.run_in_executor(
                None,
                lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY if side == "BUY" else SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
            )
            
            logger.info(f"✅ Opened {side} {symbol}: qty={quantity}, price=${price:,.2f}")
            
            return {
                "success": True,
                "message": f"Opened {side} position",
                "symbol": symbol,
                "order_id": order.get('orderId'),
                "quantity": quantity,
                "price": price,
                "leverage": leverage,
                "margin": margin,
                "executed_at": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to open {side} {symbol}: {e}")
            return {
                "success": False,
                "message": str(e),
                "symbol": symbol
            }
    
    async def _close_position(self, symbol: str) -> Dict[str, Any]:
        """Close an existing position"""
        loop = asyncio.get_event_loop()
        
        try:
            # Get current position
            positions = await loop.run_in_executor(
                None, self.client.futures_position_information
            )
            
            sym_pos = next(
                (p for p in positions if p['symbol'] == symbol), 
                None
            )
            
            if not sym_pos:
                return {
                    "success": False,
                    "message": f"No position found for {symbol}",
                    "symbol": symbol
                }
            
            amt = float(sym_pos['positionAmt'])
            
            if amt == 0:
                return {
                    "success": False,
                    "message": f"No open position for {symbol}",
                    "symbol": symbol
                }
            
            # Determine close side
            close_side = SIDE_SELL if amt > 0 else SIDE_BUY
            close_qty = abs(amt)
            
            # Place market order to close
            order = await loop.run_in_executor(
                None,
                lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    type=ORDER_TYPE_MARKET,
                    quantity=close_qty,
                    reduceOnly=True
                )
            )
            
            pnl = float(sym_pos['unRealizedProfit'])
            entry = float(sym_pos['entryPrice'])
            
            logger.info(f"✅ Closed {symbol}: PnL=${pnl:,.4f}")
            
            return {
                "success": True,
                "message": "Position closed",
                "symbol": symbol,
                "order_id": order.get('orderId'),
                "closed_pnl": pnl,
                "entry_price": entry,
                "executed_at": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to close {symbol}: {e}")
            return {
                "success": False,
                "message": str(e),
                "symbol": symbol
            }
    
    def _calculate_quantity(
        self, 
        symbol: str, 
        margin: float, 
        leverage: int, 
        price: float
    ) -> float:
        """Calculate order quantity based on margin and leverage"""
        if price <= 0:
            return 0
        
        # Position value = margin * leverage
        position_value = margin * leverage
        
        # Raw quantity
        quantity = position_value / price
        
        # Round based on symbol (simplified - should use exchange info)
        if 'BTC' in symbol:
            quantity = round(quantity, 3)
        elif 'ETH' in symbol:
            quantity = round(quantity, 3)
        else:
            quantity = round(quantity, 1)
        
        return quantity
    
    async def execute_all(self, decisions: list) -> list:
        """Execute all trading decisions"""
        results = []
        
        for decision in decisions:
            if decision.get('action') in ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE']:
                result = await self.execute_decision(decision)
                results.append(result)
                
                # Small delay between orders
                await asyncio.sleep(0.5)
        
        return results


# Test
async def test_trader():
    """Test the trader (read-only)"""
    trader = BinanceTrader()
    
    print(f"\n{'='*50}")
    print("Binance Trader Test")
    print(f"{'='*50}")
    
    # Get balance
    balance = await trader.get_account_balance()
    print(f"\nBalance: ${balance.get('total', 0):,.2f} USDT")
    print(f"Available: ${balance.get('free', 0):,.2f} USDT")
    
    # Get positions
    positions = await trader.get_positions()
    print(f"\nOpen Positions: {len(positions)}")
    for pos in positions:
        print(f"  {pos['symbol']}: {pos['side'].upper()} | PnL: {pos['percentage']:+.2f}%")


if __name__ == "__main__":
    asyncio.run(test_trader())
