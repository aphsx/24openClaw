export function classifyZone(zscore: number, config: {
    zscore_entry: number; zscore_sl: number; safe_buffer: number;
}): { zone: 'safe' | 'caution' | 'danger' | 'none'; canOpen: boolean; sizePct: number } {
    const absZ = Math.abs(zscore);
    const safeMax = config.zscore_sl - config.safe_buffer;

    if (absZ < config.zscore_entry) return { zone: 'none', canOpen: false, sizePct: 0 };
    if (absZ > safeMax) return { zone: 'danger', canOpen: false, sizePct: 0 };
    if (absZ > safeMax - 0.2) return { zone: 'caution', canOpen: true, sizePct: 50 };
    return { zone: 'safe', canOpen: true, sizePct: 100 };
}
