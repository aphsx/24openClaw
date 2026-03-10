import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, RefreshCw, Activity, Target, ShieldAlert, History as HistoryIcon, LayoutDashboard, Settings, Zap } from 'lucide-react';
import { fetchPairs, fetchPositions, triggerScan, socket } from '../lib/api';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';
import ScannerTab from './ScannerTab';

export function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs));
}

type TabType = 'SCANNER' | 'POSITIONS' | 'HISTORY' | 'CONFIG';

export default function Dashboard() {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<TabType>('SCANNER');
    const [autoScanEnabled, setAutoScanEnabled] = useState(false);
    const [isConnected, setIsConnected] = useState(socket.connected);

    useEffect(() => {
        function onConnect() { setIsConnected(true); }
        function onDisconnect() { setIsConnected(false); }
        function onPairsUpdate(newPairs: any) {
            queryClient.setQueryData(['pairs'], newPairs);
        }

        socket.on('connect', onConnect);
        socket.on('disconnect', onDisconnect);
        socket.on('pairs_update', onPairsUpdate);

        return () => {
            socket.off('connect', onConnect);
            socket.off('disconnect', onDisconnect);
            socket.off('pairs_update', onPairsUpdate);
        };
    }, [queryClient]);

    // Stats Data
    const { data: positionsData } = useQuery({ queryKey: ['positions'], queryFn: fetchPositions, refetchInterval: autoScanEnabled ? 10000 : false });
    const { data: pairsData } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs, refetchInterval: autoScanEnabled ? 10000 : false });

    // Calculate some simple stats based on the data if needed (just counting them as per requirement "Dumb View")
    const activePositionsCount = positionsData?.length || 0;
    // If backend returns object with properties, we adjust. Assuming arrays for now.
    const signalsCount = pairsData?.filter((p: any) => p.zone === 'safe' || p.zone === 'caution').length || 0;

    const scanMutation = useMutation({
        mutationFn: triggerScan,
    });

    const handleScanNow = () => {
        scanMutation.mutate();
    };

    const tabs: { id: TabType; label: string; icon: any }[] = [
        { id: 'SCANNER', label: 'SCANNER', icon: Activity },
        { id: 'POSITIONS', label: 'POSITIONS', icon: LayoutDashboard },
        { id: 'HISTORY', label: 'HISTORY', icon: HistoryIcon },
        { id: 'CONFIG', label: 'CONFIG', icon: Settings },
    ];

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white font-mono flex flex-col">
            {/* Header */}
            <header className="border-b border-[#1f2937] bg-[#111827] px-6 py-4 flex items-center justify-between shadow-lg">
                <div className="flex items-center space-x-3">
                    <div className="bg-[#3b82f6] p-2 rounded-lg">
                        <Activity className="h-6 w-6 text-white" />
                    </div>
                    <h1 className="text-xl font-bold tracking-tight">PAIRS TRADING <span className="text-[#3b82f6]">CLAW</span></h1>
                </div>

                <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-3 bg-[#0a0e17] px-4 py-2 rounded-lg border border-[#1f2937]">
                        <span className="text-sm text-gray-400">Auto Scan (10s):</span>
                        <button
                            onClick={() => setAutoScanEnabled(!autoScanEnabled)}
                            className={cn(
                                "w-12 h-6 rounded-full transition-colors flex items-center px-1 relative",
                                autoScanEnabled ? "bg-[#3b82f6]" : "bg-gray-600"
                            )}
                        >
                            <div className={cn(
                                "w-4 h-4 bg-white rounded-full transition-transform",
                                autoScanEnabled ? "translate-x-6" : "translate-x-0"
                            )} />
                        </button>
                    </div>

                    <button
                        onClick={handleScanNow}
                        disabled={scanMutation.isPending}
                        className="flex items-center space-x-2 bg-[#3b82f6] hover:bg-blue-600 transition text-white px-5 py-2.5 rounded-lg font-medium tracking-wide disabled:opacity-50"
                    >
                        {scanMutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        <span>SCAN NOW</span>
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 p-6 flex flex-col space-y-6">

                {/* Stats Bar */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <StatCard title="Active Positions" value={activePositionsCount} icon={<Target className="text-[#3b82f6]" />} />
                    <StatCard title="Actionable Signals" value={signalsCount} icon={<Activity className="text-[#22c55e]" />} />
                    <StatCard title="Active TP/SL" value="--" icon={<ShieldAlert className="text-[#f97316]" />} subtitle="Controlled by Backend" />
                    <StatCard
                        title="System Status"
                        value={isConnected ? "Live (Socket)" : "Offline"}
                        icon={<Zap className={isConnected ? "text-[#eab308]" : "text-gray-500"} />}
                        valueColor={isConnected ? "text-[#eab308]" : "text-gray-500"}
                    />
                </div>

                {/* Navigation Tabs */}
                <div className="bg-[#111827] rounded-xl border border-[#1f2937] p-2 flex space-x-2">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex-1 flex items-center justify-center space-x-2 py-3 rounded-lg font-medium transition-all shadow-sm",
                                    isActive
                                        ? "bg-[#3b82f6] text-white"
                                        : "text-gray-400 hover:text-white hover:bg-[#1f2937]/50"
                                )}
                            >
                                <Icon className="h-5 w-5" />
                                <span>{tab.label}</span>
                            </button>
                        )
                    })}
                </div>

                {/* Tab Content Section (Placeholders for next steps) */}
                <div className="flex-1 bg-[#111827] border border-[#1f2937] rounded-xl p-6 shadow-xl">
                    {activeTab === 'SCANNER' && <ScannerTab />}
                    {activeTab === 'POSITIONS' && <div className="text-gray-400">Positions View (Pending Step 4)</div>}
                    {activeTab === 'HISTORY' && <div className="text-gray-400">History View (Pending Step 4)</div>}
                    {activeTab === 'CONFIG' && <div className="text-gray-400">Config View (Pending Step 5)</div>}
                </div>

            </main>
        </div>
    );
}

function StatCard({ title, value, icon, subtitle, valueColor = "text-white" }: { title: string, value: string | number, icon: React.ReactNode, subtitle?: string, valueColor?: string }) {
    return (
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg flex flex-col justify-between hover:border-[#3b82f6]/50 transition-colors">
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-gray-400 font-medium text-sm">{title}</h3>
                <div className="p-2 bg-[#0a0e17] rounded-lg">
                    {icon}
                </div>
            </div>
            <div>
                <div className={cn("text-2xl font-bold", valueColor)}>{value}</div>
                {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
            </div>
        </div>
    );
}
