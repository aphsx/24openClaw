# PAIRS TRADING SYSTEM — ฉบับสมบูรณ์

> Prompt นี้รวมทุกอย่าง: กลยุทธ์ + แก้ Bug 26 ข้อ + Scanner + Trading Logic
> คัดลอกทั้งหมดส่งให้ Claude Code → สร้างระบบที่ทำงานได้จริง
> ผู้ใช้จะเอาไปต่อยอดทำ Dashboard เอง

---

## PART 1: กลยุทธ์ Pairs Trading

### แนวคิด

เหรียญ A กับ B เคลื่อนไหวคล้ายกัน (Correlation สูง)
วันหนึ่ง A กับ B ถ่างออกจากกัน → เราเข้าเทรด
เมื่อ A กับ B กลับมาบรรจบ → เราปิดทำกำไร

ทำกำไรจาก "ช่วงถ่าง" ไม่สนว่าตลาดจะขึ้นหรือลง (Market Neutral)

### อินดิเคเตอร์ 6 ตัว

```
1. Correlation (Pearson)     → คัดคู่ที่เคลื่อนไหวคล้ายกัน (≥ 0.80)
2. Cointegration / Hurst     → ยืนยันว่า "ถ่างแล้วจะกลับมาหากัน"
3. Spread                    → ส่วนต่างราคา: A − (β × B)
4. Z-Score ★                 → วัดว่า Spread ถ่างออกกี่ SD (ตัวจับสัญญาณหลัก)
5. Half-Life                 → วัดว่า Spread กลับมาหาค่ากลางใช้เวลานานเท่าไร
6. Hedge Ratio (β)           → สัดส่วนที่ต้องเทรดแต่ละขา
```

### Entry / Exit / TP / SL

```
ENTRY:
  Z-Score > +2.0 → Short A, Long B (A แพงเกินไป)
  Z-Score < -2.0 → Long A, Short B (A ถูกเกินไป)
  ต้องอยู่ใน Safe Zone: |Z| ≤ 2.5 เมื่อ SL = 3.0

TAKE PROFIT:
  Z-Score กลับมาที่ ±0.5 ถึง 0 → ปิดทั้ง 2 ขา

STOP LOSS:
  Z-Score เกิน ±3.0 → ตัดทิ้ง
  ถือเกิน 2× Half-Life → Time Stop
  Correlation ลดต่ำกว่า 0.50 → Correlation Break

GRACE PERIOD:
  หลังเปิด 5 นาที ห้าม Trigger SL (ป้องกัน Bug #4: SL ใน 6 วินาที)
```

### Position Sizing

```
ขาละ $500 (ปรับได้ใน Config)
Hedge Ratio: ถ้า β = 1.3 → Long A $500, Short B $650
จำกัด 5-10% ของพอร์ตต่อคู่
```

### ระยะเวลาถือ

```
Large Cap (BTC/ETH):     7-14 วัน
Mid Cap (LINK/DOT):      3-7 วัน
Small/Meme (FLOKI/MEME): 1-5 วัน
สูตร: Half-Life × 0.5 ถึง × 2.0
```

---

## PART 2: Bug 26 ข้อที่ต้องแก้ — เป็นโค้ดจริงทุกข้อ

### สิ่งที่ต้องสร้าง

```
pairs-trading/
├── docker-compose.yml
├── .env
├── db/init.sql
├── src/
│   ├── index.ts                 ← Entry point
│   ├── core/
│   │   ├── state-manager.ts     ← Bug #1: DB-First
│   │   ├── reconciliation.ts    ← Bug #1: Orphan = Alert Only
│   │   ├── validator.ts         ← Bug #2: Pre-Order Validation
│   │   ├── executor.ts          ← Bug #2: Atomic + Rollback
│   │   ├── dedup.ts             ← Bug #3: 5-Layer Dedup
│   │   ├── safe-zone.ts         ← Bug #4: Safe Entry Zone + Grace
│   │   ├── lifecycle.ts         ← Bug #5: Instance Cleanup
│   │   ├── config-manager.ts    ← Bug #6: Config from DB
│   │   ├── indicators.ts        ← Math + Division Guards
│   │   └── scanner.ts           ← Scanner Logic
│   ├── exchange/
│   │   └── okx-client.ts        ← OKX API via ccxt
│   ├── api/
│   │   └── routes.ts            ← REST API for Dashboard
│   └── types.ts
├── tests/                       ← Test ทุก Bug
└── package.json
```

