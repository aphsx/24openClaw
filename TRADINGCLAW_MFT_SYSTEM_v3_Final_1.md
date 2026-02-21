# tradingclaw MFT SYSTEM — FINAL ENGINEERING BLUEPRINT v3.0

---

## สรุปสิ่งที่เปลี่ยนจาก v2.1

| หัวข้อ | v2.1 (เดิม) | v3.0 (แก้ไข) | เหตุผล |
|--------|-------------|---------------|--------|
| Ghost Orders | 3 layers, มี decoy | 3 layers (ทุน >$1K), ไม่มี decoy | Decoy เสี่ยง ban, ทุนน้อย layer ไม่มีประโยชน์ |
| AI Predictor | Dual-path ตั้งแต่ต้น | Phase 1: Fast Path only, Phase 2: เพิ่ม LiT/TLOB | เก็บ data ก่อน 2-3 เดือน แล้วค่อย train |
| ภาษา | Rust ตั้งแต่ต้น | Rust ตั้งแต่ต้น (ตามที่ต้องการฝึก) | เรียนรู้ Rust ควบคู่กับ build system |
| Lead-Lag update | ทุก 2 ชั่วโมง | Micro: 30 วินาที / Macro: 30 นาที | Lead-lag เปลี่ยนเร็วกว่าที่คิด |
| Alpha weights | Fixed | Adaptive (online learning) | Market regime เปลี่ยนตลอด |
| เหรียญ selection | Manual | Auto Scanner แยก binary (Phase 0 validate + Runtime scanner) | ทั้งสองอย่างจำเป็น ใช้ด้วยกัน |
| Validation Phase | ไม่มี | Phase 0 บังคับ ก่อน live | ป้องกันเสียเงินกับ strategy ที่ไม่ work |
| Stop Loss | Fixed 0.5% | Adaptive: max(0.3%, min(1.0%, 2×ATR_1min)) | ปรับตาม volatility จริง |
| Profit estimate | 10.7%/เดือน ด้วย $100 | 3-10%/เดือน ด้วย $1,000+ (หลัง tune 2-3 เดือน) | รวม fill rate + realistic win rate |

---

## SECTION 0: DOCUMENT INFORMATION (อัพเดท)

```
Project Name: tradingclaw Phase 1
Strategy Name: Cross-Exchange Informed Flow Arbitrage (CEIFA)
Language: Rust (ทั้ง Validation และ Production)
Target Exchanges: Binance Futures (Signal Source), Bybit Linear (Execution), OKX Futures (Secondary Signal)
Base Latency: 30-40ms (Thailand → Singapore/Tokyo)
Capital Range: $1,000 - $10,000 (แนะนำเริ่ม $1,000+)
Trading Frequency: Medium-Frequency (200ms - 30 second holding periods)
Version: 3.0 Final
```

---

## SECTION 1: GHOST ORDER STRATEGY (แก้ไขใหม่ทั้งหมด)

### 1.1 คำตอบตรงๆ: Ghost Orders ดีไหม?

**คำตอบ: ดี — เมื่อใช้ถูกเงื่อนไข**

Ghost Orders (Multi-Layer Order Placement) เป็นเทคนิคที่ institutional market makers ใช้จริง ข้อดีมีจริง 3 ข้อ:

ข้อดีที่ 1: เพิ่ม fill rate — วาง 3 ราคาแทน 1 ราคา = โอกาส fill สูงขึ้น 40-70% เทียบกับ single order

ข้อดีที่ 2: ได้ราคาเฉลี่ยที่ดีขึ้น — Layer ที่อยู่ลึกกว่า (ราคาดีกว่า) ถ้าถูก fill = กำไรต่อ unit สูงกว่า

ข้อดีที่ 3: ป้องกัน pattern detection — HFT ที่ scan LOB จะเห็น order ของเราเป็น noise ไม่ใช่ pattern ชัดเจน

**แต่มีเงื่อนไข:**

เงื่อนไขที่ 1 — ทุนต้องพอ: แต่ละ layer ต้องมี size มากกว่า minimum order ของ exchange ถ้า Bybit LINK min = 1 LINK ($14) และวาง 3 layers = ต้องมี $42 deploy ต่อ trade ด้วย Kelly 4.6% = ต้องมีทุน $42/0.046 = $913 ขึ้นไป ดังนั้น ทุน $1,000+ Ghost Orders ใช้ได้

เงื่อนไขที่ 2 — ไม่ทำ Decoy Orders เด็ดขาด: ในเอกสารเดิมมี "ส่ง order ที่ไม่ตั้งใจ fill แล้ว cancel ใน 500ms" — อันนี้ตัดออก เพราะ:
- Bybit มี surveillance system ตรวจจับ spoofing
- ถูก flag = โดน warning → ban → เสีย account
- ไม่คุ้มเสี่ยงเลย

เงื่อนไขที่ 3 — Randomization ต้องเป็น natural ไม่ใช่ artificial:
- Size jitter Uniform(0.92, 1.08) → ดี เก็บไว้
- Timing jitter 0-3ms → ดี เก็บไว้
- สลับลำดับ layer → ดี เก็บไว้
- Decoy orders → ตัดออก

### 1.2 Ghost Order Configuration (Final Version)

**Tier 1: ทุน $500 - $999**
```
จำนวน Layers: 1 (Single Order)
เหตุผล: ทุนไม่พอ layer, เน้น signal quality แทน
Order size: Kelly fraction × Capital / Price
Placement: Best bid/ask ตาม signal direction
```

**Tier 2: ทุน $1,000 - $4,999**
```
จำนวน Layers: 2
Layer 1 (55% ของ deploy capital): Best bid/ask
Layer 2 (45% ของ deploy capital): 1 tick ถัดออกไป
Size randomization: × Uniform(0.93, 1.07) ทุกครั้ง
Timing jitter: Layer 2 ส่งหลัง Layer 1 → Uniform(0, 2ms)
```

