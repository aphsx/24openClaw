import { describe, it, expect } from 'vitest';
import { classifyZone } from '../src/core/safe-zone';

describe('Safe Zone', () => {
    const config = { zscore_entry: 2.0, zscore_sl: 3.0, safe_buffer: 0.5 }; // safeMax = 2.5

    it('classifies none zone', () => {
        expect(classifyZone(1.9, config).zone).toBe('none');
    });

    it('classifies safe zone', () => {
        expect(classifyZone(2.2, config).zone).toBe('safe');
    });

    it('classifies caution zone', () => {
        expect(classifyZone(2.4, config).zone).toBe('caution');
    });

    it('classifies danger zone', () => {
        expect(classifyZone(2.6, config).zone).toBe('danger');
    });
});
