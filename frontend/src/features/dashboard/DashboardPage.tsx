import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap, History, Shield, RefreshCw, BarChart3 } from 'lucide-react';
import { fetchPairs, fetchPositions, triggerScan, socket, cn } from '../../lib/api';
import ScannerTable from '../scanner/components/ScannerTable';

export default function DashboardPage() {
    const queryClient = useQueryClient();
    const [view, setView] = useState('scanner');
    const [autoScan, setAutoScan] = useState(false);
    const [isConnected, setIsConnected] = useState(socket.connected);
    const [scanCount, setScanCount] = useState(0);
    const [lastScan, setLastScan] = useState(new Date());

    useEffect(() => {
        socket.on('connect', () => setIsConnected(true));
        socket.on('disconnect', () => setIsConnected(false));
        socket.on('pairs_update', () => {
            queryClient.invalidateQueries({ queryKey: ['pairs'] });
            setScanCount(c => c + 1);
            setLastScan(new Date());
        });

        return () => {
            socket.off('connect');
            socket.off('disconnect');
            socket.off('pairs_update');
        };
    }, [queryClient]);

    const { data: pairsData } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs, refetchInterval: autoScan ? 5000 : false });
    const { data: positionsData } = useQuery({ queryKey: ['positions'], queryFn: fetchPositions });

    const scanMutation = useMutation({
        mutationFn: triggerScan,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['pairs'] });
            setScanCount(c => c + 1);
            setLastScan(new Date());
        },
    });

    const runScan = () => scanMutation.mutate();

    const signalsCount = pairsData?.filter((p: any) => p.qualified).length || 0;
    const blockedCount = pairsData?.filter((p: any) => p.zone === 'danger').length || 0;
    const totalPnl = 0; // Placeholder for now

    const tabs = [
        { id: "scanner", label: "SCANNER", count: pairsData?.length || 0 },
        { id: "positions", label: "POSITIONS", count: positionsData?.length || 0 },
        { id: "history", label: "HISTORY", count: 0 }, // Placeholder
        { id: "logs", label: "SYSTEM LOG", count: 12 }, // Placeholder
    ];

    return (
        <div className="min-h-screen bg-[#06080f] text-[#c8d6e5] font-mono selection:bg-ui-accent/30 selection:text-white transition-colors duration-500">

            {/* ═══ TOP BAR ═══ */}
            <div className="bg-[#080d18] border-b border-[#151f35] px-5 py-3 flex justify-between items-center flex-wrap gap-4">
                <div className="flex items-center gap-4">
                    <div className="text-sm font-bold text-ui-cyan tracking-[0.2em] flex items-center gap-2">
                        <div className="w-2 h-2 bg-ui-cyan animate-pulse" />
                        PAIRS<span className="text-[#5a6a82]">TRADE</span>
                    </div>
                    <div className="w-[1px] h-4 bg-[#151f35]" />
                    <span className="text-[9px] text-[#5a6a82] font-bold tracking-wider uppercase">V2.0 PRO · OKX FUTURES</span>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-6 mr-4">
                        <div className="flex items-center gap-2">
                            <span className="text-[9px] text-[#5a6a82] font-bold">AUTO</span>
                            <button
                                onClick={() => setAutoScan(!autoScan)}
                                className={cn(
                                    "w-8 h-4 rounded-full relative transition-all duration-300",
                                    autoScan ? "bg-ui-green/40" : "bg-[#151f35]"
                                )}
                            >
                                <div className={cn(
                                    "absolute top-0.5 w-3 h-3 rounded-full transition-all duration-300",
                                    autoScan ? "right-1 bg-ui-green" : "left-1 bg-[#5a6a82]"
                                )} />
                            </button>
                        </div>
                        <div className="text-right">
                            <div className="text-[9px] text-[#5a6a82] font-bold uppercase tracking-tighter">
                                Scan #{scanCount} · {lastScan.toLocaleTimeString("en-GB", { hour12: false })}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={runScan}
                        disabled={scanMutation.isPending}
                        className={cn(
                            "px-4 py-1.5 rounded bg-ui-accent hover:bg-ui-accent/80 text-white text-[10px] font-black tracking-widest uppercase transition-all active:scale-95 disabled:opacity-30 flex items-center gap-2",
                            scanMutation.isPending && "animate-pulse"
                        )}
                    >
                        {scanMutation.isPending ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3 fill-white" />}
                        {scanMutation.isPending ? "Scanning..." : "Scan Now"}
                    </button>
                </div>
            </div>

            {/* ═══ STATS STRIP ═══ */}
            <div className="flex border-b border-[#151f35] overflow-x-auto no-scrollbar">
                {[
                    { label: "PAIRS SCANNED", value: pairsData?.length || 0, color: "#5a6a82" },
                    { label: "SIGNALS", value: signalsCount, color: "#10b981" },
                    { label: "BLOCKED", value: blockedCount, color: "#f59e0b" },
                    { label: "OPEN POSITIONS", value: positionsData?.length || 0, color: "#2d7aed" },
                    { label: "TOTAL PnL", value: `$${totalPnl.toFixed(2)}`, color: totalPnl >= 0 ? "#10b981" : "#ef4444" },
                ].map((s, idx) => (
                    <div key={idx} className="flex-1 min-w-[140px] px-6 py-4 border-r border-[#151f35] last:border-r-0 text-center group hover:bg-white/[0.02] transition-colors">
                        <div className="text-[8px] text-[#5a6a82] font-bold tracking-[0.15em] mb-1.5 uppercase">{s.label}</div>
                        <div className="text-xl font-bold tracking-tighter" style={{ color: s.color }}>{s.value}</div>
                    </div>
                ))}
            </div>

            {/* ═══ TAB BAR ═══ */}
            <div className="flex bg-[#080d18] border-b border-[#151f35]">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setView(tab.id)}
                        className={cn(
                            "px-6 py-3 text-[10px] font-bold tracking-widest uppercase transition-all relative",
                            view === tab.id ? "text-ui-cyan border-b-2 border-ui-cyan bg-white/[0.02]" : "text-[#5a6a82] hover:text-[#c8d6e5]"
                        )}
                    >
                        {tab.label} <span className="opacity-40 text-[9px] ml-1">({tab.count})</span>
                    </button>
                ))}
            </div>

            {/* ═══ MAIN CONTENT area ═══ */}
            <div className="p-4">
                <main className="min-h-[600px] border border-[#151f35] rounded-lg bg-[#0b1120] overflow-hidden shadow-2xl">
                    {view === 'scanner' && <ScannerTable />}

                    {view === 'positions' && (
                        <div className="flex flex-col items-center justify-center p-32 space-y-4 opacity-40">
                            <BarChart3 className="h-12 w-12 text-[#5a6a82]" />
                            <div className="text-sm font-bold uppercase tracking-[0.2em] text-[#5a6a82]">No Data Stream</div>
                            <p className="text-[10px] font-bold text-[#5a6a82]/60 uppercase tracking-tight">Waiting for market engagement signals...</p>
                        </div>
                    )}

                    {view === 'history' && (
                        <div className="flex flex-col items-center justify-center p-32 space-y-4 opacity-40">
                            <History className="h-12 w-12 text-[#5a6a82]" />
                            <div className="text-sm font-bold uppercase tracking-[0.2em] text-[#5a6a82]">History Empty</div>
                        </div>
                    )}

                    {view === 'logs' && (
                        <div className="h-[600px] flex flex-col">
                            <div className="px-4 py-2 bg-[#080d18] border-b border-[#151f35] flex items-center justify-between">
                                <span className="text-[9px] font-bold text-[#5a6a82] tracking-widest uppercase">System Log — Real-Time Stream</span>
                                <div className="flex gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-ui-green animate-pulse" />
                                    <span className="text-[8px] font-bold text-ui-green tracking-widest uppercase">Live</span>
                                </div>
                            </div>
                            <div className="p-4 font-mono text-[10px] space-y-1.5 overflow-y-auto no-scrollbar bg-[#06080f]/50 flex-1">
                                <LogLine ts="14:35:22" svc="scanner" msg="Scan complete: 190 pairs → 4 signals → 2 blocked" level="info" />
                                <LogLine ts="14:35:20" svc="scanner" msg="Fetching OHLCV for 22 instruments..." level="info" />
                                <LogLine ts="14:30:22" svc="recon" msg="Reconciliation OK: DB=1 Exchange=1 Orphans=0" level="warn" />
                                <LogLine ts="14:25:18" svc="dedup" msg="Blocked NOT/TURBO: Danger Zone |Z|=2.829 > safeMax=2.5" level="warn" />
                                <LogLine ts="14:25:15" svc="trade" msg="OPEN ETH/SOL: SHORT ETH $500 / LONG SOL $725 | Z=+2.187" level="info" />
                            </div>
                        </div>
                    )}
                </main>
            </div>

            {/* ═══ FOOTER ═══ */}
            <div className="bg-[#080d18] border-t border-[#151f35] px-6 py-2 flex justify-between items-center text-[8px] font-bold text-[#5a6a82] uppercase tracking-wider">
                <div className="flex items-center gap-4">
                    <span className="text-ui-accent flex items-center gap-1">
                        <Zap className="h-2 w-2 fill-ui-accent" /> PAIRS TRADE V2.0
                    </span>
                    <span className="text-[#151f35]">|</span>
                    <span>System Status: <span className={isConnected ? "text-ui-green" : "text-ui-red"}>{isConnected ? "Operational" : "Disconnected"}</span></span>
                </div>
                <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1"><Shield className="h-2 w-2" /> Anti-Liquidation Active</span>
                    <span className="text-[#151f35]">|</span>
                    <span className="text-[#c8d6e5]">Paper Trading Mode (Internal API)</span>
                </div>
            </div>
        </div>
    );
}

function LogLine({ ts, svc, msg, level }: any) {
    const levelColors: any = { info: "#5a6a82", warn: "#f59e0b", error: "#ef4444" };
    const svcColors: any = { scanner: "#06b6d4", trade: "#10b981", recon: "#f59e0b", dedup: "#a78bfa" };
    return (
        <div className="flex gap-3 items-start border-b border-white/[0.02] pb-1">
            <span className="text-[#5a6a82] min-w-[55px]">{ts}</span>
            <span style={{ color: levelColors[level] }} className="min-w-[35px] font-bold uppercase text-[8px] pt-0.5">{level}</span>
            <span style={{ color: svcColors[svc] }} className="min-w-[55px] font-bold text-[8px] pt-0.5">[{svc}]</span>
            <span className="text-[#c8d6e5]">{msg}</span>
        </div>
    );
}

