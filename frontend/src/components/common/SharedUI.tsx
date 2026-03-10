import { cn } from '../../lib/api';

/**
 * ZScoreBar - A visual representation of the Z-Score
 */
export function ZScoreBar({ zscore }: { zscore: number }) {
    const absZ = Math.abs(zscore);
    const clampedZ = Math.min(absZ, 4); // Clamp at 4 for visual
    const pct = (clampedZ / 4) * 100;
    const isLong = zscore < 0;

    return (
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden flex ring-1 ring-slate-200">
            {isLong ? (
                <div className="flex-1 flex justify-end">
                    <div
                        className={cn(
                            "h-full rounded-l-full transition-all duration-1000",
                            absZ > 2 ? "bg-emerald-500" : "bg-slate-300"
                        )}
                        style={{ width: `${pct}%` }}
                    />
                </div>
            ) : (
                <div className="flex-1 flex justify-start">
                    <div
                        className={cn(
                            "h-full rounded-r-full transition-all duration-1000",
                            absZ > 2 ? "bg-rose-500" : "bg-slate-300"
                        )}
                        style={{ width: `${pct}%` }}
                    />
                </div>
            )}
        </div>
    );
}

/**
 * Sparkline - A simple line chart for price/zscore history
 */
export function Sparkline({ data, width = 100, height = 30 }: { data: number[], width?: number, height?: number }) {
    if (!data || data.length < 2) return null;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((d, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((d - min) / range) * height;
        return `${x},${y}`;
    }).join(' ');

    const lastVal = data[data.length - 1];
    const isUp = lastVal >= data[0];

    return (
        <svg width={width} height={height} className="overflow-visible">
            <polyline
                fill="none"
                stroke={isUp ? "#10b981" : "#ef4444"}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
                className="drop-shadow-sm"
            />
        </svg>
    );
}
