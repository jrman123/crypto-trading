import { query } from './database.js';
import { TradingSignal } from './signals.js';
import { getLatestMarketData } from './marketData.js';
import { log } from './log.js';

export interface PaperTrade {
  id?: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  total_value: number;
  signal_id?: number;
  timestamp: number;
  status: 'EXECUTED' | 'CANCELLED' | 'FAILED';
}

export async function executePaperTrade(
  signal: TradingSignal,
  usdAmount: number = 100
): Promise<PaperTrade> {
  // Get current market price
  const marketData = await getLatestMarketData(signal.symbol);
  
  if (!marketData) {
    throw new Error(`No market data available for ${signal.symbol}`);
  }
  
  const price = marketData.close;
  const side = signal.signal_type === 'BUY' ? 'BUY' : 'SELL';
  
  // Calculate quantity based on USD amount
  const quantity = usdAmount / price;
  const total_value = quantity * price;
  
  const trade: PaperTrade = {
    symbol: signal.symbol,
    side,
    quantity,
    price,
    total_value,
    signal_id: signal.id,
    timestamp: Date.now(),
    status: 'EXECUTED'
  };
  
  // Store trade in database
  const sql = `
    INSERT INTO paper_trades (symbol, side, quantity, price, total_value, signal_id, timestamp, status)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING id
  `;
  
  const result = await query<{ id: number }>(sql, [
    trade.symbol,
    trade.side,
    trade.quantity,
    trade.price,
    trade.total_value,
    trade.signal_id,
    trade.timestamp,
    trade.status
  ]);
  
  trade.id = result.rows[0]?.id;
  
  log.info('Paper trade executed', { 
    symbol: trade.symbol, 
    side: trade.side, 
    quantity: trade.quantity,
    price: trade.price 
  });
  
  return trade;
}

export async function getPaperTrades(
  symbol?: string,
  limit: number = 100
): Promise<PaperTrade[]> {
  let sql = 'SELECT * FROM paper_trades';
  const params: any[] = [];
  
  if (symbol) {
    sql += ' WHERE symbol = $1';
    params.push(symbol);
  }
  
  sql += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
  params.push(limit);
  
  const result = await query<PaperTrade>(sql, params);
  return result.rows;
}

export async function calculatePortfolio(): Promise<{
  positions: { [symbol: string]: { quantity: number; avgPrice: number } };
  totalValue: number;
  totalPnL: number;
}> {
  const sql = `
    SELECT 
      symbol,
      SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) as net_quantity,
      SUM(CASE WHEN side = 'BUY' THEN total_value ELSE -total_value END) as net_value
    FROM paper_trades
    WHERE status = 'EXECUTED'
    GROUP BY symbol
    HAVING SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) != 0
  `;
  
  const result = await query<{
    symbol: string;
    net_quantity: number;
    net_value: number;
  }>(sql);
  
  const positions: { [symbol: string]: { quantity: number; avgPrice: number } } = {};
  let totalValue = 0;
  let totalCost = 0;
  
  for (const row of result.rows) {
    const quantity = parseFloat(String(row.net_quantity));
    const netValue = parseFloat(String(row.net_value));
    const avgPrice = Math.abs(netValue / quantity);
    
    positions[row.symbol] = {
      quantity,
      avgPrice
    };
    
    // Get current market price to calculate current value
    const marketData = await getLatestMarketData(row.symbol);
    if (marketData) {
      const currentValue = quantity * marketData.close;
      totalValue += currentValue;
      totalCost += netValue;
    }
  }
  
  const totalPnL = totalValue - totalCost;
  
  return { positions, totalValue, totalPnL };
}
