import Redis from 'ioredis';
import * as crypto from 'crypto';
import { OKXClient } from '../exchange/okx-client';
import { StateManager } from './state-manager';
import { ValidatedSignal } from '../types';

export class AtomicExecutor {
    constructor(
        private exchange: OKXClient,
        private stateManager: StateManager,
        private redis: Redis
    ) { }

    async openPair(signal: ValidatedSignal): Promise<{ success: boolean; reason: string }> {
        // ═══ Acquire Lock ═══
        const lockKey = `lock:trade:${signal.symbolA}:${signal.symbolB}`;
        const locked = await this.redis.set(lockKey, '1', 'EX', 30, 'NX');
        if (!locked) return { success: false, reason: 'lock_held' };

        try {
            // ═══ Leg A ═══
            let legA;
            try {
                legA = await this.exchange.placeOrder(signal.symbolA, signal.legASide, signal.sizeA);
            } catch (e: any) {
                return { success: false, reason: `leg_a_failed: ${e.message}` };
            }

            // ═══ Leg B ═══
            let legB;
            try {
                legB = await this.exchange.placeOrder(signal.symbolB, signal.legBSide, signal.sizeB);
            } catch (e: any) {
                // ═══ ROLLBACK: ปิด Leg A ทันที ═══
                console.error(`🔴 Leg B failed → Rolling back Leg A`);
                const reverseSide = signal.legASide === 'buy' ? 'sell' : 'buy';
                try {
                    await this.exchange.placeOrder(signal.symbolA, reverseSide, signal.sizeA);
                    // ═══ Post-Rollback Verification ═══
                    await this.sleep(2000);
                    const stillOpen = await this.exchange.hasPosition(signal.symbolA);
                    if (stillOpen) {
                        console.error('🚨 Rollback ไม่สำเร็จ! ต้องปิดด้วยมือ');
                    }
                } catch (rbErr) {
                    console.error(`🚨 CRITICAL: Rollback failed! ${signal.symbolA} ค้างอยู่!`);
                }
                return { success: false, reason: `leg_b_failed: ${e.message}` };
            }

            // ═══ ทั้ง 2 ขาสำเร็จ → บันทึก DB ═══
            const groupId = crypto.randomUUID();
            await this.stateManager.savePosition({
                groupId, symbolA: signal.symbolA, symbolB: signal.symbolB,
                legASide: signal.legASide, sizeA: signal.sizeA,
                legBSide: signal.legBSide, sizeB: signal.sizeB,
                entryZscore: signal.zscore, entryCorr: signal.correlation,
                entryBeta: signal.beta, zone: signal.zone,
                validationJson: signal.validation,
            });

            // ═══ Grace Period ═══
            await this.redis.set(`grace:${groupId}`, '1', 'EX', 300);

            return { success: true, reason: 'ok' };
        } finally {
            await this.redis.del(lockKey);
        }
    }

    async closePair(symA: string, symB: string, reason: string): Promise<{ success: boolean }> {
        // Grace Period check (Bug #4)
        if (reason === 'sl') {
            const pos = await this.stateManager.getActivePositions();
            const p = pos.find(x => x.symbol_a === symA && x.symbol_b === symB);
            if (p) {
                const graceActive = await this.redis.exists(`grace:${p.group_id}`);
                if (graceActive) return { success: false }; // SL blocked by grace
            }
        }

        // Close both legs
        await this.exchange.closePosition(symA);
        await this.exchange.closePosition(symB);

        // ═══ Post-Close Verification ═══
        await this.sleep(2000);
        const stillA = await this.exchange.hasPosition(symA);
        const stillB = await this.exchange.hasPosition(symB);
        if (stillA || stillB) {
            console.error(`⚠️ Post-close verification failed: A=${stillA} B=${stillB}`);
        }

        await this.stateManager.closePosition(symA, symB, reason, 0);
        return { success: true };
    }

    private sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }
}
