import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap, History, Shield, RefreshCw, BarChart3, Activity } from 'lucide-react';
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
        <div className="min-h-screen bg-[#06080f] text-[#c8d6e5] font-mono flex flex-col">

            {/* ═══ TOP NAVIGATION ═══ */}
            <header className="bg-[#080d18] border-b border-[#151f35] sticky top-0 z-50">
                <div className="max-w-[1800px] mx-auto px-6 py-4 flex justify-between items-center bg-[#080d18]">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-ui-accent/20 rounded-lg flex items-center justify-center border border-ui-accent/30 shadow-[0_0_15px_rgba(45,122,237,0.1)]">
                                <Zap className="w-4 h-4 text-ui-accent fill-ui-accent" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-sm font-black text-white tracking-[0.1em] leading-none mb-1">TRADINGCLAW</span>
                                <span className="text-[9px] text-[#5a6a82] font-bold tracking-widest uppercase">Statistical Arbitrage Engine</span>
                            </div>
                        </div>
                        <div className="h-6 w-[1px] bg-[#151f35]" />
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 px-3 py-1 bg-[#151f35]/30 rounded-full border border-[#151f35]">
                                <div className={cn("w-1.5 h-1.5 rounded-full", isConnected ? "bg-ui-green" : "bg-ui-red animate-pulse")} />
                                <span className="text-[9px] font-bold text-[#5a6a82] uppercase">{isConnected ? "Operational" : "Disconnected"}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-4 border-r border-[#151f35] pr-6">
                            <div className="text-right">
                                <div className="text-[9px] text-[#5a6a82] font-bold uppercase tracking-widest mb-0.5">Automated Scan</div>
                                <div className="text-[10px] font-bold text-white uppercase">{autoScan ? "Mode: Active" : "Mode: Manual"}</div>
                            </div>
                            <button
                                onClick={() => setAutoScan(!autoScan)}
                                className={cn(
                                    "w-10 h-5 rounded-full relative transition-all duration-300 border",
                                    autoScan ? "bg-ui-green/20 border-ui-green/40 shadow-[0_0_10px_rgba(16,185,129,0.1)]" : "bg-[#151f35] border-[#334155]"
                                )}
                            >
                                <div className={cn(
                                    "absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all duration-300 shadow-sm",
                                    autoScan ? "right-1 bg-ui-green" : "left-1 bg-[#5a6a82]"
                                )} />
                            </button>
                        </div>
                        <button
                            onClick={runScan}
                            disabled={scanMutation.isPending}
                            className={cn(
                                "px-6 py-2.5 rounded-lg bg-ui-accent hover:bg-ui-accent/90 hover:shadow-[0_0_20px_rgba(45,122,237,0.3)] text-white text-[11px] font-black tracking-widest uppercase transition-all active:scale-95 disabled:opacity-30 flex items-center gap-3",
                                scanMutation.isPending && "animate-pulse"
                            )}
                        >
                            {scanMutation.isPending ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Activity className="w-3 h-3" />}
                            {scanMutation.isPending ? "Executing Scan..." : "Force Scan Now"}
                        </button>
                    </div>
                </div>
            </header>

            {/* ═══ STATS OVERVIEW ═══ */}
            <div className="bg-[#06080f] border-b border-[#151f35]">
                <div className="max-w-[1800px] mx-auto flex divide-x divide-[#151f35]">
                    {[
                        { label: "Assets Scanned", value: pairsData?.length || 0, color: "#5a6a82" },
                        { label: "Active Signals", value: signalsCount, color: "#10b981", highlight: signalsCount > 0 },
                        { label: "Safety Blocked", value: blockedCount, color: "#f59e0b" },
                        { label: "Open Positions", value: positionsData?.length || 0, color: "#2d7aed" },
                        { label: "Net PnL (Est)", value: `$${totalPnl.toFixed(2)}`, color: totalPnl >= 0 ? "#10b981" : "#ef4444" },
                        { label: "Engine Status", value: `SCAN #${scanCount}`, color: "#06b6d4" },
                    ].map((s, idx) => (
                        <div key={idx} className={cn(
                            "flex-1 px-8 py-6 group transition-all hover:bg-white/[0.03] text-center relative overflow-hidden",
                            s.highlight && "bg-ui-green/[0.03]"
                        )}>
                            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.01] to-transparent pointer-events-none" />
                            <div className="relative z-10 transition-transform group-hover:scale-[1.02]">
                                <div className="text-[9px] text-[#5a6a82] font-bold tracking-[0.2em] mb-2 uppercase opacity-80 group-hover:opacity-100 transition-opacity">{s.label}</div>
                                <div className="text-2xl font-black tracking-tight" style={{ color: s.color }}>{s.value}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ═══ MAIN DASHBOARD AREA ═══ */}
            <div className="max-w-[1800px] mx-auto w-full p-6 space-y-6 flex-1">

                {/* View Switcher/Tab bar Container */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 p-1 bg-[#151f35]/50 border border-[#151f35] rounded-xl w-fit backdrop-blur-sm">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setView(tab.id)}
                                className={cn(
                                    "px-6 py-2.5 rounded-lg text-[10px] font-bold tracking-widest uppercase transition-all",
                                    view === tab.id
                                        ? "bg-[#151f35] text-ui-cyan shadow-lg border border-[#334155]/30"
                                        : "text-[#5a6a82] hover:text-[#c8d6e5] hover:bg-white/[0.02]"
                                )}
                            >
                                {tab.label}
                                {tab.count > 0 && <span className="ml-2 opacity-40 text-[9px]">[{tab.count}]</span>}
                            </button>
                        ))}
                    </div>

                    <div className="text-[9px] font-bold text-[#5a6a82] tracking-widest uppercase flex items-center gap-3">
                        <span className="opacity-50">Local Time:</span>
                        <span className="text-white tabular-nums tracking-normal">{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
                    </div>
                </div>

                <div className="bg-[#0b1120] border border-[#151f35] rounded-2xl overflow-hidden shadow-2xl min-h-[600px] flex flex-col">
                    <div className="flex-1">
                        {view === 'scanner' && <ScannerTable />}

                        {view === 'positions' && (
                            <div className="flex flex-col items-center justify-center p-32 space-y-6 opacity-40">
                                <div className="w-16 h-16 rounded-3xl bg-[#080d18] border border-[#151f35] flex items-center justify-center">
                                    <BarChart3 className="h-8 w-8 text-[#5a6a82]" />
                                </div>
                                <div className="text-center space-y-2">
                                    <div className="text-sm font-bold uppercase tracking-[0.2em] text-[#c8d6e5]">Market Engagement: Zero</div>
                                    <p className="text-[10px] font-bold text-[#5a6a82] uppercase tracking-wide">Awaiting Signal Execution from Engine</p>
                                </div>
                            </div>
                        )}

                        {view === 'history' && (
                            <div className="flex flex-col items-center justify-center p-32 space-y-6 opacity-40">
                                <div className="w-16 h-16 rounded-3xl bg-[#080d18] border border-[#151f35] flex items-center justify-center">
                                    <History className="h-8 w-8 text-[#5a6a82]" />
                                </div>
                                <div className="text-sm font-bold uppercase tracking-[0.2em] text-[#c8d6e5]">Trade Ledger Empty</div>
                            </div>
                        )}

                        {view === 'logs' && (
                            <div className="h-[600px] flex flex-col">
                                <div className="px-6 py-4 bg-[#080d18] border-b border-[#151f35] flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-ui-green animate-pulse" />
                                        <span className="text-[10px] font-black text-[#c8d6e5] tracking-widest uppercase">System Event Stream</span>
                                    </div>
                                    <span className="text-[9px] font-bold text-[#5a6a82] uppercase">Buffer Status: OK [128 KB]</span>
                                </div>
                                <div className="p-6 font-mono text-[11px] space-y-2.5 overflow-y-auto bg-[#06080f]/50 flex-1">
                                    <LogLine ts="14:35:22" svc="scanner" msg="Scan complete: 190 pairs → 4 signals → 2 blocked" level="info" />
                                    <LogLine ts="14:35:20" svc="scanner" msg="Fetching OHLCV for 22 instruments..." level="info" />
                                    <LogLine ts="14:30:22" svc="recon" msg="Reconciliation OK: DB=1 Exchange=1 Orphans=0" level="warn" />
                                    <LogLine ts="14:25:18" svc="dedup" msg="Blocked NOT/TURBO: Danger Zone |Z|=2.829 > safeMax=2.5" level="warn" />
                                    <LogLine ts="14:25:15" svc="trade" msg="OPEN ETH/SOL: SHORT ETH $500 / LONG SOL $725 | Z=+2.187" level="info" />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* ═══ FOOTER ═══ */}
            <footer className="bg-[#080d18] border-t border-[#151f35] py-3 mt-auto">
                <div className="max-w-[1800px] mx-auto px-6 flex justify-between items-center text-[9px] font-bold text-[#5a6a82] uppercase tracking-wider">
                    <div className="flex items-center gap-6">
                        <span className="text-ui-accent flex items-center gap-2">
                            PLUME ALPHA v2.0
                        </span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span className="flex items-center gap-2 italic uppercase">
                            <Shield className="h-3 w-3" /> Kernel-Level Trade Protection Active
                        </span>
                    </div>
                    <div className="flex items-center gap-6">
                        <span className="text-ui-orange">Node: OKX-US-EAST-1</span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span className="text-[#c8d6e5]">Mode: Paper Simulation</span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span>Sync: <span className="text-white">{lastScan.toLocaleTimeString("en-GB", { hour12: false })}</span></span>
                    </div>
                </div>
            </footer>
        </div>
    );
}

function LogLine({ ts, svc, msg, level }: any) {
    const levelColors: any = { info: "#5a6a82", warn: "#f59e0b", error: "#ef4444" };
    const svcColors: any = { scanner: "#06b6d4", trade: "#10b981", recon: "#f59e0b", dedup: "#a78bfa" };
    return (
        <div className="flex gap-4 items-start border-b border-white/[0.02] pb-2 last:border-0 text-left">
            <span className="text-[#5a6a82] min-w-[65px] tabular-nums">{ts}</span>
            <span style={{ color: levelColors[level] }} className="min-w-[45px] font-black uppercase text-[9px] pt-0.5">{level}</span>
            <span style={{ color: svcColors[svc] }} className="min-w-[65px] font-black text-[9px] pt-0.5">[{svc}]</span>
            <span className="text-[#c8d6e5] opacity-90">{msg}</span>
        </div>
    );
}

