export interface Instrument {
    symbol: string;
    hasFutures: boolean;
    vol24h: number;
    lastPrice: number;
}

export interface PairSignal {
    symbolA: string;
    symbolB: string;
    correlation: number;
    beta: number;
    halfLife: number;
}

export interface ValidatedSignal extends PairSignal {
    legASide: 'buy' | 'sell';
    legBSide: 'buy' | 'sell';
    sizeA: number;
    sizeB: number;
    zscore: number;
    zone: string;
    validation: object;
}

export interface Check {
    name: string;
    pass: boolean;
    detail: string;
}

export interface PairResult {
    symbolA: string;
    symbolB: string;
    correlation: number;
    hurst: number;
    halfLife: number;
    hedgeRatio: number;
    zscore: number;
    zone: string;
    canOpen: boolean;
    sizePct: number;
    direction: { legA: string; legB: string };
    dedupChecks: any[];
    blocked: boolean;
    blockReason: string | null;
}

export interface ScanResult {
    skipped?: boolean;
    reason?: string;
    pairs?: PairResult[];
    signals?: PairResult[];
    blocked?: PairResult[];
    duration?: number;
    total?: number;
}
