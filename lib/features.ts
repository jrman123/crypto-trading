import { query } from './database.js';
import { getMarketData, MarketDataPoint } from './marketData.js';
import { log } from './log.js';

export interface TechnicalFeatures {
  symbol: string;
  timestamp: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  ema_12?: number;
  ema_26?: number;
  sma_50?: number;
  sma_200?: number;
  volatility?: number;
}

// Calculate Simple Moving Average
function calculateSMA(prices: number[], period: number): number {
  if (prices.length < period) return prices[prices.length - 1];
  const slice = prices.slice(0, period);
  return slice.reduce((sum, p) => sum + p, 0) / period;
}

// Calculate Exponential Moving Average
function calculateEMA(prices: number[], period: number, prevEMA?: number): number {
  if (prices.length === 0) return 0;
  const multiplier = 2 / (period + 1);
  const currentPrice = prices[0];
  
  if (!prevEMA) {
    return calculateSMA(prices, Math.min(period, prices.length));
  }
  
  return (currentPrice - prevEMA) * multiplier + prevEMA;
}

// Calculate RSI
function calculateRSI(prices: number[], period: number = 14): number {
  if (prices.length < period + 1) return 50; // neutral
  
  const changes = [];
  for (let i = 0; i < period; i++) {
    changes.push(prices[i] - prices[i + 1]);
  }
  
  const gains = changes.filter(c => c > 0).reduce((sum, c) => sum + c, 0) / period;
  const losses = Math.abs(changes.filter(c => c < 0).reduce((sum, c) => sum + c, 0)) / period;
  
  if (losses === 0) return 100;
  const rs = gains / losses;
  return 100 - (100 / (1 + rs));
}

// Calculate MACD
// NOTE: This uses a simplified approximation for the signal line.
// Standard MACD signal is a 9-period EMA of MACD values, but we approximate it
// with 0.9 multiplier for simplicity in this initial implementation.
// For production use, consider implementing proper 9-period EMA calculation
// by maintaining historical MACD values.
function calculateMACD(prices: number[]): { macd: number; signal: number } {
  const ema12 = calculateEMA(prices, 12);
  const ema26 = calculateEMA(prices, 26);
  const macd = ema12 - ema26;
  
  // Simplified signal line approximation
  const signal = macd * 0.9;
  
  return { macd, signal };
}

// Calculate volatility (standard deviation of returns)
function calculateVolatility(prices: number[], period: number = 20): number {
  if (prices.length < period) return 0;
  
  const returns = [];
  for (let i = 0; i < period - 1; i++) {
    if (prices[i + 1] !== 0) {
      returns.push((prices[i] - prices[i + 1]) / prices[i + 1]);
    }
  }
  
  const mean = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / returns.length;
  return Math.sqrt(variance);
}

export async function buildFeatures(symbol: string, timestamp: number): Promise<TechnicalFeatures> {
  // Get historical data (last 200 candles for SMA-200)
  const historicalData = await getMarketData(symbol, undefined, timestamp, 200);
  
  if (historicalData.length === 0) {
    throw new Error(`No market data found for ${symbol}`);
  }
  
  // Extract close prices (most recent first)
  const closePrices = historicalData.map(d => d.close);
  
  // Calculate all indicators
  const rsi = calculateRSI(closePrices, 14);
  const { macd, signal } = calculateMACD(closePrices);
  const ema_12 = calculateEMA(closePrices, 12);
  const ema_26 = calculateEMA(closePrices, 26);
  const sma_50 = calculateSMA(closePrices, 50);
  const sma_200 = calculateSMA(closePrices, 200);
  const volatility = calculateVolatility(closePrices, 20);
  
  const features: TechnicalFeatures = {
    symbol,
    timestamp,
    rsi,
    macd,
    macd_signal: signal,
    ema_12,
    ema_26,
    sma_50,
    sma_200,
    volatility
  };
  
  // Store features in database
  const sql = `
    INSERT INTO features (symbol, timestamp, rsi, macd, macd_signal, ema_12, ema_26, sma_50, sma_200, volatility)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    ON CONFLICT (symbol, timestamp) DO UPDATE SET
      rsi = EXCLUDED.rsi,
      macd = EXCLUDED.macd,
      macd_signal = EXCLUDED.macd_signal,
      ema_12 = EXCLUDED.ema_12,
      ema_26 = EXCLUDED.ema_26,
      sma_50 = EXCLUDED.sma_50,
      sma_200 = EXCLUDED.sma_200,
      volatility = EXCLUDED.volatility
  `;
  
  await query(sql, [
    features.symbol,
    features.timestamp,
    features.rsi,
    features.macd,
    features.macd_signal,
    features.ema_12,
    features.ema_26,
    features.sma_50,
    features.sma_200,
    features.volatility
  ]);
  
  log.info('Features built', { symbol, timestamp });
  return features;
}

export async function getFeatures(symbol: string, timestamp?: number): Promise<TechnicalFeatures | null> {
  let sql = 'SELECT * FROM features WHERE symbol = $1';
  const params: any[] = [symbol];
  
  if (timestamp) {
    sql += ' AND timestamp = $2';
    params.push(timestamp);
  }
  
  sql += ' ORDER BY timestamp DESC LIMIT 1';
  
  const result = await query<TechnicalFeatures>(sql, params);
  return result.rows[0] || null;
}