**Tier 3: ทุน $5,000+**
```
จำนวน Layers: 3
Layer 1 (40% ของ deploy capital): Best bid/ask
Layer 2 (35%): 1 tick ถัดออกไป
Layer 3 (25%): 2 ticks ถัดออกไป
Size randomization: × Uniform(0.92, 1.08) ทุกครั้ง
Timing jitter: Layer N ส่งหลัง Layer N-1 → Uniform(0, 3ms)
Layer order: สลับลำดับ 30% ของเวลา (ส่ง Layer 3 ก่อน Layer 1 บ้าง)
```

### 1.3 Ghost Order Fill Rate Model

เป้าหมาย fill rate ต่อ signal:

```
Single layer ที่ best price: ~25-35% fill rate
2 layers: ~35-50% fill rate 
3 layers: ~45-65% fill rate
```

สูตรคำนวณ expected fill rate ต่อ layer:

```
P_fill(layer_n) = P_price_reaches(n) × P_queue_position(n) × P_not_cancelled(n)

P_price_reaches(n) = 1 - exp(-lambda_hawkes × holding_time × depth_factor(n))
depth_factor(1) = 1.0 (best price)
depth_factor(2) = 0.7 (1 tick deep)
depth_factor(3) = 0.45 (2 ticks deep)

P_queue_position(n) = our_size / total_size_at_level(n)
   (ถ้า level เพิ่งสร้าง = 1.0, ถ้ามี queue หนา = ต่ำ)

P_not_cancelled(n) = probability ที่เราไม่ cancel ก่อน fill
   (ขึ้นกับ signal stability ≈ 0.85-0.95)
```

### 1.4 Partial Fill Management

เมื่อบาง layer fill แต่บางไม่ fill:

```
กรณี Layer 1 fill, Layer 2-3 ยัง resting:
→ ถ้า signal ยังแรง: เก็บ Layer 2-3 ไว้ (เพิ่ม position)
→ ถ้า signal อ่อนลง: cancel Layer 2-3 ทันที
→ ถ้า signal กลับทิศ: cancel + เริ่ม exit logic

กรณี Layer 2 หรือ 3 fill แต่ Layer 1 ไม่ fill:
→ แปลว่าราคาวิ่งเข้ามาลึก = อาจเป็น signal ดี
→ ให้ cancel Layer 1 (อยู่ผิดราคาแล้ว)
→ เริ่ม exit logic ตามปกติ
```

---

## SECTION 2: AI PREDICTOR (แก้ไขเป็น Phased Approach)

### 2.1 คำตอบตรงๆ: AI ช่วยไหม?

**ช่วย — แต่ต้องมี data ก่อน**

AI/ML Predictor (LiT/TLOB) คือ Transformer model ขนาดเล็กที่เรียนรู้ pattern จาก LOB (Limit Order Book) snapshots เพื่อทำนายทิศทางราคาใน 200-1000ms ข้างหน้า

ในงานวิจัย (Zhang et al. 2019 "DeepLOB", Kolm et al. 2023 "Deep Order Flow Imbalance") model แบบนี้ให้ accuracy 55-62% ในการทำนายทิศทาง ซึ่งดีกว่า linear model 3-7%

**แต่ปัญหาคือ:**

ปัญหา A: ต้องการ training data — LOB tick-level data 30-90 วัน ต่อเหรียญ ซึ่งตอนนี้ยังไม่มี

ปัญหา B: ต้อง calibrate — model ที่ train กับ data เดือนที่แล้วอาจ fail เดือนนี้ ต้อง retrain สม่ำเสมอ

ปัญหา C: Complexity — ถ้า model bug แล้วให้ signal ผิดทิศ = เสียเงินจาก bug ไม่ใช่จาก market

**สรุปตัดสินใจ:**

```
Phase 1 (เดือนที่ 1-3): ใช้ Fast Path เท่านั้น
  - Linear Regression model
  - Features: MLOFI, PGT, Lead-Lag, VPIN, OBI, TFI
  - เก็บ LOB data ทุก tick ลง disk พร้อมๆ กัน (สำหรับ Phase 2)
  - Storage estimate: ~2-5 GB/วัน (compressed)

Phase 2 (เดือนที่ 4+): เพิ่ม Smart Path
  - ใช้ data ที่เก็บมา 90+ วัน train TLOB/LiT
  - Export เป็น ONNX → INT8 quantize
  - Load ใน Rust ผ่าน ort crate
  - A/B test: Fast Path vs Smart Path → ใช้ตัวที่ดีกว่า
  - ถ้า Smart Path ไม่ดีกว่า → ทิ้ง ใช้ Fast Path ต่อ
```

### 2.2 Fast Path (Phase 1) — รายละเอียดเต็ม

```
Model: Online Linear Regression with SGD (Stochastic Gradient Descent)

Input Features (7 ตัว):
  f1: MLOFI_norm_binance     — แรงกดดันบน Binance (signal source)
  f2: MLOFI_norm_bybit       — แรงกดดันบน Bybit (execution venue)
  f3: price_gap_norm          — (P_bin - P_byb) / sigma_spread
  f4: PGT_norm               — ความเร่งของ OFI
  f5: VPIN_50                 — toxicity level (ยิ่งสูงยิ่งอันตราย)
  f6: OBI_bybit              — Order Book Imbalance ratio
  f7: TFI_binance            — Trade Flow Imbalance (actual trades)

Output:
  direction_score = W . features + bias
  ค่าบวก = คาด Long, ค่าลบ = คาด Short
  |direction_score| = confidence level

Online Learning:
  หลังทุก trade ที่ปิด position:
    label = actual_pnl > 0 ? +1 : -1
    error = label - direction_score
    W(t+1) = W(t) + learning_rate × error × features
    learning_rate = 0.001
    L2 regularization lambda = 0.01
  
  ทำให้ model adapt ตลอดเวลา ไม่ต้อง retrain offline
```

### 2.3 Data Collection Pipeline (สำหรับ Phase 2)

