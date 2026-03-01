import { query } from './database.js';
import { log } from './log.js';

export interface MarketDataPoint {
  symbol: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export async function ingestMarketData(data: MarketDataPoint): Promise<void> {
  const sql = `
    INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, timestamp) DO UPDATE SET
      open = EXCLUDED.open,
      high = EXCLUDED.high,
      low = EXCLUDED.low,
      close = EXCLUDED.close,
      volume = EXCLUDED.volume
  `;

  await query(sql, [
    data.symbol,
    data.timestamp,
    data.open,
    data.high,
    data.low,
    data.close,
    data.volume
  ]);

  log.info('Market data ingested', { symbol: data.symbol, timestamp: data.timestamp });
}

export async function getMarketData(
  symbol: string,
  startTime?: number,
  endTime?: number,
  limit: number = 100
): Promise<MarketDataPoint[]> {
  let sql = 'SELECT * FROM market_data WHERE symbol = $1';
  const params: any[] = [symbol];

  if (startTime) {
    params.push(startTime);
    sql += ` AND timestamp >= $${params.length}`;
  }

  if (endTime) {
    params.push(endTime);
    sql += ` AND timestamp <= $${params.length}`;
  }

  sql += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
  params.push(limit);

  const result = await query<MarketDataPoint>(sql, params);
  return result.rows;
}

export async function getLatestMarketData(symbol: string): Promise<MarketDataPoint | null> {
  const sql = 'SELECT * FROM market_data WHERE symbol = $1 ORDER BY timestamp DESC LIMIT 1';
  const result = await query<MarketDataPoint>(sql, [symbol]);
  return result.rows[0] || null;
}
