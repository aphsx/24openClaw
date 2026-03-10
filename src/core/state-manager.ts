import { Pool } from 'pg';
import Redis from 'ioredis';

export class StateManager {
    constructor(private db: Pool, private redis: Redis) { }

    async savePosition(pos: {
        groupId: string; symbolA: string; symbolB: string;
        legASide: string; sizeA: number; legBSide: string; sizeB: number;
        entryZscore: number; entryCorr: number; entryBeta: number; zone: string;
        validationJson: object;
    }): Promise<void> {
        // DB ก่อนเสมอ
        await this.db.query(
            `INSERT INTO trades
       (group_id, symbol_a, symbol_b, leg_a_side, leg_a_size_usd,
        leg_b_side, leg_b_size_usd, entry_zscore, entry_corr,
        entry_beta, entry_zone, validation_json, status)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,'open')`,
            [pos.groupId, pos.symbolA, pos.symbolB, pos.legASide, pos.sizeA,
            pos.legBSide, pos.sizeB, pos.entryZscore, pos.entryCorr,
            pos.entryBeta, pos.zone, JSON.stringify(pos.validationJson)]
        );
        // แล้วค่อย Redis
        await this.redis.set(`position:active:${pos.symbolA}:${pos.symbolB}`, pos.groupId);
        await this.redis.incr(`exposure:${pos.symbolA}`);
        await this.redis.incr(`exposure:${pos.symbolB}`);
    }

    async closePosition(symbolA: string, symbolB: string, reason: string, pnl: number): Promise<void> {
        await this.db.query(
            `UPDATE trades SET status='closed', exit_reason=$1, pnl_usd=$2, closed_at=NOW()
       WHERE symbol_a=$3 AND symbol_b=$4 AND status='open'`,
            [reason, pnl, symbolA, symbolB]
        );
        await this.redis.del(`position:active:${symbolA}:${symbolB}`);
        await this.redis.decr(`exposure:${symbolA}`);
        await this.redis.decr(`exposure:${symbolB}`);
        await this.redis.set(`cooldown:${symbolA}:${symbolB}`, '1', 'EX', 3600);
    }

    async getActivePositions(): Promise<any[]> {
        const { rows } = await this.db.query(`SELECT * FROM trades WHERE status='open'`);
        return rows;
    }

    // ตอน Startup: rebuild Redis จาก DB
    async rebuildCache(): Promise<number> {
        // ลบ cache เก่า
        const oldKeys = await this.redis.keys('position:active:*');
        if (oldKeys.length) await this.redis.del(...oldKeys);
        const oldExp = await this.redis.keys('exposure:*');
        if (oldExp.length) await this.redis.del(...oldExp);

        // โหลดจาก DB
        const positions = await this.getActivePositions();
        for (const p of positions) {
            await this.redis.set(`position:active:${p.symbol_a}:${p.symbol_b}`, p.group_id);
            await this.redis.incr(`exposure:${p.symbol_a}`);
            await this.redis.incr(`exposure:${p.symbol_b}`);
        }
        return positions.length;
    }
}
