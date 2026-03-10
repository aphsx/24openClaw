import ccxt from 'ccxt';
import { Pool } from 'pg';
import Redis from 'ioredis';
import * as ind from './indicators';
import { classifyZone } from './safe-zone';
import { ConfigManager } from './config-manager';
import { DedupService } from './dedup';
import { PairResult, ScanResult } from '../types';

export class PairsScanner {
    private exchange: any;

    constructor(
        private db: Pool,
        private redis: Redis,
        private config: ConfigManager,
        private dedup: DedupService
    ) {
        this.exchange = new ccxt.okx({ enableRateLimit: true });
    }

    async scan(): Promise<ScanResult> {
        const start = Date.now();

        // ═══ Lock ป้องกันสแกนซ้อน (Bug #5) ═══
        const locked = await this.redis.set('lock:scan', '1', 'EX', 120, 'NX');
        if (!locked) return { skipped: true, reason: 'scan_in_progress' };

        try {
            // ═══ Step 1: ดึงรายชื่อเหรียญ ═══
            const markets = await this.exchange.loadMarkets();
            const symbols = Object.keys(markets).filter(s =>
                markets[s] && markets[s].swap && markets[s].quote === 'USDT' && markets[s].active
            );

            // ═══ Step 2: ดึง Ticker กรอง Volume > $20M ═══
            const tickers = await this.exchange.fetchTickers(symbols);
            const qualified = Object.entries(tickers)
                .filter(([_, t]: [string, any]) => {
                    const usdVolume = t.quoteVolume || (parseFloat(t.info?.volCcy24h || '0') * t.last) || 0;
                    return usdVolume > 20_000_000;
                })
                .map(([sym, t]: [string, any]) => {
                    const usdVolume = t.quoteVolume || (parseFloat(t.info?.volCcy24h || '0') * t.last) || 0;
                    return { symbol: sym.split('/')[0], price: t.last, vol: usdVolume };
                })
                .slice(0, 25); // จำกัด 25 เหรียญ (325 คู่)

            console.log(`Qualified coins: ${qualified.length}`);

            // ═══ Step 3: ดึง OHLCV 180 วัน (cached ใน DB) ═══
            const closes: Record<string, number[]> = {};
            for (const coin of qualified) {
                closes[coin.symbol] = await this.getCloses(coin.symbol, 180);
                await this.sleep(100); // Rate limit
            }

            // ═══ Step 4: คำนวณทุกคู่ ═══
            const pairs: PairResult[] = [];
            const symbolList = qualified.map(c => c.symbol);
            const cfgEntry = await this.config.get('zscore_entry');
            const cfgSl = await this.config.get('zscore_sl');
            const cfgBuf = await this.config.get('safe_buffer');
            const cfgCorr = await this.config.get('corr_min');
            const cfgHlMin = await this.config.get('half_life_min');
            const cfgHlMax = await this.config.get('half_life_max');
            const cfgMaxCoin = await this.config.get('max_same_coin');

            for (let i = 0; i < symbolList.length; i++) {
                for (let j = i + 1; j < symbolList.length; j++) {
                    const symA = symbolList[i];
                    const symB = symbolList[j];
                    const cA = closes[symA];
                    const cB = closes[symB];
                    if (!cA || !cB || cA.length < 60 || cB.length < 60) continue;

                    // ตัดให้ยาวเท่ากัน
                    const len = Math.min(cA.length, cB.length);
                    const a = cA.slice(-len);
                    const b = cB.slice(-len);

                    // Correlation
                    const corr = ind.correlation(a, b);
                    if (corr === null) continue;

                    // Hedge Ratio
                    const beta = ind.hedgeRatio(a, b);
                    if (beta === null) continue;

                    // Spread series
                    const spreads = a.map((v, idx) => v - beta * b[idx]);

                    // Half-Life
                    const hl = ind.halfLife(spreads);
                    if (hl === null) continue;

                    // Hurst (ต้อง < 0.5 = mean-reverting)
                    const hurst = ind.hurstExponent(spreads);
                    if (hurst === null) continue;

                    // Z-Score
                    const recent60 = spreads.slice(-60);
                    const spreadMean = recent60.reduce((acc, v) => acc + v, 0) / recent60.length;
                    const spreadSd = Math.sqrt(recent60.reduce((acc, v) => acc + (v - spreadMean) ** 2, 0) / recent60.length);
                    const z = ind.zScore(spreads[spreads.length - 1], spreadMean, spreadSd);
                    if (z === null) continue;

                    // Check if passes stat checks
                    const passedStats = corr >= cfgCorr && hl >= cfgHlMin && hl <= cfgHlMax && hurst < 0.5;

                    // Zone classification
                    const zone = classifyZone(z, { zscore_entry: cfgEntry, zscore_sl: cfgSl, safe_buffer: cfgBuf });

                    // Dedup check
                    const dedupResult = await this.dedup.canOpen(symA, symB, cfgMaxCoin);

                    // Direction
                    const direction = z > 0 ? { legA: 'sell', legB: 'buy' } : { legA: 'buy', legB: 'sell' };

                    const canOpenFinal = zone.canOpen && dedupResult.pass && passedStats;

                    pairs.push({
                        symbolA: symA, symbolB: symB,
                        correlation: corr,
                        hurst: Math.max(-9999, Math.min(9999, hurst)),
                        halfLife: Math.max(-9999, Math.min(9999, hl)),
                        hedgeRatio: Math.max(-9999, Math.min(9999, beta)),
                        zscore: Math.max(-9999, Math.min(9999, z)),
                        zone: zone.zone, canOpen: canOpenFinal,
                        sizePct: zone.sizePct, direction,
                        dedupChecks: dedupResult.checks,
                        blocked: Math.abs(z) >= cfgEntry && (!canOpenFinal),
                        blockReason: !passedStats ? 'Stats failed' : !zone.canOpen ? `Zone: ${zone.zone}` : !dedupResult.pass ? 'Dedup failed' : null,
                    });
                }
            }

            // Sort: signals first → then |Z| descending
            pairs.sort((a, b) => {
                if (a.canOpen && !b.canOpen) return -1;
                if (!a.canOpen && b.canOpen) return 1;
                return Math.abs(b.zscore) - Math.abs(a.zscore);
            });

            // ═══ Step 5: บันทึก DB ═══
            const signals = pairs.filter(p => p.canOpen);
            const blocked = pairs.filter(p => p.blocked);

            // Upsert pairs table
            for (const p of pairs) {
                await this.db.query(
                    `INSERT INTO pairs (symbol_a, symbol_b, correlation, hurst_exp, half_life,
           hedge_ratio, zscore, zone, qualified, validation_json, scanned_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
           ON CONFLICT (symbol_a, symbol_b) DO UPDATE SET
           correlation=$3, hurst_exp=$4, half_life=$5, hedge_ratio=$6,
           zscore=$7, zone=$8, qualified=$9, validation_json=$10, scanned_at=NOW()`,
                    [p.symbolA, p.symbolB, p.correlation, p.hurst, p.halfLife,
                    p.hedgeRatio, p.zscore, p.zone, p.canOpen,
                    JSON.stringify({ zone: p.zone, sizePct: p.sizePct, direction: p.direction, dedup: p.dedupChecks })]
                );

                // Cache Z-Score ใน Redis
                await this.redis.set(`zscore:${p.symbolA}:${p.symbolB}`, p.zscore.toString(), 'EX', 300);
            }

            const duration = Date.now() - start;
            await this.db.query(
                `INSERT INTO scan_results (total_pairs, qualified, signals, blocked, duration_ms, details)
         VALUES ($1,$2,$3,$4,$5,$6)`,
                [pairs.length, pairs.filter(p => p.correlation >= cfgCorr).length,
                signals.length, blocked.length, duration, JSON.stringify(signals.slice(0, 10))]
            );

            return { pairs, signals, blocked, duration: duration, total: pairs.length };

        } finally {
            await this.redis.del('lock:scan');
        }
    }

