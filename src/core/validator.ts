import { z } from 'zod';
import { ConfigManager } from './config-manager';
import { OKXClient } from '../exchange/okx-client';
import { PairSignal, Check } from '../types';

const OrderParamsSchema = z.object({
    symbol: z.string().min(1),
    side: z.enum(['buy', 'sell']),
    sizeUsd: z.number().positive().finite().refine(v => !isNaN(v)),
    price: z.number().positive().finite(),
});

export class PreOrderValidator {
    constructor(private exchange: OKXClient, private config: ConfigManager) { }

    async validate(signal: PairSignal): Promise<{ pass: boolean; checks: Check[] }> {
        const checks: Check[] = [];
        const c = (name: string, pass: boolean, detail: string) =>
            checks.push({ name, pass, detail });

        // 1. Futures มีจริง
        const instA = await this.exchange.getInstrument(signal.symbolA);
        const instB = await this.exchange.getInstrument(signal.symbolB);
        c('futures_exist', !!instA && !!instB,
            `A:${!!instA} B:${!!instB}`);

        // 2. ราคา > 0
        const pxA = instA?.lastPrice || 0;
        const pxB = instB?.lastPrice || 0;
        c('price_positive', pxA > 0 && pxB > 0,
            `A:${pxA} B:${pxB}`);

        // 3. β valid (ไม่ Infinity ไม่ NaN)
        const betaOk = isFinite(signal.beta) && !isNaN(signal.beta) && signal.beta > 0;
        c('beta_valid', betaOk, `β=${signal.beta}`);

        // 4. Size valid
        if (pxA > 0 && pxB > 0 && betaOk) {
            const sizeUsd = await this.config.get('position_size_usd');
            const sA = OrderParamsSchema.safeParse({ symbol: signal.symbolA, side: 'buy', sizeUsd, price: pxA });
            const sB = OrderParamsSchema.safeParse({ symbol: signal.symbolB, side: 'sell', sizeUsd: sizeUsd * signal.beta, price: pxB });
            c('size_valid', sA.success && sB.success,
                `A:${sA.success} B:${sB.success}`);
        } else {
            c('size_valid', false, 'ข้ามเพราะ price/beta ไม่ผ่าน');
        }

        // 5. Correlation
        const corrMin = await this.config.get('corr_min');
        c('correlation', signal.correlation >= corrMin,
            `${signal.correlation.toFixed(3)} ≥ ${corrMin}`);

        // 6. Half-Life
        const hlMin = await this.config.get('half_life_min');
        const hlMax = await this.config.get('half_life_max');
        c('half_life', signal.halfLife >= hlMin && signal.halfLife <= hlMax,
            `${signal.halfLife.toFixed(1)}d [${hlMin}-${hlMax}]`);

        // 7. Volume > $20M (ป้องกัน Liquidity Trap)
        c('volume', (instA?.vol24h || 0) > 20e6 && (instB?.vol24h || 0) > 20e6,
            `A:$${((instA?.vol24h || 0) / 1e6).toFixed(0)}M B:$${((instB?.vol24h || 0) / 1e6).toFixed(0)}M`);

        return { pass: checks.every(c => c.pass), checks };
    }
}