```
ขณะที่ Phase 1 ทำงาน ระบบเก็บ data ลง disk พร้อมกัน:

LOB Snapshots:
  - เก็บทุก 100ms (10 snapshots/วินาที)
  - Format: timestamp_us, [[bid_price, bid_qty] × 10], [[ask_price, ask_qty] × 10]
  - Compression: zstd level 3
  - File rotation: ไฟล์ใหม่ทุก 1 ชั่วโมง

Trade Events:
  - เก็บทุก trade จาก aggTrade stream
  - Format: timestamp_us, price, qty, is_buyer_maker
  
Signal Log:
  - เก็บทุก signal ที่ system generate
  - Format: timestamp, all_features, direction_score, action_taken, result

Storage Budget:
  Per coin: ~1-2 GB/วัน (compressed)
  2 coins × 90 วัน = ~180-360 GB
  วิธีประหยัด: เก็บบน external HDD หรือ compress aggressive กว่า
```

---

## SECTION 3: VALIDATION PHASE + ASSET SCANNER (ตอบคำถามว่าทำอะไรก่อน)

### 3.1 คำตอบตรงๆ: ต้องเทสก่อนหรือให้โปรแกรมรันได้เลย?

**ทำทั้งสองอย่าง แต่คนละจังหวะ:**

```
Phase 0A (สัปดาห์ที่ 1): Validation Tool
  → Rust binary ตัวแรก ชื่อ "tradingclaw-scanner"
  → ต่อ WebSocket เก็บ data จาก Binance + Bybit
  → วัด lead-lag, spread, fill probability ของทุกเหรียญใน universe
  → รันทิ้งไว้ 24-48 ชั่วโมง
  → ผลลัพธ์: ranking ว่าเหรียญไหนมี alpha → ตัดสินใจได้

Phase 0B (สัปดาห์ที่ 2): Validate ผลลัพธ์
  → ดูข้อมูลที่ได้ → ตัดสินใจว่า strategy CEIFA ใช้ได้กับเหรียญไหน
  → ถ้าไม่มีเหรียญที่ pass → pivot strategy (ไป funding rate arb)
  → ถ้ามีเหรียญ pass → เริ่ม Phase 1

Phase 1+ (Runtime): Asset Scanner ทำงานต่อเนื่อง
  → Scanner เดียวกันนี้ กลายเป็นส่วนหนึ่งของ production system
  → รัน background แบบ 3-tier scan (1min, 15min, 2hr)
  → เมื่อพบเหรียญใหม่ที่ดีกว่า → trigger rotation
```

**ดังนั้น tradingclaw-scanner เป็นทั้ง validation tool และ production component — เขียนครั้งเดียว ใช้ได้ตลอด**

### 3.2 tradingclaw-scanner Architecture

```
Binary: tradingclaw-scanner

Mode 1: --mode validate (Phase 0)
  - ต่อทุกเหรียญใน universe พร้อมกัน (15-25 เหรียญ)
  - เก็บ data 24-48 ชม.
  - Output: report.json + report_readable.txt
  - แสดง ranking + recommendation

Mode 2: --mode scan (Production)
  - รัน background ใน main trading system
  - 3-tier scan schedule
  - Output: COS scores → ส่งไป trading engine ผ่าน channel

Shared Code:
  - WebSocket client (ใช้ร่วมกับ trading engine)
  - MLOFI calculator (ใช้ร่วม)
  - Cross-correlation calculator
  - COS scoring engine
```

### 3.3 Validation Criteria (Phase 0 ตัดสินใจอย่างไร)

เหรียญต้องผ่าน **ทุกข้อ** ถึงจะเป็น candidate:

```
Criterion 1 — Lead-Lag Existence:
  peak_cross_correlation > 0.60
  optimal_lag > 80ms (ต้องมากกว่า round-trip latency)
  optimal_lag < 500ms (ต้องไม่นานเกิน)
  PASS condition: correlation > 0.60 AND 80ms < lag < 500ms

Criterion 2 — Lead-Lag Stability:
  วัด lead-lag ทุก 30 นาที เป็นเวลา 24 ชม. = 48 samples
  coefficient_of_variation(lag) < 0.4 (lag ไม่ผันผวนเกิน 40%)
  PASS condition: CV < 0.4

Criterion 3 — Spread vs Alpha:
  average_spread < 0.15%
  estimated_alpha > 2.5 × total_round_trip_cost
  total_round_trip_cost = 2 × maker_fee + expected_slippage
  PASS condition: alpha/cost ratio > 2.5

Criterion 4 — Liquidity:
  average_LOB_depth_5_levels > $100,000
  daily_volume > $50M
  PASS condition: both met

Criterion 5 — Minimum Order Compatibility:
  min_order_value < $20 (ต้อง layer ได้ด้วยทุนไม่มาก)
  PASS condition: met
```

### 3.4 Validation Output Format

```
=== tradingclaw SCANNER REPORT ===
Date: 2026-02-20 00:00 to 2026-02-21 00:00
Duration: 24 hours
Coins Scanned: 22

=== TOP CANDIDATES ===

Rank 1: LINK/USDT
  Lead-Lag: 185ms (corr=0.78, CV=0.28) ✅
  Spread: 0.04% ✅
  Alpha/Cost: 3.8 ✅
  Depth: $340K ✅
  Min Order: $7.20 ✅
  COS Score: 87/100
  VERDICT: STRONG CANDIDATE

Rank 2: SOL/USDT
  Lead-Lag: 142ms (corr=0.71, CV=0.32) ✅
  Spread: 0.03% ✅
  Alpha/Cost: 3.2 ✅
  Depth: $520K ✅
  Min Order: $10.50 ✅
  COS Score: 82/100
  VERDICT: STRONG CANDIDATE

...

Rank 15: DOGE/USDT
  Lead-Lag: 65ms (corr=0.45, CV=0.55) ❌ (lag < 80ms, corr < 0.60)
  VERDICT: REJECTED (insufficient lead-lag)

=== RECOMMENDATION ===
Primary coin: LINK/USDT
Warm standby: SOL/USDT, AVAX/USDT
Strategy viability: CONFIRMED — proceed to Phase 1
```

---

## SECTION 4: FEATURES เพิ่มเติมที่ขาดในเอกสารเดิม

