import { Pool } from 'pg';
import Redis from 'ioredis';
import { StateManager } from './state-manager';

export class LifecycleManager {
    private intervals: NodeJS.Timeout[] = [];

    constructor(private redis: Redis, private db: Pool, private stateManager: StateManager) { }

    async startup(): Promise<void> {
        // 1. ลบ Lock เก่าที่ค้าง
        const locks = await this.redis.keys('lock:*');
        if (locks.length) await this.redis.del(...locks);

        // 2. Rebuild cache จาก DB
        const count = await this.stateManager.rebuildCache();
        console.log(`[Startup] Rebuilt ${count} positions from DB`);
    }

    addInterval(fn: () => void, ms: number): void {
        this.intervals.push(setInterval(fn, ms));
    }

    async shutdown(): Promise<void> {
        this.intervals.forEach(id => clearInterval(id));
        await this.redis.quit();
        await this.db.end();
        console.log('[Shutdown] Clean exit');
    }

    listen(): void {
        process.on('SIGTERM', () => this.shutdown());
        process.on('SIGINT', () => this.shutdown());
    }
}
