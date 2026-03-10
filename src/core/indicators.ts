export function correlation(a: number[], b: number[]): number | null {
    if (a.length !== b.length || a.length < 10) return null;
    const mA = mean(a), mB = mean(b);
    const sA = stddev(a), sB = stddev(b);
    if (sA === 0 || sB === 0) return null;
    const cov = a.reduce((s, v, i) => s + (v - mA) * (b[i] - mB), 0) / a.length;
    const r = cov / (sA * sB);
    return isFinite(r) ? Math.max(-1, Math.min(1, r)) : null;
}

export function hedgeRatio(a: number[], b: number[]): number | null {
    const vB = variance(b);
    if (vB === 0) return null;
    const cov = covariance(a, b);
    const beta = cov / vB;
    return isFinite(beta) && !isNaN(beta) && beta > 0 ? beta : null;
}

export function spread(priceA: number, priceB: number, beta: number): number | null {
    if (!isFinite(beta) || priceB <= 0) return null;
    return priceA - beta * priceB;
}

export function zScore(currentSpread: number, meanSpread: number, sdSpread: number): number | null {
    if (sdSpread === 0 || !isFinite(sdSpread)) return null;
    const z = (currentSpread - meanSpread) / sdSpread;
    return isFinite(z) ? z : null;
}

export function halfLife(spreads: number[]): number | null {
    if (spreads.length < 20) return null;
    const lag = spreads.slice(0, -1);
    const delta = spreads.slice(1).map((s, i) => s - lag[i]);
    const mLag = mean(lag);
    const devLag = lag.map(l => l - mLag);
    const vLag = variance(devLag);
    if (vLag === 0) return null;
    const lambda = covariance(delta, devLag) / vLag;
    if (lambda >= 0) return null; // ไม่ mean-revert
    const hl = -Math.log(2) / lambda;
    return isFinite(hl) && hl > 0 ? hl : null;
}

export function hurstExponent(series: number[]): number | null {
    if (series.length < 20) return null;
    const n = series.length;
    const m = mean(series);
    const dev = series.map(x => x - m);
    let cumSum = 0;
    const cumDev = dev.map(d => (cumSum += d, cumSum));
    const R = Math.max(...cumDev) - Math.min(...cumDev);
    const S = stddev(series);
    if (S === 0 || R === 0) return null;
    const H = Math.log(R / S) / Math.log(n);
    return isFinite(H) ? H : null;
}

// Helpers
export function mean(arr: number[]): number { return arr.reduce((a, b) => a + b, 0) / arr.length; }
export function variance(arr: number[]): number {
    if (arr.length === 0) return 0;
    const m = mean(arr);
    return arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length;
}
export function stddev(arr: number[]): number { return Math.sqrt(variance(arr)); }
export function covariance(a: number[], b: number[]): number {
    if (a.length === 0 || a.length !== b.length) return 0;
    const mA = mean(a), mB = mean(b);
    return a.reduce((s, v, i) => s + (v - mA) * (b[i] - mB), 0) / a.length;
}