### 4.1 Order Book Imbalance Ratio (OBI) — ใหม่

```
Concept: วัดอัตราส่วนแรงซื้อ vs แรงขายจาก LOB โดยรวม

Formula:
OBI(t) = (V_bid_total_5L - V_ask_total_5L) / (V_bid_total_5L + V_ask_total_5L)

V_bid_total_5L = SUM(quantity at bid level 1 to 5)
V_ask_total_5L = SUM(quantity at ask level 1 to 5)

Interpretation:
OBI > +0.3: แรงซื้อมากกว่าแรงขายชัดเจน → bullish
OBI ใกล้ 0: สมดุล
OBI < -0.3: แรงขายมากกว่า → bearish

ข้อดีเทียบกับ MLOFI:
- คำนวณเร็วมาก (< 1 microsecond)
- ไม่ต้องเก็บ historical data
- ใช้เป็น fast confirmation signal

Integration:
- ไม่ได้แทน MLOFI แต่ใช้ร่วม
- ถ้า MLOFI บวก AND OBI บวก → confidence สูงขึ้น
- ถ้า MLOFI บวก BUT OBI ลบ → conflicting signal → ลด size
```

### 4.2 Trade Flow Imbalance (TFI) — ใหม่

```
Concept: วัดแรงกดจาก actual trades (ไม่ใช่แค่ orders ใน book)

Formula:
TFI(t, N) = (V_buy_N - V_sell_N) / (V_buy_N + V_sell_N)

V_buy_N = total volume ของ N trades ล่าสุดที่เป็น buyer-initiated
V_sell_N = total volume ของ N trades ล่าสุดที่เป็น seller-initiated
N = 100 trades (default)

Classification: ใช้ is_buyer_maker field จาก aggTrade stream
  is_buyer_maker = true → seller-initiated (taker sold)
  is_buyer_maker = false → buyer-initiated (taker bought)

Interpretation:
TFI > +0.2: aggressive buying → bullish
TFI < -0.2: aggressive selling → bearish

ทำไมสำคัญ:
- MLOFI ดู passive orders (ที่อาจเป็น spoof)
- TFI ดู actual execution (เงินจริง)
- เมื่อ MLOFI + TFI เห็นด้วยกัน → signal แข็งแรงมาก
```

### 4.3 Adaptive Alpha Weights — ใหม่ (แทน Fixed Weights)

```
เดิม: w1=0.35, w2=0.30, w3=0.20, w4=0.15 (fixed ตลอด)

ใหม่: weights ปรับอัตโนมัติตาม recent accuracy

Initial weights: เหมือนเดิม (0.35, 0.30, 0.20, 0.15)

หลังทุก batch ของ 50 filled trades:
  สำหรับ component i:
    accuracy_i = จำนวน trades ที่ component i ทำนายทิศถูก / 50
    performance_score_i = accuracy_i - 0.50 (baseline = random)
    w_i_new = w_i × (1 + lr × performance_score_i)
    lr = 0.05 (learning rate สำหรับ weight adaptation)
  
  Normalize ทุก weight:
    w_i = w_i / SUM(all w)
  
  Clamp ป้องกัน extreme:
    w_i = max(0.05, min(0.50, w_i))

ตัวอย่าง:
  ถ้า MLOFI accuracy = 0.60, Lead-Lag accuracy = 0.52:
    w_mlofi_new = 0.35 × (1 + 0.05 × 0.10) = 0.35 × 1.005 = 0.3518
    w_leadlag_new = 0.30 × (1 + 0.05 × 0.02) = 0.30 × 1.001 = 0.3003
  → MLOFI ได้น้ำหนักเพิ่ม เพราะ accuracy สูงกว่า
```

### 4.4 Adaptive Stop Loss — ใหม่ (แทน Fixed 0.5%)

```
เดิม: stop_loss = 0.5% ของ position value (ตลอด)

ใหม่: ปรับตาม market volatility

stop_loss_pct = max(0.30%, min(1.00%, 2.0 × ATR_1min_pct))

ATR_1min_pct = Average True Range ของ 1-minute candles / mid_price × 100%

คำนวณ ATR:
  TR_i = max(High_i - Low_i, |High_i - Close_(i-1)|, |Low_i - Close_(i-1)|)
  ATR_1min = EMA(TR, period=14) (14 one-minute candles)
  ATR_1min_pct = ATR_1min / mid_price × 100

ตัวอย่าง:
  ช่วง quiet: ATR_1min_pct = 0.08% → stop = max(0.3%, 0.16%) = 0.30%
  ช่วง normal: ATR_1min_pct = 0.20% → stop = max(0.3%, 0.40%) = 0.40%
  ช่วง volatile: ATR_1min_pct = 0.60% → stop = max(0.3%, 1.20%) = clamped 1.00%

เหตุผล:
  - ช่วง quiet: stop แคบ → ลด loss เร็ว ไม่รอนาน
  - ช่วง volatile: stop กว้าง → ไม่ถูก stop หลอกจาก noise
```

### 4.5 Lead-Lag Dual Update — ใหม่ (แทน fixed 2 ชม.)

```
เดิม: update ทุก 2 ชั่วโมง

ใหม่: 2 ระดับ

Micro Update (ทุก 30 วินาที):
  Window: 5 นาทีล่าสุด
  คำนวณ: cross-correlation ที่ lag 50-500ms
  ผลลัพธ์: tau_star_micro, corr_micro
  ใช้สำหรับ: real-time trading decisions

Macro Update (ทุก 30 นาที):
  Window: 2 ชั่วโมงล่าสุด
  คำนวณ: เหมือน micro แต่ window ใหญ่กว่า
  ผลลัพธ์: tau_star_macro, corr_macro
  ใช้สำหรับ: baseline reference, detect regime change

Conflict Resolution:
  ถ้า |tau_star_micro - tau_star_macro| < 50ms → ใช้ tau_star_micro
  ถ้า |tau_star_micro - tau_star_macro| >= 50ms → "lag unstable"
    → ลด confidence 50%
    → ใช้ tau_star_macro (conservative)

  ถ้า corr_micro < 0.40 → lead-lag อาจพังชั่วคราว
    → ลด lead-lag weight (w2) ลง 50%
    → พึ่ง MLOFI + PGT แทน

  ถ้า corr_micro < 0.25 เป็นเวลา > 5 นาที → หยุดเทรดเหรียญนี้
```

