import { ingestMarketData, getMarketData, MarketDataPoint } from '../lib/marketData.js';
import { log } from '../lib/log.js';

function cors(res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

export default async function handler(req: any, res: any) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  
  try {
    if (req.method === 'POST') {
      // Ingest market data
      const data: MarketDataPoint = req.body;
      
      if (!data.symbol || !data.timestamp || data.close === undefined) {
        return res.status(400).json({ error: 'symbol, timestamp, and close are required' });
      }
      
      await ingestMarketData(data);
      return res.status(200).json({ ok: true, message: 'Market data ingested' });
      
    } else if (req.method === 'GET') {
      // Get market data
      const { symbol, startTime, endTime, limit } = req.query;
      
      if (!symbol) {
        return res.status(400).json({ error: 'symbol is required' });
      }
      
      const data = await getMarketData(
        symbol,
        startTime ? parseInt(startTime) : undefined,
        endTime ? parseInt(endTime) : undefined,
        limit ? parseInt(limit) : 100
      );
      
      return res.status(200).json({ ok: true, data });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Market data endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