### Tech Stack

```
Runtime:    Node.js + TypeScript
Database:   PostgreSQL 16 (Source of Truth)
Cache:      Redis 7 (Real-time + Dedup + Locks)
Exchange:   ccxt → OKX (Public API สำหรับสแกน)
Validation: zod
Container:  Docker Compose
Test:       vitest
```

---

### DATABASE SCHEMA

```sql
-- file: db/init.sql

CREATE TABLE instruments (
    symbol      VARCHAR(20) PRIMARY KEY,
    has_futures BOOLEAN DEFAULT true,
    vol_24h     DECIMAL(20,2),
    last_price  DECIMAL(20,10),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ohlcv_daily (
    symbol VARCHAR(20) NOT NULL,
    ts     DATE NOT NULL,
    close  DECIMAL(20,10) NOT NULL,
    volume DECIMAL(20,4),
    PRIMARY KEY (symbol, ts)
);

CREATE TABLE pairs (
    id              SERIAL PRIMARY KEY,
    symbol_a        VARCHAR(20) NOT NULL,
    symbol_b        VARCHAR(20) NOT NULL,
    correlation     DECIMAL(6,4),
    hurst_exp       DECIMAL(6,4),
    half_life       DECIMAL(8,2),
    hedge_ratio     DECIMAL(10,6),
    zscore          DECIMAL(8,4),
    zone            VARCHAR(10),
    qualified       BOOLEAN DEFAULT false,
    validation_json JSONB,
    scanned_at      TIMESTAMPTZ,
    UNIQUE(symbol_a, symbol_b)
);

CREATE TABLE trades (
    id              SERIAL PRIMARY KEY,
    group_id        UUID NOT NULL UNIQUE,
    symbol_a        VARCHAR(20) NOT NULL,
    symbol_b        VARCHAR(20) NOT NULL,
    leg_a_side      VARCHAR(5) NOT NULL,
    leg_a_size_usd  DECIMAL(12,2),
    leg_a_order_id  VARCHAR(100),
    leg_b_side      VARCHAR(5) NOT NULL,
    leg_b_size_usd  DECIMAL(12,2),
    leg_b_order_id  VARCHAR(100),
    entry_zscore    DECIMAL(8,4),
    entry_corr      DECIMAL(6,4),
    entry_beta      DECIMAL(10,6),
    entry_zone      VARCHAR(10),
    exit_zscore     DECIMAL(8,4),
    exit_reason     VARCHAR(20),
    pnl_usd         DECIMAL(12,2),
    funding_paid    DECIMAL(12,4),
    fees_paid       DECIMAL(12,4),
    status          VARCHAR(20) DEFAULT 'open',
    validation_json JSONB,
    opened_at       TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);
CREATE INDEX idx_trades_status ON trades(status);

CREATE TABLE reconciliation_logs (
    id           SERIAL PRIMARY KEY,
    checked_at   TIMESTAMPTZ DEFAULT NOW(),
    db_count     INTEGER,
    exchange_count INTEGER,
    orphans      INTEGER DEFAULT 0,
    action       VARCHAR(20) DEFAULT 'alert_only',
    details      JSONB
);

CREATE TABLE scan_results (
    id          SERIAL PRIMARY KEY,
    scanned_at  TIMESTAMPTZ DEFAULT NOW(),
    total_pairs INTEGER,
    qualified   INTEGER,
    signals     INTEGER,
    blocked     INTEGER,
    duration_ms INTEGER,
    details     JSONB
);

CREATE TABLE config (
    key         VARCHAR(50) PRIMARY KEY,
    value       DECIMAL(12,6) NOT NULL,
    description TEXT,
    backtest_rank  INTEGER,
    backtest_total INTEGER,
    last_optimized TIMESTAMPTZ
);

INSERT INTO config (key, value, description) VALUES
('zscore_entry',      2.0,    'Z-Score entry threshold'),
('zscore_tp',         0.5,    'Z-Score take profit'),
('zscore_sl',         3.0,    'Z-Score stop loss'),
('corr_min',          0.80,   'Minimum correlation'),
('half_life_min',     5,      'Min half-life days'),
('half_life_max',     30,     'Max half-life days'),
('safe_buffer',       0.5,    'Buffer from SL for safe zone'),
('grace_period_sec',  300,    'Grace period seconds'),
('cooldown_sec',      3600,   'Cooldown after close'),
('max_same_coin',     2,      'Max pairs per coin'),
('position_size_usd', 500,    'USD per leg'),
('scan_interval_sec', 60,     'Scan interval');
```

