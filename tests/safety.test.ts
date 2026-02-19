import { getSafetyFlag, setSafetyFlag, checkSafety, pauseTrading, resumeTrading, isSystemHealthy } from '../lib/safety';

// Mock database
jest.mock('../lib/database', () => ({
  query: jest.fn()
}));

import { query } from '../lib/database';

describe('Safety', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getSafetyFlag', () => {
    it('should get safety flag', async () => {
      const mockFlag = {
        flag_name: 'TRADING_ENABLED',
        is_paused: false,
        reason: 'Normal operation'
      };
      (query as jest.Mock).mockResolvedValue({ rows: [mockFlag] });

      const result = await getSafetyFlag('TRADING_ENABLED');

      expect(result).toEqual(mockFlag);
    });
  });

  describe('setSafetyFlag', () => {
    it('should set safety flag to paused', async () => {
      const mockFlag = {
        flag_name: 'TRADING_ENABLED',
        is_paused: true,
        reason: 'High volatility'
      };
      (query as jest.Mock).mockResolvedValue({ rows: [mockFlag] });

      const result = await setSafetyFlag('TRADING_ENABLED', true, 'High volatility', 'admin');

      expect(result.is_paused).toBe(true);
      expect(query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO safety_flags'),
        expect.arrayContaining(['TRADING_ENABLED', true, 'High volatility'])
      );
    });
  });

  describe('checkSafety', () => {
    it('should return true if flag is not paused', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [{ flag_name: 'TRADING_ENABLED', is_paused: false }] 
      });

      const result = await checkSafety('TRADING_ENABLED');

      expect(result).toBe(true);
    });

    it('should return false if flag is paused', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [{ flag_name: 'TRADING_ENABLED', is_paused: true }] 
      });

      const result = await checkSafety('TRADING_ENABLED');

      expect(result).toBe(false);
    });

    it('should return false if flag not found', async () => {
      (query as jest.Mock).mockResolvedValue({ rows: [] });

      const result = await checkSafety('UNKNOWN_FLAG');

      expect(result).toBe(false);
    });
  });

  describe('pauseTrading', () => {
    it('should pause trading', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [{ flag_name: 'TRADING_ENABLED', is_paused: true }] 
      });

      await pauseTrading('Emergency stop', 'admin');

      expect(query).toHaveBeenCalledWith(
        expect.any(String),
        expect.arrayContaining(['TRADING_ENABLED', true, 'Emergency stop', expect.any(Date), 'admin'])
      );
    });
  });

  describe('resumeTrading', () => {
    it('should resume trading', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [{ flag_name: 'TRADING_ENABLED', is_paused: false }] 
      });

      await resumeTrading('admin');

      expect(query).toHaveBeenCalledWith(
        expect.any(String),
        expect.arrayContaining(['TRADING_ENABLED', false, 'Trading resumed'])
      );
    });
  });

  describe('isSystemHealthy', () => {
    it('should return healthy status when no flags paused', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [
          { flag_name: 'TRADING_ENABLED', is_paused: false },
          { flag_name: 'DATA_INGESTION_ENABLED', is_paused: false }
        ] 
      });

      const result = await isSystemHealthy();

      expect(result.healthy).toBe(true);
      expect(result.issues).toHaveLength(0);
    });

    it('should return unhealthy status when flags paused', async () => {
      (query as jest.Mock).mockResolvedValue({ 
        rows: [
          { flag_name: 'TRADING_ENABLED', is_paused: true, reason: 'High volatility' },
          { flag_name: 'DATA_INGESTION_ENABLED', is_paused: false }
        ] 
      });

      const result = await isSystemHealthy();

      expect(result.healthy).toBe(false);
      expect(result.issues).toHaveLength(1);
      expect(result.issues[0]).toContain('High volatility');
    });
  });
});
