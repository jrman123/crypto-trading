import { buildFeatures, getFeatures } from '../lib/features.js';
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
      // Build features
      const { symbol, timestamp } = req.body;
      
      if (!symbol || !timestamp) {
        return res.status(400).json({ error: 'symbol and timestamp are required' });
      }
      
      const features = await buildFeatures(symbol, timestamp);
      return res.status(200).json({ ok: true, features });
      
    } else if (req.method === 'GET') {
      // Get features
      const { symbol, timestamp } = req.query;
      
      if (!symbol) {
        return res.status(400).json({ error: 'symbol is required' });
      }
      
      const features = await getFeatures(symbol, timestamp ? parseInt(timestamp) : undefined);
      return res.status(200).json({ ok: true, features });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Features endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