### REDIS KEYS

```
price:{symbol}                       → ราคาล่าสุด          TTL 60s
zscore:{symA}:{symB}                 → Z-Score              TTL 300s
position:active:{symA}:{symB}        → group_id             ไม่มี TTL
cooldown:{symA}:{symB}               → "1"                  TTL 3600s
exposure:{symbol}                    → count                ไม่มี TTL
grace:{groupId}                      → "1"                  TTL 300s
lock:trade:{symA}:{symB}             → "1"                  TTL 30s
lock:scan                            → "1"                  TTL 120s
```

---

### BUG #1: DB-FIRST — state-manager.ts

ปัญหา: เก็บใน memory → restart แล้วหาย → orphan detection ปิดออเดอร์ดีทิ้ง
แก้: ทุก state → DB ก่อน → Cache Redis → ถ้า Redis หาย rebuild จาก DB

```typescript
// file: src/core/state-manager.ts

import { Pool } from 'pg';
import Redis from 'ioredis';

export class StateManager {
  constructor(private db: Pool, private redis: Redis) {}

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
```

### BUG #1 (ต่อ): RECONCILIATION — Orphan = Alert Only ห้าม Auto-Close

```typescript
// file: src/core/reconciliation.ts

export class ReconciliationService {
  constructor(
    private stateManager: StateManager,
    private exchange: OKXClient,
    private db: Pool
  ) {}

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
```

---

### BUG #2: VALIDATE + ATOMIC EXECUTION + ROLLBACK

ปัญหา: ราคา=0 → Size=Infinity → Leg A สำเร็จ Leg B fail → Orphan ค้าง
แก้: ตรวจทุกอย่างก่อนส่ง + ถ้า Leg B fail → ปิด Leg A ทันที + ตรวจว่าปิดจริง

```typescript
// file: src/core/validator.ts

import { z } from 'zod';

const OrderParamsSchema = z.object({
  symbol: z.string().min(1),
  side: z.enum(['buy', 'sell']),
  sizeUsd: z.number().positive().finite().refine(v => !isNaN(v)),
  price: z.number().positive().finite(),
});

export class PreOrderValidator {
  constructor(private exchange: OKXClient, private config: ConfigManager) {}

  async validate(signal: PairSignal): Promise<{ pass: boolean; checks: Check[] }> {
    const checks: Check[] = [];
    const c = (name: string, pass: boolean, detail: string) =>
      checks.push({ name, pass, detail });

    // 1. Futures มีจริง
    const instA = await this.exchange.getInstrument(signal.symbolA);
    const instB = await this.exchange.getInstrument(signal.symbolB);
    c('futures_exist', !!instA && !!instB,
      `A:${!!instA} B:${!!instB}`);

    // 2. ราคา > 0
    const pxA = instA?.lastPrice || 0;
    const pxB = instB?.lastPrice || 0;
    c('price_positive', pxA > 0 && pxB > 0,
      `A:${pxA} B:${pxB}`);

    // 3. β valid (ไม่ Infinity ไม่ NaN)
    const betaOk = isFinite(signal.beta) && !isNaN(signal.beta) && signal.beta > 0;
    c('beta_valid', betaOk, `β=${signal.beta}`);

    // 4. Size valid
    if (pxA > 0 && pxB > 0 && betaOk) {
      const sizeUsd = await this.config.get('position_size_usd');
      const sA = OrderParamsSchema.safeParse({ symbol: signal.symbolA, side: 'buy', sizeUsd, price: pxA });
      const sB = OrderParamsSchema.safeParse({ symbol: signal.symbolB, side: 'sell', sizeUsd: sizeUsd * signal.beta, price: pxB });
      c('size_valid', sA.success && sB.success,
        `A:${sA.success} B:${sB.success}`);
    } else {
      c('size_valid', false, 'ข้ามเพราะ price/beta ไม่ผ่าน');
    }

    // 5. Correlation
    const corrMin = await this.config.get('corr_min');
    c('correlation', signal.correlation >= corrMin,
      `${signal.correlation.toFixed(3)} ≥ ${corrMin}`);

    // 6. Half-Life
    const hlMin = await this.config.get('half_life_min');
    const hlMax = await this.config.get('half_life_max');
    c('half_life', signal.halfLife >= hlMin && signal.halfLife <= hlMax,
      `${signal.halfLife.toFixed(1)}d [${hlMin}-${hlMax}]`);

    // 7. Volume > $20M (ป้องกัน Liquidity Trap)
    c('volume', (instA?.vol24h || 0) > 20e6 && (instB?.vol24h || 0) > 20e6,
      `A:$${((instA?.vol24h || 0) / 1e6).toFixed(0)}M B:$${((instB?.vol24h || 0) / 1e6).toFixed(0)}M`);

    return { pass: checks.every(c => c.pass), checks };
  }
}
```

