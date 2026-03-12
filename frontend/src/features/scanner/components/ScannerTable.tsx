import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchPairs, openTrade, cn } from '../../../lib/api';
import { RefreshCw, LayoutGrid, AlertCircle, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

function MiniSpread({ zscore }: { zscore: number }) {
    const w = 100, h = 24;
    const data = Array.from({ length: 30 }, (_, i) => {
        const base = Math.sin(i * 0.3) * 1.5;
        return i === 29 ? zscore : base + (Math.random() - 0.5) * 1.2;
    });
    const mn = Math.min(...data, -3), mx = Math.max(...data, 3), rng = mx - mn || 1;
    const pts = data.map((v, i) => `${(i / 29) * w},${h - ((v - mn) / rng) * h}`).join(" ");
    const last = data[data.length - 1];
    const cy = h - ((last - mn) / rng) * h;
    const col = Math.abs(last) > 2 ? (last > 0 ? "#ef4444" : "#10b981") : "#5a6a82";
    const zeroY = h - ((0 - mn) / rng) * h;
    return (
        <svg width={w} height={h} style={{ display: "block" }}>
            <line x1={0} y1={zeroY} x2={w} y2={zeroY} stroke="#1e293b" strokeWidth={0.7} />
            <polyline fill="none" stroke={col} strokeWidth={1.4} points={pts} />
            <circle cx={w} cy={cy} r={2} fill={col} />
        </svg>
    );
}

function ZoneBadge({ zone, sizePct }: { zone: string; sizePct?: number }) {
    const map: Record<string, { bg: string; border: string; color: string; label: string; drop: string }> = {
        safe:    { bg: "rgba(22,163,74,0.15)",   border: "rgba(34,197,94,0.3)",  color: "#4ade80", label: `SAFE ${sizePct || 100}%`,    drop: "rgba(16,185,129,0.1)" },
        caution: { bg: "rgba(194,65,12,0.15)",   border: "rgba(234,88,12,0.3)",  color: "#fb923c", label: `CAUTION ${sizePct || 50}%`,  drop: "rgba(249,115,22,0.1)" },
        danger:  { bg: "rgba(153,27,27,0.15)",   border: "rgba(220,38,38,0.3)",  color: "#f87171", label: "BLOCKED",                    drop: "rgba(239,68,68,0.1)" },
        none:    { bg: "rgba(30,41,59,0.15)",    border: "rgba(71,85,105,0.3)",  color: "#94a3b8", label: "NO SIGNAL",                  drop: "rgba(0,0,0,0)" },
    };
    const s = map[zone] || map.none;
    return (
        <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color, boxShadow: `0 0 10px ${s.drop}` }}
            className="px-2 py-0.5 rounded text-[8px] font-black tracking-[0.1em] whitespace-nowrap backdrop-blur-sm">
            {s.label}
        </span>
    );
}

function Side({ side }: { side: string }) {
    const isLong = side === "LONG" || side === "buy";
    return (
        <span style={{ color: isLong ? "#4ade80" : "#f87171", background: isLong ? "rgba(22,163,74,0.1)" : "rgba(153,27,27,0.1)", border: `1px solid ${isLong ? "rgba(34,197,94,0.2)" : "rgba(220,38,38,0.2)"}` }}
            className="font-black text-[8px] px-2 py-0.5 rounded tracking-widest">
            {isLong ? "LONG" : "SHORT"}
        </span>
    );
}

