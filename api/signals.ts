import { generateSignal, getLatestSignal, getSignals } from '../lib/signals.js';
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
      // Generate signal
      const { symbol, timestamp } = req.body;
      
      if (!symbol || !timestamp) {
        return res.status(400).json({ error: 'symbol and timestamp are required' });
      }
      
      const signal = await generateSignal(symbol, timestamp);
      return res.status(200).json({ ok: true, signal });
      
    } else if (req.method === 'GET') {
      // Get signals
      const { symbol, latest, startTime, endTime, limit } = req.query;
      
      if (!symbol) {
        return res.status(400).json({ error: 'symbol is required' });
      }
      
      if (latest === 'true') {
        const signal = await getLatestSignal(symbol);
        return res.status(200).json({ ok: true, signal });
      }
      
      const signals = await getSignals(
        symbol,
        startTime ? parseInt(startTime) : undefined,
        endTime ? parseInt(endTime) : undefined,
        limit ? parseInt(limit) : 50
      );
      
      return res.status(200).json({ ok: true, signals });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Signals endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
