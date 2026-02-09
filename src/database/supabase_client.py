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
        """Mark cycle as completed"""
        if not self.enabled:
            return None
            
        try:
            data = {
                "completed_at": datetime.utcnow().isoformat(),
                "status": status,
                "decisions_count": summary.get('decisions_count', 0) if summary else 0,
                "trades_executed": summary.get('trades_executed', 0) if summary else 0
            }
            
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
        """Store executed trade"""
        if not self.enabled:
            return False
            
        try:
            data = {
                "cycle_id": cycle_id,
                "action": action,
                "symbol": symbol,
                "side": "LONG" if action == "OPEN_LONG" else "SHORT" if action == "OPEN_SHORT" else "CLOSE",
                "entry_price": result.get('price', 0),
                "quantity": result.get('quantity', 0),
                "leverage": result.get('leverage', 0),
                "margin": result.get('margin', 0),
                "pnl_usdt": result.get('closed_pnl', 0),
                "reasoning": reasoning[:500],
                "order_id": str(result.get('order_id', '')),
                "success": result.get('success', False),
                "error_message": result.get('message', '') if not result.get('success') else None,
                "executed_at": result.get('executed_at', datetime.utcnow().isoformat())
            }
            
            self.client.table("trades").insert(data).execute()
            logger.debug(f"Stored trade: {action} {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store trade: {e}")
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


# Singleton instance
db = SupabaseClient()
