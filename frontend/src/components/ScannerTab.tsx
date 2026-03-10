import { useQuery } from '@tanstack/react-query';
import { fetchPairs } from '../lib/api';
import { cn } from './Dashboard';
import { RefreshCw } from 'lucide-react';

export default function ScannerTab() {
    const { data: pairsData, isLoading, isError } = useQuery({ queryKey: ['pairs'], queryFn: fetchPairs });

    if (isLoading) return <div className="p-8 text-center text-gray-400 flex items-center justify-center space-x-2"><RefreshCw className="h-4 w-4 animate-spin" /><span>Loading Scanner Data...</span></div>;
    if (isError) return <div className="p-8 text-center text-red-500">Error loading pairs. Is the backend running?</div>;

    if (!pairsData || pairsData.length === 0) {
        return (
            <div className="p-12 text-center flex flex-col items-center justify-center items-center h-full">
                <div className="text-gray-500 mb-2">No valid pairs found yet.</div>
                <div className="text-sm text-gray-600">The scanner might still be processing or waiting for enough data.</div>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-400">
                <thead className="text-xs uppercase bg-[#1f2937] text-gray-300">
                    <tr>
                        <th className="px-6 py-4 rounded-tl-lg">Pair</th>
                        <th className="px-6 py-4">Z-Score</th>
                        <th className="px-6 py-4">Correlation</th>
                        <th className="px-6 py-4">Half Life</th>
                        <th className="px-6 py-4">Zone</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4 rounded-tr-lg text-right">Last Scan</th>
                    </tr>
                </thead>
                <tbody>
                    {pairsData.map((pair: any, i: number) => {
                        return (
                            <tr key={`${pair.symbol_a}-${pair.symbol_b}-${i}`} className="border-b border-[#1f2937] hover:bg-[#2d3748]/30 transition-colors">
                                <td className="px-6 py-4 font-bold text-white whitespace-nowrap">
                                    {pair.symbol_a} <span className="text-gray-500 font-normal px-1">/</span> {pair.symbol_b}
                                </td>
                                <td className="px-6 py-4">
                                    <span className={cn(
                                        "font-mono px-2 py-1 rounded bg-[#0a0e17] border",
                                        Math.abs(pair.zscore) >= 2 ? "text-red-400 border-red-500/30" : "text-gray-300 border-gray-700"
                                    )}>
                                        {Number(pair.zscore).toFixed(3)}
                                    </span>
                                </td>
                                <td className="px-6 py-4">{(Number(pair.correlation) * 100).toFixed(1)}%</td>
                                <td className="px-6 py-4">{Number(pair.half_life).toFixed(1)}</td>
                                <td className="px-6 py-4">
                                    <span className={cn(
                                        "px-2 py-1 text-xs rounded-full border",
                                        pair.zone === 'safe' ? "border-green-500/30 text-green-400 bg-green-500/10" :
                                            pair.zone === 'caution' ? "border-yellow-500/30 text-yellow-400 bg-yellow-500/10" :
                                                pair.zone === 'danger' ? "border-red-500/30 text-red-500 bg-red-500/10" :
                                                    "border-gray-500/30 text-gray-400 bg-gray-500/10"
                                    )}>
                                        {pair.zone?.toUpperCase() || '-'}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    {pair.qualified ? (
                                        <span className="text-green-400 flex items-center gap-1">● READY</span>
                                    ) : (
                                        <span className="text-gray-500">-</span>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-right text-xs">
                                    {new Date(pair.scanned_at).toLocaleTimeString()}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
