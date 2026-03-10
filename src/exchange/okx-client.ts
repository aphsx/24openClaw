import ccxt from 'ccxt';
import { Instrument } from '../types';

export class OKXClient {
    public ccxtClient: any;

    constructor() {
        this.ccxtClient = new ccxt.okx({
            enableRateLimit: true,
            apiKey: process.env.OKX_API_KEY || '',
            secret: process.env.OKX_SECRET_KEY || '',
            password: process.env.OKX_PASSWORD || '',
        });
    }

    async getInstrument(symbol: string): Promise<Instrument | null> {
        try {
            const ticker = await this.ccxtClient.fetchTicker(`${symbol}/USDT:USDT`);
            return {
                symbol,
                hasFutures: true,
                vol24h: ticker.quoteVolume || 0,
                lastPrice: ticker.last || 0,
            };
        } catch {
            return null;
        }
    }

    async getOpenPositions(): Promise<any[]> {
        try {
            if (!process.env.OKX_API_KEY) return [];
            const positions = await this.ccxtClient.fetchPositions();
            return positions;
        } catch {
            return [];
        }
    }

    async hasPosition(symbol: string): Promise<boolean> {
        try {
            if (!process.env.OKX_API_KEY) return false;
            const positions = await this.ccxtClient.fetchPositions([`${symbol}/USDT:USDT`]);
            return positions.length > 0;
        } catch {
            return false;
        }
    }

    async placeOrder(symbol: string, side: 'buy' | 'sell', sizeUsd: number): Promise<any> {
        if (!process.env.OKX_API_KEY) {
            console.log(`[DRY RUN] Would place ${side} order for ${symbol} size $${sizeUsd}`);
            return { id: `mock_${Date.now()}` };
        }
        const ticker = await this.ccxtClient.fetchTicker(`${symbol}/USDT:USDT`);
        if (!ticker.last) throw new Error(`No price for ${symbol}`);

        // Convert USD to contract size or base currency based on OKX rules, simplified here:
        const amount = sizeUsd / ticker.last;
        return await this.ccxtClient.createMarketOrder(`${symbol}/USDT:USDT`, side, amount);
    }

    async closePosition(symbol: string): Promise<any> {
        if (!process.env.OKX_API_KEY) {
            console.log(`[DRY RUN] Would close position for ${symbol}`);
            return;
        }
        const positions = await this.ccxtClient.fetchPositions([`${symbol}/USDT:USDT`]);
        if (positions.length === 0) return;
        const pos = positions[0];
        const side = pos.side === 'long' ? 'sell' : 'buy';
        return await this.ccxtClient.createMarketOrder(`${symbol}/USDT:USDT`, side, Math.abs(pos.contracts || 0), undefined, { reduceOnly: true });
    }
}
