import { Pool } from 'pg';
import { StateManager } from './state-manager';
import { OKXClient } from '../exchange/okx-client';

export class ReconciliationService {
    constructor(
        private stateManager: StateManager,
        private exchange: OKXClient,
        private db: Pool
    ) { }

    async run(): Promise<{ orphans: string[]; ghosts: string[] }> {
        const dbPositions = await this.stateManager.getActivePositions();
        const dbKeys = new Set(dbPositions.map(p => `${p.symbol_a}/${p.symbol_b}`));

        const exchPositions = await this.exchange.getOpenPositions();
        const exchKeys = new Set(exchPositions.map(p => p.symbol));

        const orphans: string[] = []; // อยู่บน Exchange ไม่อยู่ใน DB
        const ghosts: string[] = [];  // อยู่ใน DB ไม่อยู่บน Exchange

        for (const k of exchKeys) if (!dbKeys.has(k)) orphans.push(k);
        for (const k of dbKeys) if (!exchKeys.has(k)) ghosts.push(k);

        // ═══ ORPHAN = แจ้งเตือนเท่านั้น ห้าม AUTO-CLOSE เด็ดขาด! ═══
        if (orphans.length > 0) {
            console.error(`🔴 ORPHANS: ${orphans.join(', ')} — ต้องจัดการด้วยมือ`);
        }

        await this.db.query(
            `INSERT INTO reconciliation_logs (db_count, exchange_count, orphans, action, details)
       VALUES ($1,$2,$3,'alert_only',$4)`,
            [dbKeys.size, exchKeys.size, orphans.length,
            JSON.stringify({ orphans, ghosts })]
        );

        return { orphans, ghosts };
    }
}
