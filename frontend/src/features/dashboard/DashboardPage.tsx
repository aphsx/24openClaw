import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Activity, Target, Zap, History, Settings, List, Shield } from 'lucide-react';
import { fetchPairs, fetchPositions, triggerScan, socket, cn } from '../../lib/api';
import ScannerTable from '../scanner/components/ScannerTable';

export default function DashboardPage() {
    const queryClient = useQueryClient();
    const [view, setView] = useState('scanner');
    const [autoScan, setAutoScan] = useState(false);
    const [isConnected, setIsConnected] = useState(socket.connected);

    useEffect(() => {
        socket.on('connect', () => setIsConnected(true));
        socket.on('disconnect', () => setIsConnected(false));
        socket.on('pairs_update', () => queryClient.invalidateQueries({ queryKey: ['pairs'] }));

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
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pairs'] }),
    });

    const stats = [
        { label: "Positions", value: positionsData?.length || 0, color: "#3b82f6", icon: "📊" },
        { label: "Signals", value: pairsData?.filter((p: any) => p.qualified).length || 0, color: "#10b981", icon: "📡" },
        { label: "Blocked", value: 0, color: "#f59e0b", icon: "🚫" },
        { label: "Opened", value: positionsData?.length || 0, color: "#8b5cf6", icon: "🟢" },
        { label: "TP", value: 0, color: "#10b981", icon: "💰" },
        { label: "SL", value: 0, color: "#ef4444", icon: "🛑" },
        { label: "Cooldowns", value: 0, color: "#64748b", icon: "⏳" },
    ];

    const tabs = [
        { id: "scanner", label: `📡 SCANNER (${pairsData?.length || 0})` },
        { id: "positions", label: `📊 POSITIONS (${positionsData?.length || 0})` },
        { id: "history", label: "📋 HISTORY" },
        { id: "logs", label: "📝 LOGS" },
        { id: "config", label: "⚙️ CONFIG" },
    ];

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-4 space-y-6 max-w-[1600px] mx-auto selection:bg-blue-100 animate-in fade-in duration-500">

            {/* ═══ HEADER ═══ */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-white border border-slate-200 px-6 py-4 rounded-xl shadow-sm">
                <div className="flex items-center gap-4">
                    <div className="text-2xl font-black italic tracking-tighter text-blue-600 uppercase flex items-center gap-2">
                        <Zap className="h-7 w-7 fill-blue-600 text-blue-100" />
                        PAIRS SCANNER
                    </div>
                    <div className="text-[10px] font-bold bg-slate-900 text-white px-2 py-0.5 rounded-full">v2.0 PRO — PYTHON</div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => scanMutation.mutate()}
                        disabled={scanMutation.isPending}
                        className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-bold shadow-md hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
                    >
                        🔍 Scan Now
                    </button>
                    <button
                        onClick={() => setAutoScan(!autoScan)}
                        className={cn(
                            "px-6 py-2 rounded-lg text-sm font-bold border transition-all flex items-center gap-2",
                            autoScan ? "bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm shadow-emerald-100" : "bg-slate-100 text-slate-600 border-slate-200"
                        )}
                    >
                        <div className={cn("w-2 h-2 rounded-full", autoScan ? "bg-emerald-500 animate-pulse" : "bg-slate-400")} />
                        {autoScan ? "AUTO ON" : "AUTO OFF"}
                    </button>
                    <div className="text-[11px] font-bold text-slate-400 uppercase pl-4 border-l border-slate-200 flex items-center gap-2">
                        System: <span className={cn("inline-flex items-center gap-1", isConnected ? "text-emerald-500" : "text-rose-500")}>
                            {isConnected ? "Connected" : "Disconnected"}
                        </span>
                    </div>
                </div>
            </div>

            {/* ═══ STATS BAR ═══ */}
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-4">
                {stats.map((s) => (
                    <div key={s.label} className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm group hover:border-blue-200 transition-all">
                        <div className="text-[10px] font-bold uppercase text-slate-400 mb-2 flex items-center gap-1">
                            {s.icon} {s.label}
                        </div>
                        <div className="text-3xl font-black italic tracking-tighter" style={{ color: s.color }}>{s.value}</div>
                    </div>
                ))}
            </div>

            {/* ═══ TAB BAR ═══ */}
            <div className="dashboard-card bg-slate-100 p-1.5 flex flex-wrap gap-1">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setView(tab.id)}
                        className={cn(
                            "tab-item px-6 py-2.5",
                            view === tab.id ? "tab-item-active font-bold" : "tab-item-inactive font-semibold"
                        )}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* ═══ MAIN CONTENT area ═══ */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm min-h-[600px] overflow-hidden">
                {view === 'scanner' && <ScannerTable />}

                {view === 'positions' && (
                    <div className="flex flex-col items-center justify-center p-32 space-y-4 opacity-50 grayscale">
                        <Activity className="h-20 w-20 text-slate-300" />
                        <div className="text-2xl font-black uppercase text-slate-400">No Market Engagement</div>
                        <p className="text-sm font-medium text-slate-500 uppercase tracking-tight">The engine is currently in monitoring mode.</p>
                    </div>
                )}

                {view === 'history' && (
                    <div className="flex flex-col items-center justify-center p-32 space-y-4 opacity-50 grayscale text-center">
                        <History className="h-20 w-20 text-slate-300" />
                        <div className="text-2xl font-black uppercase text-slate-400 tracking-tighter">Zero Logs Detected</div>
                    </div>
                )}

                {view === 'logs' && (
                    <div className="p-8 font-mono text-[12px] space-y-3 bg-slate-900 text-slate-300 max-h-[600px] overflow-y-auto">
                        <div className="flex gap-4 border-b border-white/5 pb-2">
                            <span className="text-blue-400">[14:06:57]</span>
                            <span className="font-bold text-emerald-400">[ENGINE]</span>
                            <span>Statistical cluster initialized. Listening for python socket payload...</span>
                        </div>
                        <div className="flex gap-4 border-b border-white/5 pb-2">
                            <span className="text-blue-400">[14:07:01]</span>
                            <span className="font-bold text-blue-400">[INFO]</span>
                            <span>Qualified 18 assets for USDT/PERP cluster scan.</span>
                        </div>
                    </div>
                )}

                {view === 'config' && (
                    <div className="p-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                        <div className="space-y-6">
                            <h3 className="font-black uppercase tracking-tight text-lg border-b border-slate-100 pb-2 flex gap-2 items-center text-slate-800">
                                <Target className="h-5 w-5 text-blue-500" /> Statistical Thresholds
                            </h3>
                            <div className="grid gap-3">
                                <ConfigItem label="Z-Score Entry" value="2.0" />
                                <ConfigItem label="Min Correlation" value="0.85" />
                                <ConfigItem label="Half-Life Limit" value="2 - 30 days" />
                            </div>
                        </div>
                        <div className="space-y-6">
                            <h3 className="font-black uppercase tracking-tight text-lg border-b border-slate-100 pb-2 flex gap-2 items-center text-slate-800">
                                <Shield className="h-5 w-5 text-emerald-500" /> Safety Protocols
                            </h3>
                            <div className="grid gap-3">
                                <div className="flex items-center gap-3 text-[11px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 p-2 rounded-lg">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                                    DB-FIRST STORAGE PROTECTION ACTIVE
                                </div>
                                <div className="flex items-center gap-3 text-[11px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 p-2 rounded-lg">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                                    MULTI-INSTANCING CLEANUP ACTIVE
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* ═══ FOOTER ═══ */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-white border border-slate-200 px-6 py-4 rounded-xl text-[11px] font-bold text-slate-400 uppercase tracking-tight shadow-sm">
                <div className="flex items-center gap-4">
                    <span className="text-blue-600 font-black flex items-center gap-1"><Zap className="h-3 w-3 fill-blue-600" /> PLUME v2.0 PRO</span>
                    <span className="text-slate-200">|</span>
                    <span>Monitoring across USDT-PERP markets</span>
                </div>
                <div className="text-slate-900 border-l border-slate-200 pl-4">
                    ⚠️ Paper Trading Simulation Active
                </div>
            </div>
        </div>
    );
}

function ConfigItem({ label, value }: { label: string, value: string }) {
    return (
        <div className="flex items-center justify-between p-3 border border-slate-100 bg-slate-50/50 rounded-lg">
            <span className="text-[11px] font-bold text-slate-400 uppercase">{label}</span>
            <span className="font-bold text-sm bg-white border border-slate-200 px-3 py-1 rounded-md text-slate-700">{value}</span>
        </div>
    );
}