---

## SECTION 5: UPDATED ALPHA SIGNAL FORMULA

### 5.1 Signal Fusion (v3.0)

```
alpha_raw(t) = w1 × MLOFI_norm(t)
             + w2 × beta(t) × Delta_P_bin_norm(t - tau_star)
             + w3 × tanh(PGT_norm(t))
             + w4 × (1 - VPIN_50(t)) × sign(MLOFI(t))
             + w5 × OBI_bybit(t)               ← ใหม่
             + w6 × TFI_binance(t)              ← ใหม่

Default weights (before adaptation):
  w1 = 0.28 (MLOFI)            — ลดจาก 0.35 เพราะแบ่งให้ OBI/TFI
  w2 = 0.25 (Lead-Lag)         — ลดเล็กน้อย
  w3 = 0.17 (PGT)              — ลดเล็กน้อย
  w4 = 0.10 (VPIN-adjusted)    — ลด
  w5 = 0.10 (OBI)              — ใหม่
  w6 = 0.10 (TFI)              — ใหม่
  SUM = 1.00

Weights จะ adapt ตาม Section 4.3
```

### 5.2 VPIN Adjustment (ไม่เปลี่ยน)

```
alpha_adjusted(t) = alpha_raw(t) × (1 - 0.5 × VPIN_50(t))
```

### 5.3 BTC Regime Gate (ไม่เปลี่ยน)

```
alpha_final(t) = alpha_adjusted(t) × Regime_filter(t)
```

### 5.4 Entry Conditions (v3.0 — เพิ่มเงื่อนไข)

```
ต้องผ่านทั้งหมด:

Condition 1: |alpha_final(t)| > theta(t)                      — signal แรงพอ
Condition 2: VPIN_50(t) < 0.50                                 — ไม่ toxic
Condition 3: Spread < max_spread                               — spread ไม่กว้างเกิน
Condition 4: LOB_depth > minimum_depth                         — liquidity พอ
Condition 5: BTC_Regime_filter > 0                             — BTC ไม่ veto
Condition 6: Expected_Alpha > Total_Cost × 1.5                 — กำไรคุ้ม fee
Condition 7: lead_lag_corr_micro > 0.40                        — lead-lag ยังทำงาน (ใหม่)
Condition 8: |OBI| + |TFI| > 0.3                              — มี directional flow จริง (ใหม่)
Condition 9: time_since_last_trade > min_cooldown (2 วินาที)   — anti-overtrade (ใหม่)
```

---

## SECTION 6: PROFIT MODEL ที่ REALISTIC (แก้ไขใหม่)

### 6.1 Realistic Expected PnL

```
สมมติฐาน (conservative):
  Capital: $1,000
  Active deploy per trade (Kelly 5%): $50
  Maker fee: 0.01% (Bybit VIP 0)
  Average spread capture: 0.04% (4 bps) ← ค่าเฉลี่ยหลัง fill
  Fill rate: 30% (ของ signals ที่ส่ง)
  Win rate: 54% (หลัง fee)
  Average win: 0.04% ของ position
  Average loss: 0.03% ของ position (ขาดทุนมักน้อยกว่าเพราะ stop adaptive)
  Signals per day: 300-600

คำนวณ:
  Filled trades per day: 300 × 30% = 90 fills (conservative)
  
  Per winning trade: $50 × 0.04% - $50 × 0.01% × 2 = $0.020 - $0.010 = $0.010
  Per losing trade: -$50 × 0.03% - $50 × 0.01% × 2 = -$0.015 - $0.010 = -$0.025

  Daily PnL = 90 × (0.54 × $0.010 - 0.46 × $0.025)
            = 90 × ($0.0054 - $0.0115)
            = 90 × (-$0.0061)
            = -$0.549 ← ขาดทุน!

ปัญหา: ด้วย Kelly 5% และ position size $50 → กำไรต่อ trade เล็กเกิน

แก้ไข: ต้องใช้ leverage เบาๆ หรือ deploy มากกว่า 5%
```

### 6.2 Adjusted Model (ใช้ได้จริง)

```
Capital: $1,000
Leverage: 3x (conservative สำหรับ crypto)
Effective position: $150 per trade
Kelly fraction adjusted: 5% × 3 = 15% effective
Maker fee: 0.01%

Per winning trade: $150 × 0.04% - $150 × 0.01% × 2 = $0.060 - $0.030 = $0.030
Per losing trade: -$150 × 0.03% - $150 × 0.01% × 2 = -$0.045 - $0.030 = -$0.075

Wait — ยัง loss dominant. ปัญหาคือ average loss > average win

ต้องปรับ win rate target: 58%+ หรือ win/loss ratio ดีกว่า

Realistic achievable model:
  Win rate: 56%
  Average win: 0.05% (ปรับ target profit ให้สูงขึ้น)
  Average loss: 0.035% (adaptive stop loss ช่วย)
  Position: $150 (3x leverage on $50 deploy)
  Fee round-trip: $0.030

  Per winner: $150 × 0.05% - $0.030 = $0.075 - $0.030 = $0.045
  Per loser: -$150 × 0.035% - $0.030 = -$0.0525 - $0.030 = -$0.0825

  Daily PnL = 90 × (0.56 × $0.045 - 0.44 × $0.0825)
            = 90 × ($0.0252 - $0.0363)
            = 90 × (-$0.0111)
            = -$1.00 ← ยังลบ!

ปัญหาจริงๆ: ด้วย average spread capture 0.04-0.05% และ maker fee 0.01% per side:
  → margin ต่อ trade = 0.04% - 0.02% = 0.02% = 2 bps เท่านั้น
  → ต้องการ win rate > 60% หรือ position ใหญ่กว่านี้มาก
```

### 6.3 ทำไงให้ Positive? — ทางออกจริง