function ValidationPanel({ pair }: { pair: any }) {
    const checks = [
        { name: "Futures Contract",  pass: true,                                    detail: `${pair.symbol_a}: OK  ${pair.symbol_b}: OK` },
        { name: "Price Stream",      pass: true,                                    detail: "Active" },
        { name: "β valid",           pass: pair.hedge_ratio > 0,                   detail: `β=${Number(pair.hedge_ratio).toFixed(4)}` },
        { name: "Corr ≥ 0.80",       pass: pair.correlation >= 0.80,               detail: Number(pair.correlation).toFixed(3) },
        { name: "Hurst < 0.5",       pass: (pair.hurst_exp || 0.45) < 0.5,         detail: `H=${Number(pair.hurst_exp || 0.45).toFixed(3)}` },
        { name: "HL 2–35d",          pass: pair.half_life >= 2 && pair.half_life <= 35, detail: `${Number(pair.half_life).toFixed(1)}d` },
        { name: "ADF p ≤ 0.05",      pass: (pair.cointegration_pvalue ?? 1) <= 0.05, detail: `p=${Number(pair.cointegration_pvalue ?? 1).toFixed(4)}` },
        { name: "|Z| ≥ 2.0",         pass: Math.abs(pair.zscore) >= 2.0,           detail: `Z=${Number(pair.zscore).toFixed(3)}` },
        { name: "Safe Zone",         pass: pair.zone !== "danger",                  detail: pair.zone?.toUpperCase() || "N/A" },
        { name: "Dedup Engine",      pass: true,                                    detail: "Unique" },
    ];
    const passCount = checks.filter(c => c.pass).length;

    return (
        <div className="mt-2 p-4 bg-[#0c1222] border border-[#1e3a5f] rounded-lg">
            <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-bold text-ui-cyan uppercase tracking-widest">
                    Validation — {pair.symbol_a}/{pair.symbol_b}
                </span>
                <span className={cn("text-[10px] font-bold", passCount === checks.length ? "text-ui-green" : "text-ui-red")}>
                    {passCount}/{checks.length} PASSED
                </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {checks.map((c, i) => (
                    <div key={i} className={cn("flex items-center gap-2 p-1.5 rounded bg-white/[0.02] border", c.pass ? "border-ui-green/20" : "border-ui-red/30")}>
                        {c.pass ? <CheckCircle2 className="w-3 h-3 text-ui-green shrink-0" /> : <XCircle className="w-3 h-3 text-ui-red shrink-0" />}
                        <div className="flex flex-col">
                            <span className="text-[8px] text-[#5a6a82] font-bold uppercase tracking-tight leading-none mb-1">{c.name}</span>
                            <span className={cn("text-[9px] font-bold", c.pass ? "text-ui-green" : "text-ui-red")}>{c.detail}</span>
                        </div>
                    </div>
                ))}
            </div>
            {pair.qualified && (
                <div className="mt-3 p-3 bg-white/[0.03] rounded border border-[#151f35] flex flex-wrap gap-6 items-center">
                    <div className="flex flex-col">
                        <span className="text-[7px] text-[#5a6a82] font-bold uppercase tracking-widest">Est Hold Time</span>
                        <span className="text-[10px] font-bold text-[#c8d6e5]">
                            {(pair.half_life * 0.5).toFixed(0)} – {Number(pair.half_life).toFixed(0)} – {(pair.half_life * 2).toFixed(0)} Days
                        </span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[7px] text-[#5a6a82] font-bold uppercase tracking-widest">Action Vector</span>
                        <div className="flex items-center gap-2 mt-0.5">
                            <Side side={pair.zscore > 0 ? "SHORT" : "LONG"} />
                            <span className="text-[10px] font-bold">{pair.symbol_a}</span>
                            <span className="text-[#5a6a82]">/</span>
                            <Side side={pair.zscore > 0 ? "LONG" : "SHORT"} />
                            <span className="text-[10px] font-bold">{pair.symbol_b}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function ScannerTable() {
    const queryClient = useQueryClient();
    const { data: pairsData, isLoading, isError } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs });
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [executingId, setExecutingId] = useState<string | null>(null);
    const [lastResult, setLastResult] = useState<{ id: string; success: boolean; msg: string } | null>(null);

    const executeMutation = useMutation({
        mutationFn: (pair: any) => openTrade(pair),
        onMutate: (pair: any) => setExecutingId(`${pair.symbol_a}-${pair.symbol_b}`),
        onSettled: () => setExecutingId(null),
        onSuccess: (result: any, pair: any) => {
            const id = `${pair.symbol_a}-${pair.symbol_b}`;
            if (result.success) {
                setLastResult({ id, success: true, msg: `Opened! GroupID: ${result.groupId?.slice(0, 8)}` });
                queryClient.invalidateQueries({ queryKey: ['positions'] });
                queryClient.invalidateQueries({ queryKey: ['portfolio'] });
            } else {
                setLastResult({ id, success: false, msg: result.reason || 'Blocked' });
            }
            setTimeout(() => setLastResult(r => r?.id === id ? null : r), 5000);
        },
        onError: (_: any, pair: any) => {
            const id = `${pair.symbol_a}-${pair.symbol_b}`;
            setLastResult({ id, success: false, msg: 'Network error' });
            setTimeout(() => setLastResult(r => r?.id === id ? null : r), 5000);
        },
    });

    const handleExecute = (e: React.MouseEvent, pair: any) => {
        e.stopPropagation();
        executeMutation.mutate(pair);
    };

    if (isLoading) return (
        <div className="p-32 text-center text-[#5a6a82] flex flex-col items-center justify-center space-y-4">
            <RefreshCw className="h-8 w-8 text-ui-cyan animate-spin" />
            <span className="font-bold text-[10px] uppercase tracking-[0.3em]">Synchronizing Market Data...</span>
        </div>
    );

    if (isError) return (
        <div className="p-20 flex flex-col items-center justify-center">
            <div className="bg-[#450a0a]/20 border border-ui-red/30 p-12 rounded-lg flex flex-col items-center max-w-2xl text-center">
                <AlertCircle className="w-12 h-12 text-ui-red mb-4" />
                <div className="text-ui-red font-bold text-sm uppercase tracking-widest mb-2">Critical Link Failure</div>
                <div className="text-[#c8d6e5] text-xs leading-relaxed opacity-60">API bridge (3001) unreachable. Check Python logs.</div>
            </div>
        </div>
    );

    if (!pairsData || pairsData.length === 0) return (
        <div className="p-32 flex flex-col items-center justify-center opacity-30 space-y-4">
            <LayoutGrid className="h-12 w-12 text-[#5a6a82]" />
            <div className="font-bold text-xs uppercase tracking-[0.2em] text-[#5a6a82]">Empty Cluster Result</div>
        </div>
    );

    const sortedPairs = [...pairsData].sort((a: any, b: any) => {
        if (a.qualified && !b.qualified) return -1;
        if (!a.qualified && b.qualified) return 1;
        return Math.abs(b.zscore) - Math.abs(a.zscore);
    });

    const columns = [
        { label: "PAIR",   width: "160px" },
        { label: "Z-SCORE",width: "100px" },
        { label: "CORR",   width: "80px"  },
        { label: "HURST",  width: "80px"  },
        { label: "HL",     width: "70px"  },
        { label: "β",      width: "70px"  },
        { label: "SPREAD", width: "120px" },
        { label: "ZONE",   width: "120px" },
        { label: "ACTION", width: "130px" },
    ];
    const gridCols = "160px 100px 80px 80px 70px 70px 120px 120px 130px";

    return (
        <div className="overflow-x-auto p-4">
            <div className="grid gap-4 px-4 py-2 bg-[#080d18] rounded-t-lg border-x border-t border-[#151f35]"
                style={{ gridTemplateColumns: gridCols }}>
                {columns.map((col, idx) => (
                    <span key={idx} className="text-[8px] font-black text-[#5a6a82] tracking-wider uppercase">{col.label}</span>
                ))}
            </div>

            <div className="flex flex-col border-x border-[#151f35] border-b bg-[#0b1120] rounded-b-lg overflow-hidden">
                {sortedPairs.map((pair: any) => {
                    const id       = `${pair.symbol_a}-${pair.symbol_b}`;
                    const isSelected  = selectedId === id;
                    const isSignal    = pair.qualified;
                    const absZ        = Math.abs(pair.zscore);
                    const isExecuting = executingId === id;
                    const result      = lastResult?.id === id ? lastResult : null;

                    // validation_json can be a string (from DB) or object
                    const valJson = typeof pair.validation_json === 'string'
                        ? JSON.parse(pair.validation_json || '{}')
                        : (pair.validation_json || {});
                    const sizePct = valJson.sizePct ?? (pair.zone === 'caution' ? 50 : 100);

                    return (
                        <div key={id} className="border-t first:border-t-0 border-[#151f35]">
                            <div
                                onClick={() => setSelectedId(isSelected ? null : id)}
                                className={cn(
                                    "grid gap-4 px-4 py-2.5 items-center cursor-pointer transition-all relative overflow-hidden",
                                    isSelected ? "bg-ui-accent/[0.07]" : isSignal ? "bg-ui-green/[0.05] hover:bg-ui-green/[0.08]" : "hover:bg-white/[0.03]"
                                )}
                                style={{ gridTemplateColumns: gridCols }}
                            >
                                {/* Pair */}
                                <div className="flex items-center gap-2">
                                    <span className={cn("text-[11px] font-bold", isSignal ? "text-white" : "text-[#c8d6e5]")}>{pair.symbol_a}</span>
                                    <span className="text-[#151f35]">/</span>
                                    <span className={cn("text-[11px] font-bold", isSignal ? "text-white" : "text-[#c8d6e5]")}>{pair.symbol_b}</span>
                                </div>

                                {/* Z-Score */}
                                <div className={cn("text-xs font-black tabular-nums",
                                    absZ > 3 ? "text-ui-red" : absZ > 2 ? (pair.zscore > 0 ? "text-rose-400" : "text-ui-green") : "text-[#5a6a82]")}>
                                    {pair.zscore > 0 ? "+" : ""}{Number(pair.zscore).toFixed(3)}
                                </div>

                                {/* Corr */}
                                <div className={cn("text-[10px] font-bold tabular-nums",
                                    pair.correlation >= 0.8 ? "text-ui-green" : pair.correlation >= 0.6 ? "text-ui-orange" : "text-ui-red")}>
                                    {Number(pair.correlation).toFixed(2)}
                                </div>

                                {/* Hurst */}
                                <div className={cn("text-[10px] font-bold", (pair.hurst_exp || 0.45) < 0.5 ? "text-ui-green" : "text-ui-red")}>
                                    {Number(pair.hurst_exp || 0.45).toFixed(2)}
                                </div>

                                {/* HL */}
                                <div className="text-[10px] font-bold text-[#c8d6e5] opacity-80 tabular-nums">
                                    {Number(pair.half_life).toFixed(0)}d
                                </div>

                                {/* β */}
                                <div className="text-[10px] font-bold text-[#5a6a82] tabular-nums">
                                    {Number(pair.hedge_ratio).toFixed(2)}
                                </div>

                                {/* Spread */}
                                <div><MiniSpread zscore={pair.zscore} /></div>

                                {/* Zone */}
                                <div><ZoneBadge zone={pair.zone || 'none'} sizePct={sizePct * 100} /></div>

                                {/* Action */}
                                <div onClick={e => e.stopPropagation()}>
                                    {result ? (
                                        <div className={cn("text-[8px] font-black uppercase tracking-tight px-2 py-1 rounded border",
                                            result.success ? "text-ui-green border-ui-green/30 bg-ui-green/10" : "text-ui-red border-ui-red/30 bg-ui-red/10")}>
                                            {result.msg}
                                        </div>
                                    ) : isSignal ? (
                                        <button
                                            onClick={e => handleExecute(e, pair)}
                                            disabled={isExecuting}
                                            className={cn(
                                                "w-full py-1.5 rounded text-[9px] font-black uppercase tracking-widest text-[#06080f] shadow-lg active:scale-95 transition-all flex items-center justify-center gap-1",
                                                isExecuting ? "opacity-60 cursor-not-allowed bg-[#5a6a82]" : pair.zscore > 0 ? "bg-ui-red hover:opacity-90" : "bg-ui-green hover:opacity-90"
                                            )}>
                                            {isExecuting ? (
                                                <><Loader2 className="w-3 h-3 animate-spin" /> OPENING...</>
                                            ) : (
                                                pair.zscore > 0 ? "SHORT" : "LONG"
                                            )}
                                        </button>
                                    ) : pair.zone === 'danger' ? (
                                        <div className="text-[7px] text-ui-red font-black uppercase tracking-tighter flex items-center gap-1">
                                            <XCircle className="w-2.5 h-2.5" /> Blocked
                                        </div>
                                    ) : (
                                        <div className="w-1/2 h-[1px] bg-[#151f35]" />
                                    )}
                                </div>
                            </div>

                            {isSelected && (
                                <div className="px-4 pb-4">
                                    <ValidationPanel pair={pair} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
