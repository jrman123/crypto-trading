import { ingestMarketData, getMarketData, getLatestMarketData } from '../lib/marketData';

// Mock database
jest.mock('../lib/database', () => ({
  query: jest.fn()
}));

import { query } from '../lib/database';

describe('Market Data', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('ingestMarketData', () => {
    it('should ingest market data successfully', async () => {
      (query as jest.Mock).mockResolvedValue({ rows: [] });

      const data = {
        symbol: 'BTCUSDT',
        timestamp: 1708300800000,
        open: 50000,
        high: 51000,
        low: 49500,
        close: 50500,
        volume: 1000
      };

      await ingestMarketData(data);

      expect(query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO market_data'),
        [data.symbol, data.timestamp, data.open, data.high, data.low, data.close, data.volume]
      );
    });
  });

  describe('getMarketData', () => {
    it('should get market data for symbol', async () => {
      const mockData = [
        { symbol: 'BTCUSDT', timestamp: 1708300800000, close: 50500 }
      ];
      (query as jest.Mock).mockResolvedValue({ rows: mockData });

      const result = await getMarketData('BTCUSDT', undefined, undefined, 100);

      expect(result).toEqual(mockData);
      expect(query).toHaveBeenCalledWith(
        expect.stringContaining('SELECT * FROM market_data'),
        ['BTCUSDT', 100]
      );
    });

    it('should filter by time range', async () => {
      (query as jest.Mock).mockResolvedValue({ rows: [] });

      await getMarketData('BTCUSDT', 1708300000000, 1708400000000, 50);

      expect(query).toHaveBeenCalledWith(
        expect.stringContaining('timestamp >='),
        ['BTCUSDT', 1708300000000, 1708400000000, 50]
      );
    });
  });

  describe('getLatestMarketData', () => {
    it('should get latest market data', async () => {
      const mockData = { symbol: 'BTCUSDT', timestamp: 1708300800000, close: 50500 };
      (query as jest.Mock).mockResolvedValue({ rows: [mockData] });

      const result = await getLatestMarketData('BTCUSDT');

      expect(result).toEqual(mockData);
    });

    it('should return null if no data exists', async () => {
      (query as jest.Mock).mockResolvedValue({ rows: [] });

      const result = await getLatestMarketData('BTCUSDT');

      expect(result).toBeNull();
    });
  });
});
