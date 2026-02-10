"""
Supabase Client
Handles all database operations
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from supabase import create_client, Client

from src.utils.config import config
from src.utils.logger import logger


class SupabaseClient:
    """Database client for Supabase"""
    
    def __init__(self):
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            self.client: Client = create_client(
                config.SUPABASE_URL,
                config.SUPABASE_KEY
            )
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning("Supabase not configured, running without database")
    
    # ==========================================
    # TRADING CYCLES
    # ==========================================
    
    async def create_cycle(self, cycle_id: str) -> Optional[Dict]:
        """Create new trading cycle record"""
        if not self.enabled:
            return None
            
        try:
            data = {
                "id": cycle_id,
                "started_at": datetime.utcnow().isoformat(),
                "status": "RUNNING"
            }
            
            result = self.client.table("trading_cycles").insert(data).execute()
            logger.debug(f"Created cycle: {cycle_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to create cycle: {e}")
            return None
    
    async def complete_cycle(
        self, 
        cycle_id: str, 
        status: str = "COMPLETED",
        summary: Dict = None
    ) -> Optional[Dict]:
        """Mark cycle as completed with expanded data"""
        if not self.enabled:
            return None
            
        try:
            data = {
                "completed_at": datetime.utcnow().isoformat(),
                "status": status,
                "decisions_count": summary.get('decisions_count', 0) if summary else 0,
                "trades_executed": summary.get('trades_executed', 0) if summary else 0,
                "ai_model": summary.get('ai_model') if summary else None,
                "ai_confidence": summary.get('ai_confidence') if summary else None,
                "market_outlook": summary.get('market_outlook') if summary else None,
                "total_cycle_ms": summary.get('total_cycle_ms') if summary else None,
                "balance_usdt": summary.get('balance_usdt') if summary else None,
                "available_margin": summary.get('available_margin') if summary else None,
                "open_positions_count": summary.get('open_positions_count', 0) if summary else 0,
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            result = self.client.table("trading_cycles")\
                .update(data)\
                .eq("id", cycle_id)\
                .execute()
                
            logger.debug(f"Completed cycle: {cycle_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to complete cycle: {e}")
            return None
    
    # ==========================================
    # RAW DATA STORAGE
    # ==========================================
    
    async def store_raw_binance(self, cycle_id: str, data: Dict) -> bool:
        """Store raw Binance data"""
        return await self._store_data("raw_binance_data", cycle_id, data)
    
    async def store_raw_news(self, cycle_id: str, data: Dict) -> bool:
        """Store raw news data"""
        return await self._store_data("raw_news_data", cycle_id, data)
    
    async def store_raw_onchain(self, cycle_id: str, data: Dict) -> bool:
        """Store raw on-chain data"""
        return await self._store_data("raw_onchain_data", cycle_id, data)
    
    # ==========================================
    # PROCESSED DATA STORAGE
    # ==========================================
    
    async def store_processed_technical(self, cycle_id: str, data: Dict) -> bool:
        """Store processed technical data"""
        return await self._store_data("processed_technical", cycle_id, data)
    
    async def store_processed_sentiment(self, cycle_id: str, data: Dict) -> bool:
        """Store processed sentiment data"""
        return await self._store_data("processed_sentiment", cycle_id, data)
    
    async def store_aggregated_data(self, cycle_id: str, data: Dict) -> bool:
        """Store aggregated data"""
        return await self._store_data("aggregated_data", cycle_id, data)
    
    # ==========================================
    # AI DECISIONS
    # ==========================================
    
    async def store_ai_decision(self, cycle_id: str, decision: Dict) -> bool:
        """Store AI decision"""
        if not self.enabled:
            return False
            
        try:
            data = {
                "cycle_id": cycle_id,
                "ai_model": decision.get('ai_model', 'unknown'),
                "confidence_score": decision.get('confidence', 0),
                "market_assessment": decision.get('analysis', {}).get('market_assessment', ''),
                "decisions_json": json.dumps(decision.get('decisions', [])),
                "raw_response": json.dumps(decision),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.client.table("ai_decisions").insert(data).execute()
            logger.debug(f"Stored AI decision for cycle: {cycle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store AI decision: {e}")
            return False
    
    # ==========================================
    # TRADES
    # ==========================================
    
    async def store_trade(
        self, 
        cycle_id: str, 
        action: str,
        symbol: str,
        result: Dict,
        reasoning: str = ""
    ) -> bool:
        """Store executed trade with fees and PnL details"""
        if not self.enabled:
            return False
            
        try:
            data = {
                "symbol": symbol,
                "side": "LONG" if action == "OPEN_LONG" else "SHORT" if action == "OPEN_SHORT" else "CLOSE",
                "leverage": result.get('leverage', 0),
                "margin_usdt": result.get('margin', 0),
                "status": "OPEN" if action in ('OPEN_LONG', 'OPEN_SHORT') else "CLOSED",
            }
            
            if action in ('OPEN_LONG', 'OPEN_SHORT'):
                data.update({
                    "cycle_id_open": cycle_id,
                    "entry_price": result.get('avg_price') or result.get('price', 0),
                    "entry_qty": result.get('executed_qty') or result.get('quantity', 0),
                    "entry_value": result.get('cum_quote', 0),
                    "order_id_open": result.get('order_id'),
                    "commission_open": result.get('commission', 0),
                    "commission_asset": result.get('commission_asset', 'USDT'),
                    "reasoning_open": reasoning[:500],
                    "opened_at": result.get('executed_at', datetime.utcnow().isoformat()),
                })
            elif action == 'CLOSE':
                data.update({
                    "cycle_id_close": cycle_id,
                    "exit_price": result.get('avg_price') or result.get('exit_price', 0),
                    "exit_qty": result.get('executed_qty') or result.get('quantity', 0),
                    "exit_value": result.get('cum_quote', 0),
                    "order_id_close": result.get('order_id'),
                    "commission_close": result.get('commission', 0),
                    "gross_pnl": result.get('closed_pnl', 0),
                    "reasoning_close": reasoning[:500],
                    "closed_at": result.get('executed_at', datetime.utcnow().isoformat()),
                    "is_winner": (result.get('closed_pnl', 0) or 0) > 0,
                })
                # Calculate net PnL
                gross = result.get('closed_pnl', 0) or 0
                commission = result.get('commission', 0) or 0
                net = gross - commission
                data['net_pnl'] = net
                margin = result.get('margin', 0)
                data['roi_on_margin'] = (net / margin * 100) if margin > 0 else 0
                data['is_winner'] = net > 0
            
            self.client.table("trades").insert(data).execute()
            logger.debug(f"Stored trade: {action} {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store trade: {e}")
            return False
    
    # ==========================================
    # MARKET SNAPSHOTS
    # ==========================================
    
    async def store_market_snapshot(
        self, 
        cycle_id: str, 
        market_data: Dict[str, Any]
    ) -> bool:
        """Store per-coin market data from aggregator output"""
        if not self.enabled:
            return False
            
        try:
            records = []
            for symbol, data in market_data.items():
                tech = data.get('technical', {})
                ls = data.get('long_short_ratio', {})
                
                record = {
                    "cycle_id": cycle_id,
                    "symbol": symbol,
                    "current_price": data.get('price', 0),
                    # EMAs
                    "ema9": tech.get('ema_9'),
                    "ema21": tech.get('ema_21'),
                    "ema20": tech.get('ema_20'),
                    "ema50": tech.get('ema_50'),
                    "ema55": tech.get('ema_55'),
                    "ema200": tech.get('ema_200'),
                    # RSI
                    "rsi": tech.get('rsi_14'),
                    "rsi_7": tech.get('rsi_7'),
                    "rsi_ema": tech.get('rsi_ema'),
                    # MACD
                    "macd": tech.get('macd_line'),
                    "macd_signal": tech.get('macd_signal'),
                    "macd_histogram": tech.get('macd_histogram'),
                    # ATR
                    "atr": tech.get('atr_14'),
                    "atr_percent": tech.get('atr_percent'),
                    "volatility": tech.get('volatility'),
                    # Bollinger
                    "bb_upper": tech.get('bollinger', {}).get('upper'),
                    "bb_middle": tech.get('bollinger', {}).get('middle'),
                    "bb_lower": tech.get('bollinger', {}).get('lower'),
                    # Price range
                    "recent_high": tech.get('recent_high'),
                    "recent_low": tech.get('recent_low'),
                    "day_high": tech.get('day_high'),
                    "day_low": tech.get('day_low'),
                    # Volume
                    "volume_24h": data.get('volume_24h'),
                    "quote_volume_24h": data.get('quote_volume_24h'),
                    "volume_ratio": tech.get('volume_ratio'),
                    "price_change_24h": data.get('price_change_24h'),
                    # Futures
                    "funding_rate": data.get('funding_rate'),
                    "long_ratio": ls.get('long_ratio'),
                    "short_ratio": ls.get('short_ratio'),
                    "long_short_ratio": ls.get('long_short_ratio'),
                    # Signals
                    "trend": tech.get('trend'),
                    "momentum": tech.get('momentum'),
                    "combined_score": data.get('combined_score'),
                    "combined_signal": data.get('combined_signal'),
                    "signal_agreement": data.get('signal_agreement'),
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                # Remove None values to avoid DB errors
                record = {k: v for k, v in record.items() if v is not None}
                records.append(record)
            
            if records:
                self.client.table("market_snapshots").insert(records).execute()
                logger.debug(f"Stored {len(records)} market snapshots for cycle: {cycle_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store market snapshots: {e}")
            return False
    
    # ==========================================
    # ORDERS (raw Binance order data)
    # ==========================================
    
    async def store_order(
        self, 
        cycle_id: str, 
        result: Dict,
        trade_id: int = None
    ) -> bool:
        """Store raw Binance order data"""
        if not self.enabled:
            return False
            
        try:
            raw_order = result.get('raw_order', {})
            
            data = {
                "cycle_id": cycle_id,
                "trade_id": trade_id,
                "order_id": result.get('order_id'),
                "client_order_id": result.get('client_order_id', ''),
                "symbol": result.get('symbol', ''),
                "side": raw_order.get('side', ''),
                "order_type": raw_order.get('type', 'MARKET'),
                "quantity": result.get('quantity', 0),
                "executed_qty": result.get('executed_qty', 0),
                "avg_price": result.get('avg_price', 0),
                "cum_quote": result.get('cum_quote', 0),
                "commission": result.get('commission', 0),
                "commission_asset": result.get('commission_asset', 'USDT'),
                "status": raw_order.get('status', 'FILLED'),
                "reduce_only": raw_order.get('reduceOnly', False),
                "raw_response": json.dumps(raw_order) if raw_order else None,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            self.client.table("orders").insert(data).execute()
            logger.debug(f"Stored order: {result.get('order_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store order: {e}")
            return False
    
    # ==========================================
    # ACCOUNT SNAPSHOTS
    # ==========================================
    
    async def store_account_snapshot(
        self, 
        cycle_id: str, 
        balance: Dict,
        positions: list,
        realized_pnl_today: float = 0,
        total_commission_today: float = 0,
        trades_today: int = 0
    ) -> bool:
        """Store account balance + equity snapshot"""
        if not self.enabled:
            return False
            
        try:
            total_unrealized = sum(p.get('unrealizedPnl', 0) for p in positions)
            total_margin = sum(p.get('initialMargin', 0) for p in positions)
            total_balance = balance.get('total', 0)
            
            data = {
                "cycle_id": cycle_id,
                "total_balance": total_balance,
                "available_balance": balance.get('free', 0),
                "total_margin_used": total_margin,
                "total_unrealized_pnl": total_unrealized,
                "total_position_value": sum(
                    p.get('positionAmt', 0) * p.get('markPrice', 0) 
                    for p in positions
                ),
                "open_positions_count": len(positions),
                "equity": total_balance + total_unrealized,
                "margin_ratio": (total_margin / (total_balance + total_unrealized) * 100) 
                    if (total_balance + total_unrealized) > 0 else 0,
                "realized_pnl_today": realized_pnl_today,
                "total_commission_today": total_commission_today,
                "trades_today": trades_today,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            self.client.table("account_snapshots").insert(data).execute()
            logger.debug(f"Stored account snapshot for cycle: {cycle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store account snapshot: {e}")
            return False
    
    # ==========================================
    # POSITIONS HISTORY
    # ==========================================
    
    async def store_positions_history(
        self, 
        cycle_id: str, 
        positions: list
    ) -> bool:
        """Snapshot all open positions for this cycle"""
        if not self.enabled or not positions:
            return False
            
        try:
            records = []
            for pos in positions:
                record = {
                    "cycle_id": cycle_id,
                    "symbol": pos.get('symbol', ''),
                    "side": pos.get('side', '').upper(),
                    "position_amt": pos.get('positionAmt', 0),
                    "entry_price": pos.get('entryPrice', 0),
                    "mark_price": pos.get('markPrice', 0),
                    "leverage": pos.get('leverage', 0),
                    "initial_margin": pos.get('initialMargin', 0),
                    "unrealized_pnl": pos.get('unrealizedPnl', 0),
                    "unrealized_pnl_percent": pos.get('percentage', 0),
                    "created_at": datetime.utcnow().isoformat(),
                }
                records.append(record)
            
            if records:
                self.client.table("positions_history").insert(records).execute()
                logger.debug(f"Stored {len(records)} position snapshots")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store positions history: {e}")
            return False
    
    # ==========================================
    # ERROR LOGGING
    # ==========================================
    
    async def log_error(
        self, 
        cycle_id: str, 
        error_type: str, 
        error_message: str,
        stack_trace: str = ""
    ) -> bool:
        """Log error to database"""
        if not self.enabled:
            return False
            
        try:
            data = {
                "cycle_id": cycle_id,
                "error_type": error_type,
                "error_message": error_message[:1000],
                "stack_trace": stack_trace[:2000] if stack_trace else None,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.client.table("error_logs").insert(data).execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            return False
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    async def _store_data(self, table: str, cycle_id: str, data: Dict) -> bool:
        """Generic method to store JSON data"""
        if not self.enabled:
            return False
            
        try:
            record = {
                "cycle_id": cycle_id,
                "data": json.dumps(data),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.client.table(table).insert(record).execute()
            logger.debug(f"Stored data in {table} for cycle: {cycle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store in {table}: {e}")
            return False
    
    async def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades for analysis"""
        if not self.enabled:
            return []
            
        try:
            result = self.client.table("trades")\
                .select("*")\
                .order("executed_at", desc=True)\
                .limit(limit)\
                .execute()
                
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    async def get_performance_summary(self, days: int = 7) -> Dict:
        """Get performance summary for last N days"""
        if not self.enabled:
            return {}
            
        try:
            trades = await self.get_recent_trades(limit=100)
            
            total_pnl = sum(t.get('pnl_usdt', 0) for t in trades)
            win_count = len([t for t in trades if t.get('pnl_usdt', 0) > 0])
            loss_count = len([t for t in trades if t.get('pnl_usdt', 0) < 0])
            
            return {
                "total_trades": len(trades),
                "total_pnl": total_pnl,
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": win_count / len(trades) * 100 if trades else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    async def cleanup_old_data(self, days: int = 30) -> bool:
        """Delete raw data older than N days to save database space.
        Keeps trades and ai_decisions forever for analysis."""
        if not self.enabled:
            return False
            
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        tables_to_clean = [
            "raw_binance_data",
            "raw_news_data",
            "raw_onchain_data",
            "processed_technical",
            "processed_sentiment",
            "aggregated_data",
        ]
        
        total_deleted = 0
        for table in tables_to_clean:
            try:
                result = self.client.table(table)\
                    .delete()\
                    .lt("created_at", cutoff)\
                    .execute()
                count = len(result.data) if result.data else 0
                total_deleted += count
                if count > 0:
                    logger.info(f"  🧹 Cleaned {count} rows from {table}")
            except Exception as e:
                logger.error(f"Failed to clean {table}: {e}")
        
        # Also clean old error logs (keep last 7 days)
        try:
            error_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            self.client.table("error_logs")\
                .delete()\
                .lt("created_at", error_cutoff)\
                .execute()
        except Exception:
            pass
        
        logger.info(f"🧹 Total cleaned: {total_deleted} rows (data older than {days} days)")
        return True


# Singleton instance
db = SupabaseClient()