```typescript
// file: src/core/executor.ts

export class AtomicExecutor {
  constructor(
    private exchange: OKXClient,
    private stateManager: StateManager,
    private redis: Redis
  ) {}

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
      } catch (e) {
        return { success: false, reason: `leg_a_failed: ${e.message}` };
      }

      // ═══ Leg B ═══
      let legB;
      try {
        legB = await this.exchange.placeOrder(signal.symbolB, signal.legBSide, signal.sizeB);
      } catch (e) {
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
```

---

### BUG #3: DEDUP 5 ชั้น

ปัญหา: เปิดออเดอร์ซ้ำ สัญญาณซ้ำ แจ้งเตือนซ้ำ
แก้: ตรวจ 5 ชั้น ผ่านหมดถึงจะเปิดได้

```typescript
// file: src/core/dedup.ts

export class DedupService {
  constructor(private db: Pool, private redis: Redis, private exchange: OKXClient) {}

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

    // ชั้น 5: Concentration (ห้ามใช้เหรียญเดียวกันเกิน N คู่)
    const expA = parseInt(await this.redis.get(`exposure:${symA}`) || '0');
    const expB = parseInt(await this.redis.get(`exposure:${symB}`) || '0');
    checks.push({ layer: 5, name: 'concentration', pass: expA < maxSameCoin && expB < maxSameCoin,
      detail: `${symA}:${expA} ${symB}:${expB} max:${maxSameCoin}` });

    return { pass: checks.every(c => c.pass), checks };
  }
}
```

---

### BUG #4: SAFE ENTRY ZONE + GRACE PERIOD

ปัญหา: เปิดที่ Z=3.607 ทั้งที่ SL=3.5 → โดน SL ใน 6 วินาที เกิดซ้ำ 48 ครั้ง
แก้: Safe Zone + Grace Period

```typescript
// file: src/core/safe-zone.ts

export function classifyZone(zscore: number, config: {
  zscore_entry: number; zscore_sl: number; safe_buffer: number;
}): { zone: 'safe' | 'caution' | 'danger' | 'none'; canOpen: boolean; sizePct: number } {
  const absZ = Math.abs(zscore);
  const safeMax = config.zscore_sl - config.safe_buffer; // เช่น 3.0 - 0.5 = 2.5

  if (absZ < config.zscore_entry) return { zone: 'none', canOpen: false, sizePct: 0 };
  if (absZ > safeMax)             return { zone: 'danger', canOpen: false, sizePct: 0 };
  if (absZ > safeMax - 0.2)       return { zone: 'caution', canOpen: true, sizePct: 50 };
  return { zone: 'safe', canOpen: true, sizePct: 100 };
}

// Grace Period: ใช้ Redis TTL ใน executor.ts
// SET grace:{groupId} 1 EX 300
// ก่อน trigger SL → เช็ค EXISTS grace:{groupId} → ถ้ามี → ข้าม SL
```

---

### BUG #5: LIFECYCLE MANAGEMENT

ปัญหา: Hot reload สร้าง instance ซ้ำ scheduler/bot ทำงานซ้อน
แก้: Cleanup ก่อน start + Graceful shutdown

```typescript
// file: src/core/lifecycle.ts

export class LifecycleManager {
  private intervals: NodeJS.Timeout[] = [];

  constructor(private redis: Redis, private db: Pool, private stateManager: StateManager) {}

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
```

---

### BUG #6: CONFIG FROM DB

ปัญหา: Config ตั้งจากการเดา ติดอันดับ 421 จาก 540
แก้: Config อยู่ใน DB + แจ้งเตือน needsBacktest

