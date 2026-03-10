import { Pool } from 'pg';
import Redis from 'ioredis';
import { OKXClient } from '../exchange/okx-client';

export class DedupService {
    constructor(private db: Pool, private redis: Redis, private exchange: OKXClient) { }

    async canOpen(symA: string, symB: string, maxSameCoin: number): Promise<{
        pass: boolean; checks: { layer: number; name: string; pass: boolean; detail: string }[]
    }> {
        const checks = [];

        // ชั้น 1: Redis
        const inRedis = await this.redis.exists(`position:active:${symA}:${symB}`);
        checks.push({ layer: 1, name: 'redis', pass: !inRedis, detail: inRedis ? 'เปิดอยู่แล้ว' : 'ว่าง' });

        // ชั้น 2: DB
        const { rows } = await this.db.query(
            `SELECT 1 FROM trades WHERE symbol_a=$1 AND symbol_b=$2 AND status='open' LIMIT 1`,
            [symA, symB]
        );
        checks.push({ layer: 2, name: 'database', pass: rows.length === 0, detail: rows.length > 0 ? 'มีใน DB' : 'ว่าง' });

        // ชั้น 3: Exchange
        let onExch = false;
        try {
            const posA = await this.exchange.hasPosition(symA);
            const posB = await this.exchange.hasPosition(symB);
            onExch = posA || posB;
        } catch { onExch = true; } // ถ้าเช็คไม่ได้ → ไม่ให้เปิด (Defensive)
        checks.push({ layer: 3, name: 'exchange', pass: !onExch, detail: onExch ? 'มีบน Exchange' : 'ว่าง' });

        // ชั้น 4: Cooldown
        const inCooldown = await this.redis.exists(`cooldown:${symA}:${symB}`);
        checks.push({ layer: 4, name: 'cooldown', pass: !inCooldown, detail: inCooldown ? 'ยังอยู่ใน cooldown' : 'ผ่าน' });

        // ชั้น 5: Concentration
        const expA = parseInt(await this.redis.get(`exposure:${symA}`) || '0');
        const expB = parseInt(await this.redis.get(`exposure:${symB}`) || '0');
        checks.push({
            layer: 5, name: 'concentration', pass: expA < maxSameCoin && expB < maxSameCoin,
            detail: `${symA}:${expA} ${symB}:${expB} max:${maxSameCoin}`
        });

        return { pass: checks.every(c => c.pass), checks };
    }
}