```
ทางออก A: เพิ่มทุนและ position size
  ทุน $5,000 + 3x leverage = $750 per trade
  Per winner: $750 × 0.04% - $0.15 = $0.30 - $0.15 = $0.15
  Per loser: -$750 × 0.03% - $0.15 = -$0.225 - $0.15 = -$0.375
  Daily = 90 × (0.56 × $0.15 - 0.44 × $0.375)
        = 90 × ($0.084 - $0.165)
        = 90 × (-$0.081) = -$7.29 ← ยังลบถ้า win rate 56%
  
  ต้อง win rate 69% ถึง break-even → ไม่ realistic

ทางออก B: หาเหรียญที่ spread capture ใหญ่กว่า ← นี่คือทางที่ถูก
  ถ้า average spread capture = 0.10% (10 bps) แทน 0.04%:
  Per winner ($150): $150 × 0.10% - $0.030 = $0.150 - $0.030 = $0.120
  Per loser ($150): -$150 × 0.05% - $0.030 = -$0.075 - $0.030 = -$0.105
  Daily = 90 × (0.56 × $0.120 - 0.44 × $0.105)
        = 90 × ($0.0672 - $0.0462)
        = 90 × $0.021 = $1.89/วัน
        = $56.7/เดือน (5.7% ต่อเดือนด้วยทุน $1,000) ✅

ทางออก C: ลดจำนวน trade แต่เพิ่ม quality ← ดีที่สุด
  เทรดเฉพาะ signal ที่แรงมากๆ (|alpha| > 2.0 แทน 1.0)
  30 trades/วัน แทน 90
  Win rate สูงขึ้นเป็น 62%
  Average win ใหญ่ขึ้น 0.12% (เพราะ signal quality สูง)
  Average loss 0.06%
  
  Per winner ($150): $0.180 - $0.030 = $0.150
  Per loser ($150): -$0.090 - $0.030 = -$0.120
  Daily = 30 × (0.62 × $0.150 - 0.38 × $0.120)
        = 30 × ($0.093 - $0.0456)
        = 30 × $0.0474 = $1.42/วัน
        = $42.6/เดือน (4.3% ต่อเดือน) ✅

ทางออก D: ผสม CEIFA + Funding Rate Arb ← Recommended
  CEIFA: $30-60/เดือน (จาก active trading)
  Funding Rate: $10-30/เดือน (จาก funding collection)
  รวม: $40-90/เดือน (4-9% ต่อเดือนด้วยทุน $1,000) ✅
```

### 6.4 สรุป Profit Model

```
KEY INSIGHT: 
  อย่าพยายาม trade บ่อย ให้ trade เฉพาะ signal ที่แรง
  จำนวน trade ↓ + quality ↑ = กำไรดีกว่า trade บ่อยๆ signal อ่อน

Recommended Setup:
  ทุน: $1,000+
  Leverage: 2-3x (ไม่เกิน)
  Position: $100-$300 per trade
  Threshold: alpha > 2.0 (สูงกว่าเดิม)
  Target: 20-40 filled trades/วัน
  Expected: 3-8% ต่อเดือน (หลัง tune 2-3 เดือน)

  เหรียญที่เลือกต้อง:
  → Lead-lag > 100ms
  → Typical spread > 0.08% (8 bps)
  → ยิ่ง spread กว้าง (แต่ยัง liquid) ยิ่งดี
  → Alt coins ขนาดกลาง (LINK, AVAX, FIL, NEAR) ดีกว่า BTC/ETH
```

---

## SECTION 7: REVISED IMPLEMENTATION ROADMAP (Rust Only)

### Phase 0: Scanner + Validation (สัปดาห์ที่ 1-2)

```
สิ่งที่ต้อง code:

Binary: tradingclaw-scanner

Crate Dependencies:
  tokio (async runtime)
  tokio-tungstenite (WebSocket)
  serde + serde_json (JSON parsing — เริ่มด้วยอันนี้ก่อน simd-json)
  chrono (timestamps)
  
Modules:
  ws_client.rs — WebSocket connector (Binance + Bybit)
  orderbook.rs — LOB data structure (BTreeMap)
  mlofi.rs — Multi-Level OFI calculator (10 levels)
  cross_corr.rs — Cross-correlation calculator
  scanner.rs — Universe scanner + COS scoring
  main.rs — CLI entry point

Tasks สัปดาห์ที่ 1:
  Day 1-2: WebSocket client ต่อ Binance depth stream + trade stream
  Day 3: OrderBook data structure + MLOFI calculator
  Day 4-5: WebSocket client ต่อ Bybit
  Day 6-7: Cross-correlation calculator

Tasks สัปดาห์ที่ 2:
  Day 8-9: Scanner logic (วนลูปทุกเหรียญ, คำนวณ COS)
  Day 10: Output report
  Day 11-14: รัน validation 24-48 ชม. + วิเคราะห์ผล

Deliverable: 
  ข้อมูล lead-lag + spread + fill probability ของทุกเหรียญ
  ตัดสินใจ: เหรียญไหน? ไปต่อหรือ pivot?
```

### Phase 1: Core Trading Engine (สัปดาห์ที่ 3-5)

```
Binary: tradingclaw-trader

Crate เพิ่มเติม:
  ring (HMAC-SHA256 for exchange auth)
  crossbeam (SPSC channel — ง่ายกว่า custom ring buffer ตอนเริ่ม)
  tracing + tracing-subscriber (logging)

Thread Architecture (เหมือนเอกสารเดิม):
  Thread 0: Network (WebSocket receive) — CPU Core 0
  Thread 1: Signal Engine — CPU Core 1
  Thread 2: Order Executor — CPU Core 2  
  Background: Risk Guardian — async task

Note: ตัด Thread 2 (AI Predictor) ออกใน Phase 1
  → ใช้ Fast Path linear model อยู่ใน Thread 1 แทน
  → เพิ่ม Thread AI กลับมาใน Phase 2

Tasks สัปดาห์ที่ 3:
  MLOFI + PGT + VPIN + Hawkes + OBI + TFI calculators
  Alpha fusion (6-component)
  Normalization (EWM)
  Fast Path linear predictor
  BTC Oracle (regime + directional filter)

Tasks สัปดาห์ที่ 4:
  Lead-Lag engine (dual update: micro 30s + macro 30min)
  Hayashi-Yoshida estimator
  Price prediction formula
  A-S model (reservation price + spread)

Tasks สัปดาห์ที่ 5:
  Order placement via Bybit WebSocket
  PostOnly Limit Order
  Order State Machine
  Ghost Order layers (2 layers for $1K capital)
  Order amendment (amend price without cancel)
  Rate limit Token Bucket
  HMAC signature

Deliverable: ระบบ trade อัตโนมัติพร้อม paper trade
```

