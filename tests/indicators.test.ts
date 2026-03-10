import { describe, it, expect } from 'vitest';
import * as ind from '../src/core/indicators';

describe('Indicators', () => {
    it('correlation handles divide by zero', () => {
        expect(ind.correlation([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])).toBeNull();
    });

    it('hedgeRatio handles variance = 0', () => {
        expect(ind.hedgeRatio([1, 2, 3], [1, 1, 1])).toBeNull();
    });

    it('zScore handles sd = 0', () => {
        expect(ind.zScore(10, 5, 0)).toBeNull();
    });

    it('spread handles invalid beta and zero price', () => {
        expect(ind.spread(100, 50, Infinity)).toBeNull();
        expect(ind.spread(100, 0, 1.5)).toBeNull();
        expect(ind.spread(100, 50, 1.5)).toBe(25);
    });
});