```typescript
// file: src/core/config-manager.ts

export class ConfigManager {
  private cache: Map<string, number> = new Map();

  constructor(private db: Pool) {}

  async load(): Promise<void> {
    const { rows } = await this.db.query('SELECT key, value FROM config');
    this.cache.clear();
    rows.forEach(r => this.cache.set(r.key, parseFloat(r.value)));
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
    return Object.fromEntries(rows.map(r => [r.key, {
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
```

---

### INDICATORS — ทุกจุดที่หาร ตรวจ ÷0

```typescript
// file: src/core/indicators.ts

export function correlation(a: number[], b: number[]): number | null {
  if (a.length !== b.length || a.length < 10) return null;
  const mA = mean(a), mB = mean(b);
  const sA = stddev(a), sB = stddev(b);
  if (sA === 0 || sB === 0) return null;
  const cov = a.reduce((s, v, i) => s + (v - mA) * (b[i] - mB), 0) / a.length;
  const r = cov / (sA * sB);
  return isFinite(r) ? Math.max(-1, Math.min(1, r)) : null;
}

export function hedgeRatio(a: number[], b: number[]): number | null {
  const vB = variance(b);
  if (vB === 0) return null;
  const cov = covariance(a, b);
  const beta = cov / vB;
  return isFinite(beta) && !isNaN(beta) && beta > 0 ? beta : null;
}

export function spread(priceA: number, priceB: number, beta: number): number | null {
  if (!isFinite(beta) || priceB <= 0) return null;
  return priceA - beta * priceB;
}

export function zScore(currentSpread: number, meanSpread: number, sdSpread: number): number | null {
  if (sdSpread === 0 || !isFinite(sdSpread)) return null;
  const z = (currentSpread - meanSpread) / sdSpread;
  return isFinite(z) ? z : null;
}

export function halfLife(spreads: number[]): number | null {
  if (spreads.length < 20) return null;
  const lag = spreads.slice(0, -1);
  const delta = spreads.slice(1).map((s, i) => s - lag[i]);
  const mLag = mean(lag);
  const devLag = lag.map(l => l - mLag);
  const vLag = variance(devLag);
  if (vLag === 0) return null;
  const lambda = covariance(delta, devLag) / vLag;
  if (lambda >= 0) return null; // ไม่ mean-revert
  const hl = -Math.log(2) / lambda;
  return isFinite(hl) && hl > 0 ? hl : null;
}

export function hurstExponent(series: number[]): number | null {
  if (series.length < 20) return null;
  const n = series.length;
  const m = mean(series);
  const dev = series.map(x => x - m);
  let cumSum = 0;
  const cumDev = dev.map(d => (cumSum += d, cumSum));
  const R = Math.max(...cumDev) - Math.min(...cumDev);
  const S = stddev(series);
  if (S === 0 || R === 0) return null;
  const H = Math.log(R / S) / Math.log(n);
  return isFinite(H) ? H : null;
  // H < 0.5 = mean-reverting (ดี)
  // H > 0.5 = trending (ไม่ดี)
}

// Helpers
function mean(arr: number[]): number { return arr.reduce((a, b) => a + b, 0) / arr.length; }
function variance(arr: number[]): number {
  const m = mean(arr);
  return arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length;
}
function stddev(arr: number[]): number { return Math.sqrt(variance(arr)); }
function covariance(a: number[], b: number[]): number {
  const mA = mean(a), mB = mean(b);
  return a.reduce((s, v, i) => s + (v - mA) * (b[i] - mB), 0) / a.length;
}
```

---

## PART 3: SCANNER — สแกนจากตลาดจริง

