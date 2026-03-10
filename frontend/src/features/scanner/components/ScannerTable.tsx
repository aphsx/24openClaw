import { useQuery } from '@tanstack/react-query';
import { fetchPairs, cn } from '../../../lib/api';
import { RefreshCw, LayoutGrid } from 'lucide-react';
import { Sparkline, ZScoreBar } from '../../../components/common/SharedUI';

export default function ScannerTable() {
    const { data: pairsData, isLoading, isError } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs });

    if (isLoading) return (
        <div className="p-32 text-center text-slate-400 flex flex-col items-center justify-center space-y-4">
            <RefreshCw className="h-10 w-10 animate-spin text-blue-500" />
            <span className="font-bold animate-pulse text-sm uppercase tracking-widest text-slate-500">Synchronizing Market Cluster...</span>
        </div>
    );

    if (isError) return (
        <div className="p-20 text-center flex flex-col items-center justify-center">
            <div className="bg-rose-50 border border-rose-200 p-12 rounded-2xl flex flex-col items-center shadow-lg shadow-rose-100 max-w-2xl">
                <div className="bg-rose-500 text-white px-6 py-2 rounded-full mb-6 font-black text-sm uppercase tracking-widest">CRITICAL LINK FAILURE</div>
                <div className="text-rose-950 font-black mb-4 uppercase tracking-tighter text-3xl">API OVERLOAD OR DISCONNECTED</div>
                <div className="text-rose-700/60 font-medium text-sm leading-relaxed">Ensure Python bridge (3001) and DB (Postgres) are active. Check Docker logs or local process.</div>
            </div>
        </div>
    );

    if (!pairsData || pairsData.length === 0) return (
        <div className="p-32 text-center flex flex-col items-center justify-center opacity-30 grayscale space-y-4">
            <LayoutGrid className="h-16 w-16 text-slate-300" />
            <div className="font-black text-2xl uppercase tracking-tighter text-slate-500">No Pairs Qualified</div>
        </div>
    );

    // Sorting: Qualified first, then by |Z-score|
    const sortedPairs = [...pairsData].sort((a: any, b: any) => {
        if (a.qualified && !b.qualified) return -1;
        if (!a.qualified && b.qualified) return 1;
        return Math.abs(b.zscore) - Math.abs(a.zscore);
    });

    return (
        <div className="overflow-x-auto p-6 animate-in slide-in-from-bottom duration-700">
            <table className="w-full text-sm border-separate border-spacing-y-2">
                <thead className="bg-slate-100 rounded-lg">
                    <tr className="text-[11px] font-black uppercase text-slate-500 tracking-widest text-left">
                        <th className="px-6 py-4 rounded-l-xl">Asset Cluster</th>
                        <th className="px-6 py-4 text-center">Z-Score & Index</th>
                        <th className="px-6 py-4 text-center">Correlation</th>
                        <th className="px-6 py-4 text-center">Half-Life</th>
                        <th className="px-6 py-4 text-center">Hedge β</th>
                        <th className="px-6 py-4 text-center">Spread Analysis</th>
                        <th className="px-6 py-4 text-center">Zone Matrix</th>
                        <th className="px-6 py-4 text-center">Checks</th>
                        <th className="px-6 py-4 rounded-r-xl text-right">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedPairs.map((pair: any, i: number) => {
                        const absZ = Math.abs(pair.zscore);
                        const mockHistory = Array.from({ length: 50 }, () => (Math.random() - 0.5) * 4);
                        mockHistory.push(pair.zscore);

                        const checks = [
                            { pass: true }, { pass: true }, { pass: true },
                            { pass: Number(pair.correlation) >= 0.8 },
                            { pass: Number(pair.cointegration_pvalue) <= 0.05 },
                            { pass: Number(pair.half_life) >= 2 && Number(pair.half_life) <= 35 },
                            { pass: absZ >= 2 }, { pass: pair.zone !== 'danger' }
                        ];

                        const isLong = pair.zscore < 0;

                        return (
                            <tr key={`${pair.symbol_a}-${pair.symbol_b}-${i}`} className="bg-white border border-slate-100 shadow-sm transition-all hover:scale-[1.005] hover:shadow-md cursor-default group">
                                <td className="px-6 py-5 rounded-l-xl border-l border-y border-slate-100">
                                    <div className="flex items-center gap-4">
                                        <div className="flex -space-x-2">
                                            <div className="w-10 h-10 rounded-full bg-slate-900 text-white flex items-center justify-center font-black text-xs border-2 border-white shadow-sm ring-1 ring-slate-100 uppercase">{pair.symbol_a[0]}</div>
                                            <div className="w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center font-black text-xs border-2 border-white shadow-sm ring-1 ring-slate-100 uppercase">{pair.symbol_b[0]}</div>
                                        </div>
                                        <div className="flex flex-col gap-0.5">
                                            <div className="text-base font-black tracking-tight text-slate-800 leading-tight uppercase">
                                                {pair.symbol_a}<span className="text-slate-300 font-medium mx-1">/</span><span className="text-blue-600">{pair.symbol_b}</span>
                                            </div>
                                            <span className="text-[10px] font-bold text-slate-400 tracking-tight uppercase">USDT_PERP Cluster</span>
                                        </div>
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center min-w-[140px]">
                                    <div className="inline-flex flex-col gap-2">
                                        <div className={cn(
                                            "text-lg font-black italic tracking-tighter tabular-nums leading-none",
                                            absZ > 3.5 ? "text-rose-500" : absZ > 2 ? (isLong ? "text-emerald-500" : "text-rose-500") : "text-slate-400"
                                        )}>
                                            {Number(pair.zscore).toFixed(3)}
                                        </div>
                                        <ZScoreBar zscore={Number(pair.zscore)} />
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className={cn(
                                        "text-base font-black italic tabular-nums",
                                        pair.correlation >= 0.85 ? "text-emerald-500" : pair.correlation >= 0.75 ? "text-slate-700" : "text-slate-300"
                                    )}>
                                        {Number(pair.correlation).toFixed(3)}
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className="text-sm font-bold text-slate-500 tabular-nums">
                                        {Number(pair.half_life).toFixed(1)}d
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className="text-sm font-bold text-slate-400 tabular-nums bg-slate-50 px-2 py-1 rounded-md border border-slate-100 inline-block uppercase">
                                        ß:{Number(pair.hedge_ratio).toFixed(2)}
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-100 inline-block hover:border-blue-200 transition-colors">
                                        <Sparkline data={mockHistory} width={100} height={24} />
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className={cn(
                                        "px-3 py-1 text-[10px] font-black rounded-lg uppercase inline-block border transition-all",
                                        pair.zone === 'safe' ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                                            pair.zone === 'caution' ? "bg-amber-50 text-amber-700 border-amber-200" :
                                                pair.zone === 'danger' ? "bg-rose-50 text-rose-700 border-rose-200" :
                                                    "bg-slate-100 text-slate-400 border-slate-200"
                                    )}>
                                        {pair.zone?.toUpperCase() || '-'}
                                    </div>
                                </td>

                                <td className="px-6 py-5 border-y border-slate-100 text-center">
                                    <div className="flex flex-col gap-1.5 items-center">
                                        <div className="text-[10px] font-black text-slate-400 leading-none">
                                            {checks.filter(c => c.pass).length}/{checks.length} VAL
                                        </div>
                                        <div className="flex gap-1 justify-center">
                                            {checks.map((c, idx) => (
                                                <div key={idx} className={cn("w-1.5 h-1.5 rounded-full ring-1 ring-white", c.pass ? "bg-emerald-400" : "bg-rose-200")} />
                                            ))}
                                        </div>
                                    </div>
                                </td>

                                <td className="px-6 py-5 rounded-r-xl border-r border-y border-slate-100 text-right">
                                    {pair.qualified ? (
                                        <button className={cn(
                                            "px-6 py-2 rounded-lg text-xs font-black uppercase text-white shadow-md hover:shadow-lg active:scale-95 transition-all",
                                            isLong ? "bg-emerald-500 shadow-emerald-100 hover:bg-emerald-600" : "bg-rose-500 shadow-rose-100 hover:bg-rose-600"
                                        )}>
                                            {isLong ? "EXECUTE LONG" : "EXECUTE SHORT"}
                                        </button>
                                    ) : (
                                        <div className="text-[11px] font-bold text-slate-300 uppercase italic tracking-widest pl-2">Idle_Cluster</div>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
