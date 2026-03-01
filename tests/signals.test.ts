import { generateSignal, getLatestSignal } from '../lib/signals';

// Mock dependencies
jest.mock('../lib/database', () => ({
  query: jest.fn()
}));

jest.mock('../lib/features', () => ({
  getFeatures: jest.fn()
}));

import { query } from '../lib/database';
import { getFeatures } from '../lib/features';

describe('Signals', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('generateSignal', () => {
    it('should generate BUY signal for oversold RSI', async () => {
      const mockFeatures = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        rsi: 25, // oversold
        macd: 100,
        macd_signal: 50,
        ema_12: 51000,
        ema_26: 50000,
        sma_50: 50500,
        sma_200: 49000,
        volatility: 0.02
      };

      (getFeatures as jest.Mock).mockResolvedValue(mockFeatures);
      (query as jest.Mock).mockResolvedValue({ rows: [{ id: 1 }] });

      const signal = await generateSignal('BTCUSDT', 1708300800000);

      expect(signal.signal_type).toBe('BUY');
      expect(signal.strength).toBeGreaterThan(0);
      expect(signal.confidence).toBeGreaterThan(0);
      expect(signal.reasons).toContain('RSI oversold (<30)');
    });

    it('should generate SELL signal for overbought RSI', async () => {
      const mockFeatures = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        rsi: 75, // overbought
        macd: 50,
        macd_signal: 100,
        ema_12: 49000,
        ema_26: 50000,
        sma_50: 49500,
        sma_200: 51000,
        volatility: 0.02
      };

      (getFeatures as jest.Mock).mockResolvedValue(mockFeatures);
      (query as jest.Mock).mockResolvedValue({ rows: [{ id: 1 }] });

      const signal = await generateSignal('BTCUSDT', 1708300800000);

      expect(signal.signal_type).toBe('SELL');
      expect(signal.reasons).toContain('RSI overbought (>70)');
    });

    it('should generate HOLD signal for neutral conditions', async () => {
      const mockFeatures = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        rsi: 50, // neutral
        macd: 100,
        macd_signal: 99,
        ema_12: 50000,
        ema_26: 50100,
        sma_50: 50000,
        sma_200: 50050,
        volatility: 0.01
      };

      (getFeatures as jest.Mock).mockResolvedValue(mockFeatures);
      (query as jest.Mock).mockResolvedValue({ rows: [{ id: 1 }] });

      const signal = await generateSignal('BTCUSDT', 1708300800000);

      expect(signal.signal_type).toBe('HOLD');
    });

    it('should throw error if no features found', async () => {
      (getFeatures as jest.Mock).mockResolvedValue(null);

      await expect(generateSignal('BTCUSDT', 1708300800000))
        .rejects
        .toThrow('No features found');
    });
  });

  describe('getLatestSignal', () => {
    it('should get latest signal', async () => {
      const mockSignal = {
        symbol: 'BTCUSDT',
        signal_type: 'BUY',
        strength: 0.75
      };
      (query as jest.Mock).mockResolvedValue({ rows: [mockSignal] });

      const result = await getLatestSignal('BTCUSDT');

      expect(result).toEqual(mockSignal);
    });
  });
});
