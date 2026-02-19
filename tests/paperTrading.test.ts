import { executePaperTrade, calculatePortfolio } from '../lib/paperTrading';

// Mock dependencies
jest.mock('../lib/database', () => ({
  query: jest.fn()
}));

jest.mock('../lib/marketData', () => ({
  getLatestMarketData: jest.fn()
}));

import { query } from '../lib/database';
import { getLatestMarketData } from '../lib/marketData';

describe('Paper Trading', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('executePaperTrade', () => {
    it('should execute BUY paper trade', async () => {
      const signal = {
        id: 1,
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        signal_type: 'BUY' as const,
        strength: 0.75,
        confidence: 0.8,
        reasons: ['RSI oversold']
      };

      const mockMarketData = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        close: 50000,
        open: 50000,
        high: 50000,
        low: 50000,
        volume: 1000
      };

      (getLatestMarketData as jest.Mock).mockResolvedValue(mockMarketData);
      (query as jest.Mock).mockResolvedValue({ rows: [{ id: 1 }] });

      const trade = await executePaperTrade(signal, 100);

      expect(trade.symbol).toBe('BTCUSDT');
      expect(trade.side).toBe('BUY');
      expect(trade.price).toBe(50000);
      expect(trade.quantity).toBe(100 / 50000);
      expect(trade.status).toBe('EXECUTED');
    });

    it('should execute SELL paper trade', async () => {
      const signal = {
        id: 1,
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        signal_type: 'SELL' as const,
        strength: 0.75,
        confidence: 0.8,
        reasons: ['RSI overbought']
      };

      const mockMarketData = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        close: 50000,
        open: 50000,
        high: 50000,
        low: 50000,
        volume: 1000
      };

      (getLatestMarketData as jest.Mock).mockResolvedValue(mockMarketData);
      (query as jest.Mock).mockResolvedValue({ rows: [{ id: 1 }] });

      const trade = await executePaperTrade(signal, 100);

      expect(trade.side).toBe('SELL');
    });

    it('should throw error if no market data available', async () => {
      const signal = {
        id: 1,
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        signal_type: 'BUY' as const,
        strength: 0.75,
        confidence: 0.8,
        reasons: []
      };

      (getLatestMarketData as jest.Mock).mockResolvedValue(null);

      await expect(executePaperTrade(signal, 100))
        .rejects
        .toThrow('No market data available');
    });
  });

  describe('calculatePortfolio', () => {
    it('should calculate portfolio with positions', async () => {
      const mockPositions = [
        { symbol: 'BTCUSDT', net_quantity: 0.5, net_value: 25000 }
      ];

      const mockMarketData = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        close: 52000,
        open: 50000,
        high: 52000,
        low: 50000,
        volume: 1000
      };

      (query as jest.Mock).mockResolvedValue({ rows: mockPositions });
      (getLatestMarketData as jest.Mock).mockResolvedValue(mockMarketData);

      const portfolio = await calculatePortfolio();

      expect(portfolio.positions).toHaveProperty('BTCUSDT');
      expect(portfolio.positions.BTCUSDT.quantity).toBe(0.5);
      expect(portfolio.totalValue).toBeGreaterThan(0);
    });

    it('should return empty portfolio if no positions', async () => {
      (query as jest.Mock).mockResolvedValue({ rows: [] });

      const portfolio = await calculatePortfolio();

      expect(Object.keys(portfolio.positions)).toHaveLength(0);
      expect(portfolio.totalValue).toBe(0);
      expect(portfolio.totalPnL).toBe(0);
    });
  });
});
