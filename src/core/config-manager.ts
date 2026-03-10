import { Pool } from 'pg';

export class ConfigManager {
    private cache: Map<string, number> = new Map();

    constructor(private db: Pool) { }

    async load(): Promise<void> {
        const { rows } = await this.db.query('SELECT key, value FROM config');
        this.cache.clear();
        rows.forEach((r: any) => this.cache.set(r.key, parseFloat(r.value)));
    }

    async get(key: string): Promise<number> {
        if (!this.cache.has(key)) await this.load();
        const val = this.cache.get(key);
        if (val === undefined) throw new Error(`Config not found: ${key}`);
        return val;
    }

    async getAll(): Promise<Record<string, any>> {
        const { rows } = await this.db.query(
            `SELECT key, value, description, backtest_rank, backtest_total FROM config`
        );
        return Object.fromEntries(rows.map((r: any) => [r.key, {
            value: parseFloat(r.value),
            description: r.description,
            needsBacktest: !r.backtest_rank,
        }]));
    }

    async set(key: string, value: number): Promise<void> {
        await this.db.query(`UPDATE config SET value=$1 WHERE key=$2`, [value, key]);
        this.cache.set(key, value);
    }
}
