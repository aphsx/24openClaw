import { FastifyInstance } from 'fastify';

export function registerRoutes(app: FastifyInstance, { scanner, stateManager, configManager, db }: any) {

    // ดึงผลสแกนล่าสุด
    app.get('/api/pairs', async () => {
        const { rows } = await db.query(
            `SELECT * FROM pairs ORDER BY
       CASE WHEN qualified THEN 0 ELSE 1 END,
       ABS(zscore) DESC`
        );
        return rows;
    });

    // ดึงเฉพาะ Signals
    app.get('/api/pairs/signals', async () => {
        const { rows } = await db.query(
            `SELECT * FROM pairs WHERE qualified=true ORDER BY ABS(zscore) DESC`
        );
        return rows;
    });

    // สั่งสแกนทันที
    app.post('/api/scan/trigger', async () => {
        const result = await scanner.scan();
        return result;
    });

    // ผลสแกนล่าสุด
    app.get('/api/scan/latest', async () => {
        const { rows } = await db.query(
            `SELECT * FROM scan_results ORDER BY scanned_at DESC LIMIT 1`
        );
        return rows[0] || null;
    });

    // Positions
    app.get('/api/positions', async () => {
        return await stateManager.getActivePositions();
    });

    // Trade History
    app.get('/api/trades', async () => {
        const { rows } = await db.query(
            `SELECT * FROM trades ORDER BY opened_at DESC LIMIT 100`
        );
        return rows;
    });

    // Config
    app.get('/api/config', async () => {
        return await configManager.getAll();
    });

    app.put('/api/config/:key', async (req: any) => {
        await configManager.set(req.params.key, req.body.value);
        return { ok: true };
    });

    // Reconciliation
    app.get('/api/reconciliation', async () => {
        const { rows } = await db.query(
            `SELECT * FROM reconciliation_logs ORDER BY checked_at DESC LIMIT 20`
        );
        return rows;
    });
}