### Phase 2: Risk + Paper Trading (สัปดาห์ที่ 6-7)

```
Tasks สัปดาห์ที่ 6:
  Expected Shortfall calculator
  Kill Switch
  Drawdown monitor
  Inventory limits
  Correlation Break monitor
  Adaptive stop loss (ATR-based)
  Kelly position sizing + Sortino dampener
  WebSocket reconnection (exponential backoff)

Tasks สัปดาห์ที่ 7:
  Paper trading on Bybit testnet (รัน 24/7)
  Monitor metrics: fill rate, win rate, PnL, drawdown
  Bug fix + parameter tuning
  Data collection pipeline (เก็บ LOB data สำหรับ Phase 4)

Deliverable: 
  2 สัปดาห์ paper trading data
  Decision: go live หรือ tune เพิ่ม?
```

### Phase 3: Live Trading + Asset Rotation (สัปดาห์ที่ 8-10)

```
Tasks สัปดาห์ที่ 8:
  Live trading เริ่มด้วย $200-500 (minimum size)
  Monitor ใกล้ชิด
  Compare live vs paper results

Tasks สัปดาห์ที่ 9:
  Asset Rotation Engine
  COS scoring (5 components)
  3-tier scan schedule
  Rotation protocol (drain + switch)
  
Tasks สัปดาห์ที่ 10:
  Anti-HFT: Iceberg detection, Spoofing detection
  Queue Toxicity evaluator
  Latency Confirmation Window
  Scale up capital ถ้า profitable

Deliverable:
  Full production system
  Auto-rotating between best coins
```

### Phase 4: AI + Optimization (เดือนที่ 4+)

```
Tasks:
  ใช้ data ที่เก็บมา 90+ วัน train TLOB/LiT
  Python: train model, export ONNX
  Rust: load ด้วย ort crate, INT8 inference
  A/B test: Fast Path vs Smart Path
  
  เช่า VPS Singapore (Vultr $12-24/เดือน)
  ลด latency จาก 40ms เหลือ 1-3ms
  
  Optimize:
  - simd-json แทน serde_json
  - Custom SPSC ring buffer แทน crossbeam
  - AF_XDP (eBPF) ถ้า VPS support
  - CPU core pinning + isolcpus
  
  เพิ่ม Funding Rate Arb module
```

---

## SECTION 8: CONFIGURATION PARAMETERS (v3.0 Final)

### 8.1 Signal Parameters

```
MLOFI:
  lambda_decay = 0.3
  ewm_span_short = 500 ticks (ใหม่: dual normalization)
  ewm_span_long = 10000 ticks (ใหม่)

Lead-Lag:
  tau_range = 50ms to 500ms
  tau_step = 10ms
  micro_update_interval = 30 seconds (ใหม่: แทน 2 ชั่วโมง)
  macro_update_interval = 30 minutes (ใหม่)
  micro_window = 5 minutes
  macro_window = 2 hours
  min_correlation = 0.40 (ใหม่: threshold ต่ำสุด)
  min_lag = 80ms (ใหม่: ต้องมากกว่า round-trip)

PGT:
  delta_t = 100ms
  ewm_span = 3000 ticks

VPIN:
  bucket_divisor = 50
  rolling_window = 50 buckets

Hawkes:
  calibration_window = 30 minutes
  (mu, alpha, beta_decay calibrate per coin)

OBI: (ใหม่)
  levels = 5
  
TFI: (ใหม่)
  window = 100 trades
```

### 8.2 Alpha Fusion Parameters

```
Initial weights: w1=0.28, w2=0.25, w3=0.17, w4=0.10, w5=0.10, w6=0.10
Adaptation learning rate: 0.05
Adaptation batch size: 50 trades
Weight clamp: [0.05, 0.50]
Entry threshold (theta_base): 2.0 (เพิ่มจาก 1.0 เพื่อ trade quality)
```

### 8.3 A-S Parameters

```
gamma = 0.5 (calibrate per coin)
kappa = 1.5 (calibrate per coin)
T_horizon = 30 seconds
sigma = real-time realized vol (update ทุก 1 นาที)
spread_floor = max(A-S_spread, 2 × maker_fee + 2 bps) (ใหม่)
```

### 8.4 Position Sizing

```
Kelly fractional_multiplier = 0.25
Default leverage = 3x (max 5x ห้ามเกิน)
Sortino target = 2.5
Min trade cooldown = 2 seconds (ใหม่: anti-overtrade)
```

### 8.5 Risk Parameters

```
ES_percentile = 99%
ES_limit = 5% of capital
max_drawdown_warning = 5%
max_drawdown_halt = 8%
max_position_fraction = 0.30
max_hold_time = 60 seconds
stop_loss = adaptive: max(0.30%, min(1.00%, 2 × ATR_1min_pct)) (ใหม่)
```

### 8.6 Ghost Order Parameters

```
Tier threshold: $500 = 1 layer, $1000 = 2 layers, $5000 = 3 layers
Layer allocation (2 layers): [55%, 45%]
Layer allocation (3 layers): [40%, 35%, 25%]
Size jitter: Uniform(0.92, 1.08)
Timing jitter: Uniform(0, 3ms) between layers
Layer order shuffle probability: 30%
NO decoy orders
```

### 8.7 Asset Rotation Parameters

