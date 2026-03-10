import 'dotenv/config';
import { Pool } from 'pg';
import Redis from 'ioredis';
import Fastify from 'fastify';
import cors from '@fastify/cors';

import { StateManager } from './core/state-manager';
import { ConfigManager } from './core/config-manager';
import { DedupService } from './core/dedup';
import { PairsScanner } from './core/scanner';
import { ReconciliationService } from './core/reconciliation';
import { LifecycleManager } from './core/lifecycle';
import { registerRoutes } from './api/routes';
import { OKXClient } from './exchange/okx-client';

async function main() {
    const db = new Pool({ connectionString: process.env.DATABASE_URL });
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

    const exchange = new OKXClient();
    const stateManager = new StateManager(db, redis);
    const configManager = new ConfigManager(db);
    const dedup = new DedupService(db, redis, exchange as any);
    const scanner = new PairsScanner(db, redis, configManager, dedup);
    const reconciliation = new ReconciliationService(stateManager, exchange as any, db);
    const lifecycle = new LifecycleManager(redis, db, stateManager);

    // ═══ Startup ═══
    lifecycle.listen();
    await lifecycle.startup();
    await configManager.load();

    // ═══ API ═══
    const app = Fastify();
    await app.register(cors, { origin: true });
    registerRoutes(app, { scanner, stateManager, configManager, db });
    await app.listen({ port: 3001, host: '0.0.0.0' });
    console.log('API ready on :3001');

    // ═══ Auto Scan ═══
    const scanInterval = await configManager.get('scan_interval_sec');
    lifecycle.addInterval(async () => {
        try {
            const result = await scanner.scan();
            if (!result.skipped) {
                console.log(`[Scan] ${result.signals?.length || 0} signals / ${result.total} pairs / ${result.duration}ms`);
            }
        } catch (e: any) {
            console.error('[Scan Error]', e.message);
        }
    }, scanInterval * 1000);

    // ═══ Reconciliation ทุก 5 นาที ═══
    lifecycle.addInterval(async () => {
        try { await reconciliation.run(); } catch (e: any) { console.error('[Recon Error]', e.message); }
    }, 300_000);

    console.log('System running. Scanner active.');
}

main().catch(console.error);