```typescript
// file: src/core/scanner.ts

import ccxt from 'ccxt';
import * as ind from './indicators';
import { classifyZone } from './safe-zone';

export class PairsScanner {
  private exchange: ccxt.okx;

  constructor(
    private db: Pool,
    private redis: Redis,
    private config: ConfigManager,
    private dedup: DedupService
  ) {
    this.exchange = new ccxt.okx({ enableRateLimit: true });
  }

  async scan(): Promise<ScanResult> {
    const start = Date.now();

    // ═══ Lock ป้องกันสแกนซ้อน (Bug #5) ═══
    const locked = await this.redis.set('lock:scan', '1', 'EX', 120, 'NX');
    if (!locked) return { skipped: true, reason: 'scan_in_progress' };

    try {
      // ═══ Step 1: ดึงรายชื่อเหรียญ ═══
      const markets = await this.exchange.loadMarkets();
      const symbols = Object.keys(markets).filter(s =>
        markets[s].swap && markets[s].quote === 'USDT' && markets[s].active
      );

      // ═══ Step 2: ดึง Ticker กรอง Volume > $20M ═══
      const tickers = await this.exchange.fetchTickers(symbols);
      const qualified = Object.entries(tickers)
        .filter(([_, t]) => (t.quoteVolume || 0) > 20_000_000)
        .map(([sym, t]) => ({ symbol: sym.split('/')[0], price: t.last, vol: t.quoteVolume }))
        .slice(0, 25); // จำกัด 25 เหรียญ (325 คู่)

      // ═══ Step 3: ดึง OHLCV 180 วัน (cached ใน DB) ═══
      const closes: Record<string, number[]> = {};
      for (const coin of qualified) {
        closes[coin.symbol] = await this.getCloses(coin.symbol, 180);
        await this.sleep(100); // Rate limit
      }

      // ═══ Step 4: คำนวณทุกคู่ ═══
      const pairs: PairResult[] = [];
      const symbolList = qualified.map(c => c.symbol);
      const cfgEntry = await this.config.get('zscore_entry');
      const cfgSl = await this.config.get('zscore_sl');
      const cfgBuf = await this.config.get('safe_buffer');
      const cfgCorr = await this.config.get('corr_min');
      const cfgHlMin = await this.config.get('half_life_min');
      const cfgHlMax = await this.config.get('half_life_max');
      const cfgMaxCoin = await this.config.get('max_same_coin');

      for (let i = 0; i < symbolList.length; i++) {
        for (let j = i + 1; j < symbolList.length; j++) {
          const symA = symbolList[i];
          const symB = symbolList[j];
          const cA = closes[symA];
          const cB = closes[symB];
          if (!cA || !cB || cA.length < 60 || cB.length < 60) continue;

          // ตัดให้ยาวเท่ากัน
          const len = Math.min(cA.length, cB.length);
          const a = cA.slice(-len);
          const b = cB.slice(-len);

          // Correlation
          const corr = ind.correlation(a, b);
          if (corr === null || corr < cfgCorr) continue;

          // Hedge Ratio
          const beta = ind.hedgeRatio(a, b);
          if (beta === null) continue;

          // Spread series
          const spreads = a.map((v, idx) => v - beta * b[idx]);

          // Half-Life
          const hl = ind.halfLife(spreads);
          if (hl === null || hl < cfgHlMin || hl > cfgHlMax) continue;

          // Hurst (ต้อง < 0.5 = mean-reverting)
          const hurst = ind.hurstExponent(spreads);
          if (hurst === null || hurst >= 0.5) continue;

          // Z-Score
          const recent60 = spreads.slice(-60);
          const spreadMean = recent60.reduce((a, b) => a + b, 0) / recent60.length;
          const spreadSd = Math.sqrt(recent60.reduce((s, v) => s + (v - spreadMean) ** 2, 0) / recent60.length);
          const z = ind.zScore(spreads[spreads.length - 1], spreadMean, spreadSd);
          if (z === null) continue;

          // Zone classification
          const zone = classifyZone(z, { zscore_entry: cfgEntry, zscore_sl: cfgSl, safe_buffer: cfgBuf });

          // Dedup check
          const dedupResult = await this.dedup.canOpen(symA, symB, cfgMaxCoin);

          // Direction
          const direction = z > 0 ? { legA: 'sell', legB: 'buy' } : { legA: 'buy', legB: 'sell' };

          pairs.push({
            symbolA: symA, symbolB: symB,
            correlation: corr, hurst, halfLife: hl, hedgeRatio: beta,
            zscore: z, zone: zone.zone, canOpen: zone.canOpen && dedupResult.pass,
            sizePct: zone.sizePct, direction,
            dedupChecks: dedupResult.checks,
            blocked: Math.abs(z) >= cfgEntry && (!zone.canOpen || !dedupResult.pass),
            blockReason: !zone.canOpen ? `Zone: ${zone.zone}` : !dedupResult.pass ? 'Dedup failed' : null,
          });
        }
      }

      // Sort: signals first → then |Z| descending
      pairs.sort((a, b) => {
        if (a.canOpen && !b.canOpen) return -1;
        if (!a.canOpen && b.canOpen) return 1;
        return Math.abs(b.zscore) - Math.abs(a.zscore);
      });

      // ═══ Step 5: บันทึก DB ═══
      const signals = pairs.filter(p => p.canOpen);
      const blocked = pairs.filter(p => p.blocked);

      // Upsert pairs table
      for (const p of pairs) {
        await this.db.query(
          `INSERT INTO pairs (symbol_a, symbol_b, correlation, hurst_exp, half_life,
           hedge_ratio, zscore, zone, qualified, validation_json, scanned_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
           ON CONFLICT (symbol_a, symbol_b) DO UPDATE SET
           correlation=$3, hurst_exp=$4, half_life=$5, hedge_ratio=$6,
           zscore=$7, zone=$8, qualified=$9, validation_json=$10, scanned_at=NOW()`,
          [p.symbolA, p.symbolB, p.correlation, p.hurst, p.halfLife,
           p.hedgeRatio, p.zscore, p.zone, p.canOpen,
           JSON.stringify({ zone: p.zone, sizePct: p.sizePct, direction: p.direction, dedup: p.dedupChecks })]
        );

        // Cache Z-Score ใน Redis
        await this.redis.set(`zscore:${p.symbolA}:${p.symbolB}`, p.zscore.toString(), 'EX', 300);
      }

      const duration = Date.now() - start;
      await this.db.query(
        `INSERT INTO scan_results (total_pairs, qualified, signals, blocked, duration_ms, details)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [pairs.length, pairs.filter(p => p.correlation >= cfgCorr).length,
         signals.length, blocked.length, duration, JSON.stringify(signals.slice(0, 10))]
      );

      return { pairs, signals, blocked, duration, total: pairs.length };

    } finally {
      await this.redis.del('lock:scan');
    }
  }

  private async getCloses(symbol: string, days: number): Promise<number[]> {
    // ดึงจาก DB cache ก่อน
    const { rows } = await this.db.query(
      `SELECT close FROM ohlcv_daily WHERE symbol=$1 ORDER BY ts DESC LIMIT $2`,
      [symbol, days]
    );
    if (rows.length >= days * 0.8) {
      return rows.map(r => parseFloat(r.close)).reverse();
    }

    // ถ้าไม่พอ ดึงจาก OKX
    try {
      const since = this.exchange.parse8601(
        new Date(Date.now() - days * 86400000).toISOString()
      );
      const ohlcv = await this.exchange.fetchOHLCV(
        `${symbol}/USDT:USDT`, '1d', since, days
      );
      // เก็บ DB
      for (const [ts, o, h, l, c, v] of ohlcv) {
        const date = new Date(ts).toISOString().split('T')[0];
        await this.db.query(
          `INSERT INTO ohlcv_daily (symbol, ts, close, volume)
           VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
          [symbol, date, c, v]
        );
      }
      return ohlcv.map(c => c[4]); // close prices
    } catch (e) {
      console.error(`Failed to fetch OHLCV for ${symbol}: ${e.message}`);
      return [];
    }
  }

  private sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }
}
```

---

## PART 4: REST API สำหรับ Dashboard

```typescript
// file: src/api/routes.ts
// ใช้ Fastify หรือ Express

export function registerRoutes(app, { scanner, stateManager, configManager, db }) {

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

  app.put('/api/config/:key', async (req) => {
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
```

---

## PART 5: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: pairs_trading
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes: [redisdata:/data]
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  app:
    build: .
    restart: always
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    environment:
      DATABASE_URL: postgresql://trader:${DB_PASSWORD:-changeme}@postgres:5432/pairs_trading
      REDIS_URL: redis://redis:6379
    ports: ["3001:3001"]

volumes:
  pgdata:
  redisdata:
```

---

## PART 6: ENTRY POINT

```typescript
// file: src/index.ts

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

async function main() {
  const db = new Pool({ connectionString: process.env.DATABASE_URL });
  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

  const stateManager = new StateManager(db, redis);
  const configManager = new ConfigManager(db);
  const dedup = new DedupService(db, redis, null); // exchange ใส่ทีหลัง
  const scanner = new PairsScanner(db, redis, configManager, dedup);
  const reconciliation = new ReconciliationService(stateManager, null, db);
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
    } catch (e) {
      console.error('[Scan Error]', e.message);
    }
  }, scanInterval * 1000);

  // ═══ Reconciliation ทุก 5 นาที ═══
  lifecycle.addInterval(async () => {
    try { await reconciliation.run(); } catch (e) { console.error('[Recon Error]', e.message); }
  }, 300_000);

  console.log('System running. Scanner active.');
}

main().catch(console.error);
```

---

## PART 7: BUILD ORDER สำหรับ Claude Code

```
ให้ Build ตามลำดับนี้ ทุก Step ต้อง Test ก่อนไป Step ถัดไป:

Step 1:  docker-compose.yml + .env + db/init.sql
         → docker compose up -d postgres redis

Step 2:  src/core/indicators.ts + tests
         → ทุก Math ต้องมี ÷0 guard
         → test: null เมื่อ stddev=0, variance=0, price=0

Step 3:  src/core/safe-zone.ts + tests
         → test: danger/caution/safe/none classification

Step 4:  src/core/config-manager.ts
         → อ่าน/เขียน Config จาก DB

Step 5:  src/core/state-manager.ts + tests
         → DB-First, rebuildCache
         → test: position survives "restart"

Step 6:  src/core/dedup.ts + tests
         → 5-layer check
         → test: block duplicate, block cooldown, block concentration

Step 7:  src/core/executor.ts + tests
         → Atomic + Rollback + Post-Close Verify + Grace
         → test: rollback เมื่อ Leg B fail

Step 8:  src/core/reconciliation.ts + tests
         → Orphan = Alert Only
         → test: ห้าม auto-close

Step 9:  src/core/lifecycle.ts
         → Startup cleanup + Shutdown

Step 10: src/core/scanner.ts
         → เชื่อม OKX Public API จริงผ่าน ccxt
         → สแกนคู่จริง คำนวณจริง บันทึก DB จริง

Step 11: src/api/routes.ts
         → REST API สำหรับ Dashboard

Step 12: src/index.ts
         → รวมทุกอย่าง + Auto Scan + Reconciliation

ผลลัพธ์: Backend ที่สแกนตลาดจริงทุก 60 วินาที
        มี API พร้อมให้ Frontend ดึงข้อมูลไปแสดง Dashboard
```

---

## BUG CHECKLIST — ต้องผ่านทุกข้อ

```
หมวด 1: ข้อมูลหาย (Bug #1)
 ☐ ทุก State → DB ก่อน Redis
 ☐ Startup rebuild Redis จาก DB
 ☐ Orphan = Alert Only ห้าม Auto-Close
 ☐ Reconciliation ทุก 5 นาที + Log
 ☐ Docker volumes persist

หมวด 2: คำสั่งผิด (Bug #2)
 ☐ Price > 0 validation
 ☐ Size ≠ Infinity/NaN (zod)
 ☐ β > 0, finite, not NaN
 ☐ Futures contract exists
 ☐ Atomic 2-Leg execution
 ☐ Rollback Leg A ถ้า Leg B fail
 ☐ Post-Close Verification

หมวด 3: ซ้ำซ้อน (Bug #3)
 ☐ Dedup Layer 1: Redis
 ☐ Dedup Layer 2: Database
 ☐ Dedup Layer 3: Exchange
 ☐ Dedup Layer 4: Cooldown
 ☐ Dedup Layer 5: Concentration

หมวด 4: Safe Entry (Bug #4)
 ☐ Danger Zone → Block
 ☐ Caution Zone → 50%
 ☐ Safe Zone → 100%
 ☐ Grace Period 5 นาที ห้าม SL

หมวด 5: Instance ซ้ำ (Bug #5)
 ☐ Cleanup locks on startup
 ☐ Scan lock ป้องกันซ้อน
 ☐ Graceful shutdown
 ☐ Process signal handlers

หมวด 6: Config (Bug #6)
 ☐ Config ใน DB ไม่ Hardcode
 ☐ needsBacktest flag
 ☐ API อ่าน/แก้ Config

Math Safety:
 ☐ correlation: guard stddev=0
 ☐ hedgeRatio: guard variance=0
 ☐ zScore: guard sd=0
 ☐ halfLife: guard variance=0 + lambda≥0
 ☐ hurstExponent: guard S=0
 ☐ positionSize: guard price=0 + beta=0

รวม 26 bugs + math guards = ทุกข้อต้องมี Test
```
