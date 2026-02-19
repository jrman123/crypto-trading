import { query } from './database.js';
import { log } from './log.js';

export type Sentiment = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';

export interface WebIntelligence {
  id?: number;
  source: string;
  title: string;
  content?: string;
  url?: string;
  symbols: string[];
  sentiment?: Sentiment;
  sentiment_score?: number;
  published_at?: number;
}

// Simple sentiment analysis based on keywords
function analyzeSentiment(text: string): { sentiment: Sentiment; score: number } {
  const lowerText = text.toLowerCase();
  
  const positiveWords = [
    'bullish', 'surge', 'rally', 'gain', 'up', 'high', 'growth', 'positive',
    'profit', 'buy', 'strong', 'breakout', 'moon', 'pump', 'rocket'
  ];
  
  const negativeWords = [
    'bearish', 'crash', 'drop', 'fall', 'down', 'low', 'loss', 'negative',
    'sell', 'weak', 'breakdown', 'dump', 'plunge', 'decline'
  ];
  
  let positiveCount = 0;
  let negativeCount = 0;
  
  for (const word of positiveWords) {
    if (lowerText.includes(word)) positiveCount++;
  }
  
  for (const word of negativeWords) {
    if (lowerText.includes(word)) negativeCount++;
  }
  
  const total = positiveCount + negativeCount;
  if (total === 0) {
    return { sentiment: 'NEUTRAL', score: 0.5 };
  }
  
  const score = positiveCount / total;
  
  let sentiment: Sentiment;
  if (score > 0.6) {
    sentiment = 'POSITIVE';
  } else if (score < 0.4) {
    sentiment = 'NEGATIVE';
  } else {
    sentiment = 'NEUTRAL';
  }
  
  return { sentiment, score };
}

// Extract symbols from text
function extractSymbols(text: string, allowedSymbols: string[]): string[] {
  const symbols: string[] = [];
  const lowerText = text.toLowerCase();
  
  for (const symbol of allowedSymbols) {
    const base = symbol.replace('USDT', '').toLowerCase();
    if (lowerText.includes(base) || lowerText.includes(symbol.toLowerCase())) {
      symbols.push(symbol);
    }
  }
  
  return [...new Set(symbols)];
}

export async function ingestWebIntelligence(data: {
  source: string;
  title: string;
  content?: string;
  url?: string;
  published_at?: number;
}): Promise<WebIntelligence> {
  // Get allowed symbols
  const allowedSymbols = (process.env.ALLOWED_SYMBOLS || 'BTCUSDT,ETHUSDT')
    .split(',')
    .map(s => s.trim().toUpperCase())
    .filter(Boolean);
  
  // Extract symbols from title and content
  const textToAnalyze = `${data.title} ${data.content || ''}`;
  const symbols = extractSymbols(textToAnalyze, allowedSymbols);
  
  // Analyze sentiment
  const { sentiment, score } = analyzeSentiment(textToAnalyze);
  
  const intelligence: WebIntelligence = {
    source: data.source,
    title: data.title,
    content: data.content,
    url: data.url,
    symbols,
    sentiment,
    sentiment_score: Math.round(score * 10000) / 10000,
    published_at: data.published_at || Date.now()
  };
  
  // Store in database
  const sql = `
    INSERT INTO web_intelligence (source, title, content, url, symbols, sentiment, sentiment_score, published_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING id
  `;
  
  const result = await query<{ id: number }>(sql, [
    intelligence.source,
    intelligence.title,
    intelligence.content,
    intelligence.url,
    intelligence.symbols,
    intelligence.sentiment,
    intelligence.sentiment_score,
    intelligence.published_at
  ]);
  
  intelligence.id = result.rows[0]?.id;
  
  log.info('Web intelligence ingested', { 
    source: intelligence.source, 
    symbols: intelligence.symbols,
    sentiment: intelligence.sentiment
  });
  
  return intelligence;
}

export async function getWebIntelligence(
  symbol?: string,
  limit: number = 50
): Promise<WebIntelligence[]> {
  let sql = 'SELECT * FROM web_intelligence';
  const params: any[] = [];
  
  if (symbol) {
    sql += ' WHERE $1 = ANY(symbols)';
    params.push(symbol);
  }
  
  sql += ` ORDER BY published_at DESC LIMIT $${params.length + 1}`;
  params.push(limit);
  
  const result = await query<WebIntelligence>(sql, params);
  return result.rows;
}

export async function getRecentSentiment(symbol: string, hours: number = 24): Promise<{
  averageSentiment: number;
  positiveCount: number;
  negativeCount: number;
  neutralCount: number;
}> {
  const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
  
  const sql = `
    SELECT sentiment, COUNT(*) as count, AVG(sentiment_score) as avg_score
    FROM web_intelligence
    WHERE $1 = ANY(symbols) AND published_at >= $2
    GROUP BY sentiment
  `;
  
  const result = await query<{
    sentiment: Sentiment;
    count: number;
    avg_score: number;
  }>(sql, [symbol, cutoffTime]);
  
  let positiveCount = 0;
  let negativeCount = 0;
  let neutralCount = 0;
  let totalScore = 0;
  let totalItems = 0;
  
  for (const row of result.rows) {
    const count = parseInt(String(row.count));
    const avgScore = parseFloat(String(row.avg_score));
    
    if (row.sentiment === 'POSITIVE') positiveCount = count;
    else if (row.sentiment === 'NEGATIVE') negativeCount = count;
    else neutralCount = count;
    
    totalScore += avgScore * count;
    totalItems += count;
  }
  
  const averageSentiment = totalItems > 0 ? totalScore / totalItems : 0.5;
  
  return {
    averageSentiment: Math.round(averageSentiment * 10000) / 10000,
    positiveCount,
    negativeCount,
    neutralCount
  };
}
