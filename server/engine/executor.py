import asyncio
import uuid
from .exchange import OKXClient
from .models import DBManager

class TradeExecutor:
    def __init__(self, exchange: OKXClient):
        self.exchange = exchange
        self.db = DBManager()

    async def open_pair(self, signal: dict):
        sym_a = signal['symbol_a']
        sym_b = signal['symbol_b']
        
        # Determine direction
        # signal['validation_json']['direction'] e.g. 'sell-buy'
        direction = signal['validation_json'].get('direction', 'sell-buy')
        side_a, side_b = direction.split('-')
        
        # Calculate size (Simplified: fixed $100 for now or based on config)
        base_size = await self.db.get_config('base_order_usd', 100.0)
        size_pct = signal['validation_json'].get('sizePct', 1.0)
        size_usd = base_size * size_pct

        print(f"[Executor] Opening {sym_a} ({side_a}) & {sym_b} ({side_b}) | Size: ${size_usd}")

        try:
            # Leg A
            res_a = await self.exchange.place_order(sym_a, side_a, size_usd)
            
            # Leg B
            try:
                res_b = await self.exchange.place_order(sym_b, side_b, size_usd)
            except Exception as e:
                print(f"[Executor] Leg B failed: {e}. ROLLING BACK Leg A.")
                reverse_a = 'sell' if side_a == 'buy' else 'buy'
                await self.exchange.place_order(sym_a, reverse_a, size_usd)
                return {"success": False, "reason": "leg_b_failed"}

            # Success -> Save to DB
            group_id = str(uuid.uuid4())
            # We would typically have an active_positions table
            # For now, let's just log it
            print(f"[Executor] Pair Opened! GroupID: {group_id}")
            return {"success": True, "groupId": group_id}

        except Exception as e:
            print(f"[Executor] Execution Error: {e}")
            return {"success": False, "reason": str(e)}

    async def close_pair(self, sym_a: str, sym_b: str):
        print(f"[Executor] Closing Pair {sym_a}/{sym_b}")
        await self.exchange.close_position(sym_a)
        await self.exchange.close_position(sym_b)
        return {"success": True}