```
scan_heartbeat = 60 seconds
scan_quick = 15 minutes
scan_deep = 2 hours (ลดจาก original เพราะ lead-lag micro update ทำงานแล้ว)
rotation_cos_decay = 0.60
rotation_superiority = 1.40
rotation_cooldown = 30 minutes
rotation_drain_timeout = 30 seconds
```

### 8.8 Network Parameters (ไม่เปลี่ยน)

```
tcp_nodelay = true
ws_ping_interval = 20 seconds
reconnect_base_delay = 100ms
reconnect_max_delay = 30000ms
reconnect_max_attempts = 10
```

---

## SECTION 9: CARGO WORKSPACE STRUCTURE

```
tradingclaw/
├── Cargo.toml                (workspace root)
├── crates/
│   ├── common/               (shared types, config)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types.rs      (OrderBook, Trade, Signal, Order, Position)
│   │       └── config.rs     (all parameters from Section 8)
│   │
│   ├── network/              (WebSocket clients)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── binance.rs    (Binance WS depth + aggTrade)
│   │       ├── bybit.rs      (Bybit WS LOB + trades + private)
│   │       └── okx.rs        (OKX WS — Phase 3)
│   │
│   ├── signals/              (all signal calculators)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── mlofi.rs      (Multi-Level OFI)
│   │       ├── pgt.rs        (Pressure Gradient Tensor)
│   │       ├── vpin.rs       (VPIN toxicity)
│   │       ├── hawkes.rs     (Hawkes Process)
│   │       ├── obi.rs        (Order Book Imbalance — ใหม่)
│   │       ├── tfi.rs        (Trade Flow Imbalance — ใหม่)
│   │       ├── lead_lag.rs   (Cross-correlation + Hayashi-Yoshida)
│   │       ├── vamp.rs       (Volume Adjusted Mid Price)
│   │       └── alpha.rs      (Signal fusion + adaptive weights)
│   │
│   ├── predictor/            (AI/ML path)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── fast_path.rs  (Linear model + online learning)
│   │       └── smart_path.rs (TLOB/LiT — Phase 4 placeholder)
│   │
│   ├── execution/            (order management)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── avellaneda.rs (A-S model)
│   │       ├── ghost.rs      (Ghost Order layering)
│   │       ├── state_machine.rs (Order State Machine)
│   │       ├── exit.rs       (Exit logic: target, inventory, reversal, time, stop)
│   │       └── rate_limit.rs (Token Bucket per exchange)
│   │
│   ├── risk/                 (risk management)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── expected_shortfall.rs
│   │       ├── kill_switch.rs
│   │       ├── drawdown.rs
│   │       ├── inventory.rs
│   │       ├── correlation_break.rs
│   │       └── kelly.rs      (Position sizing + Sortino)
│   │
│   ├── scanner/              (asset rotation)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── universe.rs   (Static filter)
│   │       ├── cos.rs        (COS scoring — 5 components)
│   │       ├── btc_oracle.rs (BTC regime + directional)
│   │       └── rotation.rs   (Rotation protocol)
│   │
│   └── anti_hft/             (Phase 3)
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── iceberg.rs
│           ├── spoofing.rs
│           ├── queue_toxicity.rs
│           └── latency_confirm.rs
│
├── bins/
│   ├── scanner/              (tradingclaw-scanner binary)
│   │   ├── Cargo.toml
│   │   └── src/main.rs
│   │
│   └── trader/               (tradingclaw-trader binary)
│       ├── Cargo.toml
│       └── src/main.rs
│
├── config/
│   ├── default.toml          (default parameters)
│   ├── paper.toml            (paper trading overrides)
│   └── live.toml             (live trading overrides)
│
└── data/                     (LOB data collection — Phase 2+)
    └── .gitkeep
```

---

## SECTION 10: GO-LIVE CHECKLIST (v3.0)

```
=== Phase 0 Validation ===
[ ] tradingclaw-scanner builds and runs
[ ] Connects to Binance + Bybit WebSocket successfully
[ ] Receives and parses LOB + trade data
[ ] Calculates MLOFI for all universe coins
[ ] Calculates cross-correlation (lead-lag)
[ ] Ran 24-48 hours validation
[ ] At least 3 coins pass all 5 criteria
[ ] Lead-lag > 100ms, correlation > 0.60 confirmed

=== Phase 1 Core Engine ===
[ ] All signal calculators unit tested
[ ] Alpha fusion produces reasonable values
[ ] A-S model produces valid bid/ask prices
[ ] Spread floor enforced (never trade at negative expected PnL)
[ ] Order State Machine handles all transitions
[ ] PostOnly orders accepted by Bybit (testnet)
[ ] Order amendment works (change price without cancel)
[ ] Ghost Orders deploy correct sizes per tier
[ ] Rate limit Token Bucket prevents exceeding limits
[ ] HMAC signatures validated by exchange

=== Phase 2 Risk + Paper ===
[ ] Kill Switch triggers correctly (simulated)
[ ] Drawdown monitor halts at 8%
[ ] Adaptive stop loss adjusts with ATR
[ ] WebSocket reconnect recovers within 30 seconds
[ ] Paper trading: 500+ filled trades recorded
[ ] Paper trading: fill rate > 20%
[ ] Paper trading: win rate > 52%
[ ] Paper trading: positive PnL (after all fees)
[ ] Paper trading: max drawdown < 5%

=== Phase 3 Live ===
[ ] Live trading: start with $200-500 minimum
[ ] Compare live metrics with paper (within 20% tolerance)
[ ] No unexpected behaviors for 1 week
[ ] Scale to target capital gradually (50% increase per week)
[ ] Asset Rotation tested (manual trigger + auto)
[ ] Data collection pipeline running (for Phase 4 ML)
```

---

END OF DOCUMENT

Version: 3.0 Final
Changes from v2.1: Ghost Orders revised, AI phased, 2 new signals (OBI/TFI), 
  adaptive weights, adaptive stop loss, dual lead-lag update, 
  realistic profit model, Rust-first roadmap, validation phase added
Ready for Implementation: Yes
Next Step: Phase 0 — Build tradingclaw-scanner in Rust
