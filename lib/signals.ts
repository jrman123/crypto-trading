import { query } from './database.js';
import { getFeatures, TechnicalFeatures } from './features.js';
import { log } from './log.js';

export type SignalType = 'BUY' | 'SELL' | 'HOLD';

export interface TradingSignal {
  id?: number;
  symbol: string;
  timestamp: number;
  signal_type: SignalType;
  strength: number; // 0-1
  confidence: number; // 0-1
  reasons: string[];
}

function analyzeFeatures(features: TechnicalFeatures): TradingSignal {
  const reasons: string[] = [];
  let buyScore = 0;
  let sellScore = 0;
  let totalWeight = 0;
  
  // RSI Analysis
  if (features.rsi !== undefined) {
    if (features.rsi < 30) {
      buyScore += 2;
      reasons.push('RSI oversold (<30)');
    } else if (features.rsi > 70) {
      sellScore += 2;
      reasons.push('RSI overbought (>70)');
    }
    totalWeight += 2;
  }
  
  // MACD Analysis
  if (features.macd !== undefined && features.macd_signal !== undefined) {
    if (features.macd > features.macd_signal) {
      buyScore += 1.5;
      reasons.push('MACD bullish crossover');
    } else if (features.macd < features.macd_signal) {
      sellScore += 1.5;
      reasons.push('MACD bearish crossover');
    }
    totalWeight += 1.5;
  }
  
  // EMA Analysis
  if (features.ema_12 !== undefined && features.ema_26 !== undefined) {
    if (features.ema_12 > features.ema_26) {
      buyScore += 1;
      reasons.push('EMA-12 above EMA-26 (bullish)');
    } else {
      sellScore += 1;
      reasons.push('EMA-12 below EMA-26 (bearish)');
    }
    totalWeight += 1;
  }
  
  // SMA Trend Analysis
  if (features.sma_50 !== undefined && features.sma_200 !== undefined) {
    if (features.sma_50 > features.sma_200) {
      buyScore += 1;
      reasons.push('SMA-50 above SMA-200 (golden cross)');
    } else {
      sellScore += 1;
      reasons.push('SMA-50 below SMA-200 (death cross)');
    }
    totalWeight += 1;
  }
  
  // Determine signal
  let signal_type: SignalType = 'HOLD';
  let strength = 0;
  
  const netScore = buyScore - sellScore;
  
  if (Math.abs(netScore) < 1) {
    signal_type = 'HOLD';
    strength = 0.3;
  } else if (netScore > 0) {
    signal_type = 'BUY';
    strength = Math.min(buyScore / totalWeight, 1);
  } else {
    signal_type = 'SELL';
    strength = Math.min(sellScore / totalWeight, 1);
  }
  
  // Confidence based on volatility
  let confidence = 0.7; // base confidence
  if (features.volatility !== undefined) {
    // Lower confidence in high volatility
    confidence = Math.max(0.3, 1 - features.volatility * 10);
  }
  
  return {
    symbol: features.symbol,
    timestamp: features.timestamp,
    signal_type,
    strength: Math.round(strength * 10000) / 10000,
    confidence: Math.round(confidence * 10000) / 10000,
    reasons
  };
}

export async function generateSignal(symbol: string, timestamp: number): Promise<TradingSignal> {
  const features = await getFeatures(symbol, timestamp);
  
  if (!features) {
    throw new Error(`No features found for ${symbol} at ${timestamp}`);
  }
  
  const signal = analyzeFeatures(features);
  
  // Store signal in database
  const sql = `
    INSERT INTO signals (symbol, timestamp, signal_type, strength, confidence, reasons)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id
  `;
  
  const result = await query<{ id: number }>(sql, [
    signal.symbol,
    signal.timestamp,
    signal.signal_type,
    signal.strength,
    signal.confidence,
    signal.reasons
  ]);
  
  signal.id = result.rows[0]?.id;
  
  log.info('Signal generated', { 
    symbol: signal.symbol, 
    type: signal.signal_type, 
    strength: signal.strength 
  });
  
  return signal;
}

export async function getLatestSignal(symbol: string): Promise<TradingSignal | null> {
  const sql = 'SELECT * FROM signals WHERE symbol = $1 ORDER BY timestamp DESC LIMIT 1';
  const result = await query<TradingSignal>(sql, [symbol]);
  return result.rows[0] || null;
}

export async function getSignals(
  symbol: string,
  startTime?: number,
  endTime?: number,
  limit: number = 50
): Promise<TradingSignal[]> {
  let sql = 'SELECT * FROM signals WHERE symbol = $1';
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
  
  const result = await query<TradingSignal>(sql, params);
  return result.rows;
}
