import { Pool } from 'pg';
import Redis from 'ioredis';
import 'dotenv/config';
import { PairsScanner } from './src/core/scanner';
import { ConfigManager } from './src/core/config-manager';
import { DedupService } from './src/core/dedup';
import { OKXClient } from './src/exchange/okx-client';

async function testScan() {
    const db = new Pool({ connectionString: process.env.DATABASE_URL || 'postgresql://trader:changeme@localhost:5433/pairs_trading' });
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

    // reset lock if exists
    await redis.del('lock:scan');

    const exchange = new OKXClient();
    const configManager = new ConfigManager(db);
    const dedup = new DedupService(db, redis, exchange as any);

    await configManager.load();
    const scanner = new PairsScanner(db, redis, configManager, dedup);

    console.log('Running scan...');
    const result = await scanner.scan();
    console.log(`Scan complete. Found ${result.signals?.length} signals out of ${result.total} pairs tested. Blocked: ${result.blocked?.length}. Duration: ${result.duration}ms.`);

    if (result.signals && result.signals.length > 0) {
        console.log('Top 3 signals:');
        console.log(result.signals.slice(0, 3));
    }

    process.exit(0);
}

testScan().catch(console.error);
