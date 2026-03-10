import asyncio
import time
import json
from .exchange import OKXClient
from .models import DBManager
from .stats import compute_pair_stats, classify_zone

class PairsScanner:
    def __init__(self, exchange: OKXClient):
        self.exchange = exchange
        self.db = DBManager()

    async def scan(self):
        start_time = time.time()
        print("[Scan] Starting Python Scan...")
        
        # 1. Get Top 25 Qualified Coins
        qualified_coins = await self.exchange.get_trading_symbols(min_volume=20_000_000)
        print(f"[Scan] Qualified coins: {len(qualified_coins)}")

        # 2. Get OHLCV Data (Cached or Fetch)
        closes = {}
        for coin in qualified_coins:
            symbol = coin['symbol']
            stored_closes = await self.db.get_ohlcv(symbol, 180)
            if len(stored_closes) < 144: # Less than 80% coverage
                print(f"[Scan] Fetching OHLCV for {symbol}")
                ohlcv = await self.exchange.fetch_ohlcv(symbol, 180)
                for row in ohlcv:
                    ts_date = time.strftime('%Y-%m-%d', time.gmtime(row[0]/1000))
                    await self.db.save_ohlcv(symbol, ts_date, row[4], row[5])
                closes[symbol] = [float(r[4]) for r in ohlcv]
            else:
                closes[symbol] = stored_closes
            await asyncio.sleep(0.05) # Rate limit protection

        # 3. Create Pairs and Compute Stats
        symbol_list = list(closes.keys())
        pairs_data = []
        
        # Load Configs
        config = {
            'zscore_entry': await self.db.get_config('zscore_entry', 2.0),
            'zscore_sl': await self.db.get_config('zscore_sl', 3.5),
            'safe_buffer': await self.db.get_config('safe_buffer', 0.2),
            'corr_min': await self.db.get_config('corr_min', 0.8),
            'half_life_min': await self.db.get_config('half_life_min', 2.0),
            'half_life_max': await self.db.get_config('half_life_max', 35.0),
            'pvalue_max': await self.db.get_config('pvalue_max', 0.05)
        }

        for i in range(len(symbol_list)):
            for j in range(i + 1, len(symbol_list)):
                sym_a = symbol_list[i]
                sym_b = symbol_list[j]
                
                c_a = closes[sym_a]
                c_b = closes[sym_b]
                min_len = min(len(c_a), len(c_b))
                
                corr, beta, hl, hurst, z, pval = compute_pair_stats(c_a[-min_len:], c_b[-min_len:])
                
                if any(v is None for v in [corr, beta, hl, hurst, z]): continue
                
                # Check stats
                stats_pass = (corr >= config['corr_min'] and 
                              hl >= config['half_life_min'] and 
                              hl <= config['half_life_max'] and 
                              hurst < 0.5 and 
                              (pval is not None and pval <= config['pvalue_max']))
                
                zone_info = classify_zone(z, config)
                can_open = zone_info['can_open'] and stats_pass
                
                pair_entry = {
                    'symbol_a': sym_a,
                    'symbol_b': sym_b,
                    'correlation': corr,
                    'hurst_exp': hurst,
                    'half_life': hl,
                    'hedge_ratio': beta,
                    'zscore': z,
                    'zone': zone_info['zone'],
                    'qualified': can_open,
                    'cointegration_pvalue': pval,
                    'validation_json': {
                        'zone': zone_info['zone'],
                        'sizePct': zone_info['size_pct'],
                        'direction': 'sell-buy' if z > 0 else 'buy-sell',
                        'stats_pass': stats_pass
                    }
                }
                
                await self.db.upsert_pair(pair_entry)
                pairs_data.append(pair_entry)

        # 4. Save Final Scan Result
        duration = int((time.time() - start_time) * 1000)
        signals = [p for p in pairs_data if p['qualified']]
        
        await self.db.save_scan_result(
            total=len(pairs_data),
            qualified=len([p for p in pairs_data if p['correlation'] >= config['corr_min']]),
            signals=len(signals),
            blocked=0, # Simplified
            duration=duration,
            details={'signals': [s['symbol_a'] + '-' + s['symbol_b'] for s in signals[:10]]}
        )
        
        print(f"[Scan] Complete in {duration}ms. {len(signals)} signals found.")
        return pairs_data
