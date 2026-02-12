"""
ClawBot AI — In-Memory Cache
Python dict cache for fast data access during cycle (no disk I/O)
"""
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class CycleCache:
    """
    In-memory cache for a single cycle.
    All data stored as Python dicts in RAM — fastest possible access.
    After cycle completes, data is flushed to Supabase async.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Clear all data for a new cycle."""
        self.cycle_id: str = ""
        self.started_at: datetime = datetime.now(timezone.utc)
        self.cycle_number: int = 0

        # Account state
        self.balance: float = 0.0
        self.available_margin: float = 0.0
        self.positions: list = []
        self.closed_between_cycles: list = []

        # Market data (indicators per symbol per TF)
        self.candles: Dict[str, Dict[str, Any]] = {}  # {symbol: {tf: DataFrame}}
        self.indicators: Dict[str, Dict[str, Any]] = {}  # {symbol: {tf: {ind: val}}}
        self.regimes: Dict[str, str] = {}  # {symbol: "trending_up"}
        self.prices: Dict[str, float] = {}  # {symbol: current_price}

        # News & sentiment
        self.news: list = []
        self.news_is_cached: bool = False
        self.fear_greed: Dict[str, Any] = {}

        # Market data
        self.funding_rates: Dict[str, float] = {}
        self.long_short_ratios: Dict[str, float] = {}
        self.open_interest: Dict[str, float] = {}
        self.volume_24h: Dict[str, float] = {}
        self.price_changes: Dict[str, Dict[str, float]] = {}

        # Whale Data
        self.taker_buy_sell: Dict[str, dict] = {}        # {symbol: {ratio, buy_vol, sell_vol}}
        self.top_trader_accounts: Dict[str, dict] = {}   # {symbol: {long_pct, short_pct}}
        self.top_trader_positions: Dict[str, dict] = {}  # {symbol: {long_pct, short_pct}}
        self.order_book_imbalance: Dict[str, dict] = {}  # {symbol: {bid_ask_ratio, whale_walls}}

        # AI decision
        self.ai_input_json: dict = {}
        self.ai_output_json: dict = {}
        self.ai_analysis: str = ""
        self.ai_actions: list = []
        self.ai_model: str = ""
        self.ai_latency_ms: int = 0
        self.ai_cost_usd: float = 0.0
        self.ai_prompt_tokens: int = 0
        self.ai_completion_tokens: int = 0

        # Execution results
        self.executed_trades: list = []

        # Timing
        self.phase_timings: Dict[str, int] = {}  # {phase: duration_ms}

    def set_timing(self, phase: str, duration_ms: int):
        """Record duration of a phase."""
        self.phase_timings[phase] = duration_ms

    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """Get all data for a symbol as a dict (for AI input)."""
        # Build whale activity
        whale_activity = {}
        
        # Taker buy/sell
        taker = self.taker_buy_sell.get(symbol, {})
        if taker:
            whale_activity["taker_buy_sell_ratio"] = taker.get("buySellRatio")
            
        # Top traders
        top_acc = self.top_trader_accounts.get(symbol, {})
        if top_acc:
            whale_activity["top_trader_long_pct"] = top_acc.get("longAccount")
            whale_activity["top_trader_short_pct"] = top_acc.get("shortAccount")
            
        # Top positions (optional, but requested)
        # User example showed top_trader_long_pct which usually refers to accounts or positions, 
        # I'll stick to accounts as primary but can add positions if needed. 
        # Actually user plan says: "top_trader_long_pct" in example. 
        # Let's include everything available.
        
        whale_activity["open_interest_usdt"] = self.open_interest.get(symbol, 0)
        
        # Order book
        book = self.order_book_imbalance.get(symbol, {})
        if book:
            whale_activity["order_book_bid_ask_ratio"] = book.get("bid_ask_ratio")
            whale_activity["whale_walls"] = book.get("whale_walls", [])

        return {
            "price": self.prices.get(symbol, 0),
            "indicators_5m": self.indicators.get(symbol, {}).get("5m", {}),
            "indicators_15m": self.indicators.get(symbol, {}).get("15m", {}),
            "indicators_1h": self.indicators.get(symbol, {}).get("1h", {}),
            "indicators_4h": self.indicators.get(symbol, {}).get("4h", {}),
            "regime": self.regimes.get(symbol, "unknown"),
            "funding_rate": self.funding_rates.get(symbol, 0),
            "long_short_ratio": self.long_short_ratios.get(symbol, 0),
            "volume_24h_usdt": self.volume_24h.get(symbol, 0),
            "price_change_5m_pct": self.price_changes.get(symbol, {}).get("5m", 0),
            "price_change_1h_pct": self.price_changes.get(symbol, {}).get("1h", 0),
            "price_change_24h_pct": self.price_changes.get(symbol, {}).get("24h", 0),
            "whale_activity": whale_activity
        }

    def build_ai_input(self, risk_config: dict) -> dict:
        """Build the complete JSON input for AI."""
        coins_data = {}
        for symbol in self.indicators.keys():
            coins_data[symbol] = self.get_symbol_data(symbol)

        self.ai_input_json = {
            "cycle_id": self.cycle_id,
            "timestamp": self.started_at.isoformat(),
            "account": {
                "balance_usdt": round(self.balance, 4),
                "available_margin": round(self.available_margin, 4),
                "positions": self.positions,
                "closed_since_last_cycle": self.closed_between_cycles,
            },
            "coins": coins_data,
            "news": self.news[:20],  # max 20
            "fear_greed": self.fear_greed,
            "risk_config": risk_config,
        }
        return self.ai_input_json

    def to_supabase_cycle(self) -> dict:
        """Convert cache to Supabase cycle row."""
        completed = datetime.now(timezone.utc)
        duration = int((completed - self.started_at).total_seconds() * 1000)
        return {
            "cycle_number": self.cycle_number,
            "started_at": self.started_at.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_ms": duration,
            "balance_usdt": self.balance,
            "available_margin": self.available_margin,
            "positions_count": len(self.positions),
            "actions_taken": len(self.ai_actions),
            "orders_opened": sum(1 for a in self.ai_actions if "OPEN" in a.get("action", "")),
            "orders_closed": sum(1 for a in self.ai_actions if a.get("action") == "CLOSE"),
            "sl_tp_triggered": len(self.closed_between_cycles),
            "ai_model": self.ai_model,
            "ai_latency_ms": self.ai_latency_ms,
            "ai_cost_usd": self.ai_cost_usd,
            "news_count": len(self.news),
            "news_is_cached": self.news_is_cached,
            "fear_greed_value": self.fear_greed.get("value"),
            "status": "completed",
        }
