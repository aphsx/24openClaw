import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Zap,
    Shield,
    RefreshCw,
    BarChart3,
    Activity,
    ChevronLeft,
    Database,
    LayoutDashboard,
    Wallet,
    TrendingUp,
    Lock,
    Settings,
    Layers,
    AlertCircle,
    Unplug
} from 'lucide-react';
import { fetchPairs, fetchPositions, triggerScan, socket, cn } from '../../lib/api';
import ScannerTable from '../scanner/components/ScannerTable';

export default function DashboardPage() {
    const queryClient = useQueryClient();
    const [view, setView] = useState('positions');
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

    const { data: pairsData, isError: isPairsError } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs, refetchInterval: autoScan ? 5000 : false });
    const { data: positionsData, isError: isPositionsError } = useQuery({ queryKey: ['positions'], queryFn: fetchPositions });

    const scanMutation = useMutation({
        mutationFn: triggerScan,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['pairs'] });
            setScanCount(c => c + 1);
            setLastScan(new Date());
        },
    });

    const runScan = () => scanMutation.mutate();

    // Derived State
    const hasApiControl = isConnected && !isPositionsError;
    const exchangePositions = positionsData?.filter((p: any) => !p.is_pair) || [];
    const pairPositions = positionsData?.filter((p: any) => p.is_pair) || [];

    const portfolioStats = [
        { label: "TOTAL EQUITY", value: hasApiControl ? "$0.00" : "N/A", icon: Wallet, glow: true, color: "text-white", sub: hasApiControl ? "Live" : "API Required" },
        { label: "AVAILABLE", value: hasApiControl ? "$0.00" : "N/A", icon: Database, color: "text-ui-accent" },
        { label: "UNREALIZED P&L", value: hasApiControl ? "$0.0000" : "N/A", icon: TrendingUp, color: "text-ui-green" },
        { label: "FROZEN", value: hasApiControl ? "$0.00" : "N/A", icon: Lock, color: "text-ui-orange" },
        { label: "ACCOUNT TYPE", value: hasApiControl ? "Spot/Futures" : "UNKNOWN", icon: Settings, color: "text-[#c8d6e5]" },
        { label: "POS MODE", icon: Layers, value: hasApiControl ? "Hedge" : "UNKNOWN", color: "text-[#c8d6e5]" },
    ];

    const subStats = [
        { label: "REALIZED P&L", value: "$0.00", color: "text-ui-green" },
        { label: "TOTAL FEES", value: "$0.00", color: "text-[#5a6a82]" },
        { label: "TOTAL TRADES", value: "0", color: "text-white" },
        { label: "OPEN POS", value: exchangePositions.length.toString(), color: "text-ui-accent" },
        { label: "PAIR TRADES", value: pairPositions.length.toString(), color: "text-ui-green" },
        { label: "WIN RATE", value: "0%", color: "text-[#5a6a82]" },
        { label: "AVG WIN", value: "+0.00%", color: "text-ui-green" },
        { label: "AVG LOSS", value: "+0.00%", color: "text-ui-red" },
        { label: "PROFIT FACTOR", value: "0", color: "text-[#5a6a82]" },
        { label: "BEST TRADE", value: "+0.00%", color: "text-ui-green" },
        { label: "WORST TRADE", value: "+0.00%", color: "text-ui-red" },
    ];

    const tabs = [
        { id: "overview", label: "OVERVIEW" },
        { id: "positions", label: "POSITIONS" },
        { id: "history", label: "HISTORY" },
        { id: "performance", label: "PERFORMANCE" },
        { id: "scanner", label: "SCANNER" },
    ];

    return (
        <div className="min-h-screen bg-[#020408] text-[#c8d6e5] font-sans flex flex-col selection:bg-ui-accent/30">

            {/* ═══ TOP NAVIGATION ═══ */}
            <header className="bg-[#05080f] border-b border-[#151f35] sticky top-0 z-50">
                <div className="max-w-[1800px] mx-auto px-6 py-3.5 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <button className="flex items-center gap-1.5 text-[10px] font-bold text-[#5a6a82] hover:text-[#c8d6e5] transition-colors uppercase tracking-widest">
                            <ChevronLeft className="w-3.5 h-3.5" />
                            DASHBOARD
                        </button>
                        <div className="w-[1px] h-4 bg-[#151f35]" />
                        <div className="flex items-center gap-2.5">
                            <LayoutDashboard className="w-4 h-4 text-ui-accent" />
                            <span className="text-xs font-black text-white tracking-[0.2em] uppercase">PORTFOLIO</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className={cn(
                            "flex items-center gap-1.5 px-3 py-1 border rounded-md transition-colors",
                            isConnected ? "bg-ui-green/5 border-ui-green/20" : "bg-ui-red/5 border-ui-red/20"
                        )}>
                            <div className={cn("w-1.5 h-1.5 rounded-full", isConnected ? "bg-ui-green" : "bg-ui-red animate-pulse")} />
                            <span className={cn("text-[9px] font-black uppercase tracking-widest", isConnected ? "text-ui-green" : "text-ui-red")}>
                                {isConnected ? "CONNECTED" : "OFFLINE"}
                            </span>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[8px] text-[#5a6a82] font-bold uppercase tracking-widest">Account UID</span>
                            <span className="text-[10px] font-bold text-white tabular-nums tracking-wide">{hasApiControl ? "6514087624" : "UNLINKED"}</span>
                        </div>
                        <button
                            onClick={() => queryClient.invalidateQueries()}
                            className="flex items-center gap-2 text-[9px] font-black text-[#5a6a82] hover:text-white transition-colors uppercase tracking-widest"
                        >
                            <RefreshCw className="w-3 h-3" />
                            REFRESH
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-[1800px] mx-auto w-full p-6 space-y-8 flex-1">

                <div className="flex justify-end">
                    <span className="text-[8px] font-bold text-[#5a6a82] uppercase tracking-[0.2em] italic">LIVE — updates every 30s</span>
                </div>

                {/* ═══ MAIN STATS CARDS ═══ */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
                    {portfolioStats.map((stat, idx) => (
                        <div key={idx} className={cn(
                            "stat-card-premium flex flex-col gap-3 relative overflow-hidden group hover:bg-[#0c1425]",
                            stat.glow && hasApiControl && "glow-blue"
                        )}>
                            <div className="flex items-center justify-between">
                                <span className="text-[9px] font-black text-[#5a6a82] tracking-[0.15em] uppercase">{stat.label}</span>
                                <stat.icon className="w-3.5 h-3.5 text-[#5a6a82] opacity-40 group-hover:opacity-100 transition-opacity" />
                            </div>
                            <div className="flex flex-col">
                                <span className={cn("text-xl font-black tracking-tight", stat.color, stat.glow && hasApiControl && "text-glow-blue")}>
                                    {stat.value}
                                </span>
                                {!hasApiControl && (
                                    <span className="text-[7px] font-bold text-ui-red/60 uppercase tracking-tighter mt-1">Connection Required</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* ═══ SUB STATS BAR ═══ */}
                <div className="bg-[#080d18] border border-[#151f35] rounded-xl px-8 py-4 flex items-center justify-between overflow-x-auto gap-8">
                    {subStats.map((s, idx) => (
                        <div key={idx} className="flex flex-col items-center gap-1 min-w-fit">
                            <span className="text-[7px] text-[#5a6a82] font-black tracking-widest uppercase whitespace-nowrap">{s.label}</span>
                            <span className={cn("text-[11px] font-bold tabular-nums", s.color)}>{s.value}</span>
                        </div>
                    ))}
                </div>

                {/* ═══ TABS ═══ */}
                <div className="flex items-center gap-1 border-b border-[#151f35] px-2">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setView(tab.id)}
                            className={cn(
                                "px-6 py-3 text-[10px] font-bold tracking-[0.2em] uppercase transition-all relative",
                                view === tab.id
                                    ? "text-ui-accent after:content-[''] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-ui-accent"
                                    : "text-[#5a6a82] hover:text-[#c8d6e5]"
                            )}
                        >
                            <div className="flex items-center gap-2">
                                {tab.id === 'positions' && <BarChart3 className="w-3 h-3" />}
                                {tab.label}
                            </div>
                        </button>
                    ))}
                </div>

                {/* ═══ CONTENT AREA ═══ */}
                <div className="min-h-[500px]">
                    {view === 'positions' && (
                        <div className="space-y-8 animate-in fade-in duration-700">
                            {/* Exchange Positions Table */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <BarChart3 className="w-4 h-4 text-ui-accent" />
                                        <h2 className="text-[11px] font-black text-white tracking-[0.15em] uppercase">EXCHANGE POSITIONS ({exchangePositions.length})</h2>
                                    </div>
                                    <span className="text-[9px] font-bold text-[#5a6a82] uppercase tracking-[0.1em]">Real-time from Exchange API</span>
                                </div>

                                <div className="bg-[#05080f] border border-[#151f35] rounded-lg overflow-hidden">
                                    {exchangePositions.length > 0 ? (
                                        <table className="w-full text-left">
                                            <thead>
                                                <tr className="border-b border-[#151f35] bg-[#080d18]/50">
                                                    {["INSTRUMENT", "SIDE", "SIZE", "ENTRY", "MARK", "UPL", "UPL %", "LEVER", "MARGIN", "OPENED"].map(h => (
                                                        <th key={h} className="px-4 py-2.5 text-[8px] font-black text-[#5a6a82] tracking-widest uppercase">{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-[#151f35]">
                                                {exchangePositions.map((row: any, i: number) => (
                                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                                                        <td className="px-4 py-3 text-[10px] font-bold text-white">{row.symbol}</td>
                                                        <td className="px-4 py-3">
                                                            <span className={cn("text-[9px] font-black px-1.5 py-0.5 rounded", row.side === "LONG" ? "bg-ui-green/10 text-ui-green" : "bg-ui-red/10 text-ui-red")}>{row.side}</span>
                                                        </td>
                                                        <td className="px-4 py-3 text-[10px] font-bold tabular-nums text-[#c8d6e5]">{row.size}</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold tabular-nums text-[#5a6a82]">{row.entry}</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold tabular-nums text-[#5a6a82]">{row.mark}</td>
                                                        <td className={cn("px-4 py-3 text-[10px] font-black tabular-nums", row.pnl >= 0 ? "text-ui-green" : "text-ui-red")}>{row.pnl}</td>
                                                        <td className={cn("px-4 py-3 text-[10px] font-black tabular-nums", row.pnl >= 0 ? "text-ui-green" : "text-ui-red")}>{row.pnl_pct}%</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold text-[#c8d6e5]">{row.leverage}x</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold text-[#c8d6e5]">{row.margin}</td>
                                                        <td className="px-4 py-3 text-[9px] font-medium text-[#5a6a82] italic whitespace-nowrap">{new Date(row.timestamp).toLocaleTimeString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    ) : (
                                        <div className="p-20 flex flex-col items-center justify-center space-y-3 opacity-30">
                                            {isPositionsError ? <Unplug className="w-8 h-8 text-ui-red" /> : <Database className="w-8 h-8" />}
                                            <div className="text-center">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-[#c8d6e5]">
                                                    {isPositionsError ? "API BRIDGE OFFLINE" : "NO ACTIVE POSITIONS"}
                                                </p>
                                                <p className="text-[8px] font-bold uppercase tracking-widest text-[#5a6a82] mt-1">
                                                    {isPositionsError ? "Check backend connection status" : "Connect your exchange to monitor active trades"}
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Pair Trade Positions Table */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2.5">
                                    <TrendingUp className="w-4 h-4 text-ui-green" />
                                    <h2 className="text-[11px] font-black text-white tracking-[0.15em] uppercase">PAIR TRADE POSITIONS ({pairPositions.length})</h2>
                                </div>
                                <div className="bg-[#05080f] border border-[#151f35] rounded-lg overflow-hidden">
                                    {pairPositions.length > 0 ? (
                                        <table className="w-full text-left">
                                            <thead>
                                                <tr className="border-b border-[#151f35] bg-[#080d18]/50">
                                                    {["PAIR", "DIRECTION", "LEG A", "LEG B", "ENTRY Z", "CURRENT Z", "P&L", "STATUS"].map(h => (
                                                        <th key={h} className="px-4 py-2.5 text-[8px] font-black text-[#5a6a82] tracking-widest uppercase">{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-[#151f35]">
                                                {pairPositions.map((row: any, i: number) => (
                                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                                        <td className="px-4 py-3 text-[10px] font-bold text-white">{row.pair}</td>
                                                        <td className="px-4 py-3 text-[9px] font-black text-ui-accent">{row.direction}</td>
                                                        <td className="px-4 py-3 text-[9px] font-bold text-ui-red">{row.leg_a}</td>
                                                        <td className="px-4 py-3 text-[9px] font-bold text-ui-green">{row.leg_b}</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold tabular-nums text-ui-accent">{row.entry_z}</td>
                                                        <td className="px-4 py-3 text-[10px] font-bold tabular-nums text-ui-accent">{row.current_z}</td>
                                                        <td className={cn("px-4 py-3 text-[10px] font-bold", row.pnl >= 0 ? "text-ui-green" : "text-ui-red")}>{row.pnl}%</td>
                                                        <td className="px-4 py-3">
                                                            <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-ui-green/10 text-ui-green border border-ui-green/20">{row.status}</span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    ) : (
                                        <div className="p-20 flex flex-col items-center justify-center space-y-3 opacity-30">
                                            <Layers className="w-8 h-8" />
                                            <div className="text-center">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-[#c8d6e5]">NO ACTIVE PAIR TRADES</p>
                                                <p className="text-[8px] font-bold uppercase tracking-widest text-[#5a6a82] mt-1">Scanner will automatically trigger entries when Z-Score ≥ 2.5</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'scanner' && <ScannerTable />}

                    {view === 'overview' && (
                        <div className="flex flex-col items-center justify-center p-32 space-y-4 opacity-40">
                            <Activity className="w-12 h-12 text-[#5a6a82]" />
                            <span className="text-xs font-black uppercase tracking-widest text-center">Aggregation Engine Priming...</span>
                        </div>
                    )}
                </div>
            </main>

            {/* ═══ FOOTER ═══ */}
            <footer className="bg-[#05080f] border-t border-[#151f35] py-3 mt-auto selection:bg-none">
                <div className="max-w-[1800px] mx-auto px-6 flex justify-between items-center text-[9px] font-bold text-[#5a6a82] uppercase tracking-wider">
                    <div className="flex items-center gap-6">
                        <span className="text-ui-accent flex items-center gap-2">
                            PLUME ALPHA v2.1
                        </span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span className="flex items-center gap-2 italic">
                            <Shield className="h-3 w-3" /> Kernel-Level Trade Protection Active
                        </span>
                    </div>
                    <div className="flex items-center gap-6">
                        <span className="text-ui-orange">Node: OKX-US-EAST-1</span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span className="text-[#c8d6e5]">Mode: Paper Simulation</span>
                        <div className="h-3 w-[1px] bg-[#151f35]" />
                        <span>Sync Status: <span className={cn(isConnected ? "text-ui-green" : "text-ui-red")}>{isConnected ? "SYNCHRONIZED" : "ERROR"}</span></span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