    private async getCloses(symbol: string, days: number): Promise<number[]> {
        // ดึงจาก DB cache ก่อน
        const { rows } = await this.db.query(
            `SELECT close FROM ohlcv_daily WHERE symbol=$1 ORDER BY ts DESC LIMIT $2`,
            [symbol, days]
        );
        if (rows.length >= days * 0.8) {
            return rows.map(r => parseFloat(r.close)).reverse();
        }

        // ถ้าไม่พอ ดึงจาก OKX
        try {
            const since = this.exchange.parse8601(
                new Date(Date.now() - days * 86400000).toISOString()
            );
            const ohlcv = await this.exchange.fetchOHLCV(
                `${symbol}/USDT:USDT`, '1d', since, days
            );
            // เก็บ DB
            for (const [ts, o, h, l, c, v] of ohlcv) {
                if (!ts || !c) continue;
                const date = new Date(ts).toISOString().split('T')[0];
                await this.db.query(
                    `INSERT INTO ohlcv_daily (symbol, ts, close, volume)
           VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
                    [symbol, date, c, v]
                );
            }
            return ohlcv.map((c: any) => Number(c[4])); // close prices
        } catch (e: any) {
            console.error(`Failed to fetch OHLCV for ${symbol}: ${e.message}`);
            return [];
        }
    }

    private sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }
}
