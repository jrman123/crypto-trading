import { ingestWebIntelligence, getWebIntelligence, getRecentSentiment } from '../lib/webIntelligence.js';
import { checkSafety } from '../lib/safety.js';
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
      // Ingest web intelligence
      const isSafe = await checkSafety('WEB_INTELLIGENCE_ENABLED');
      if (!isSafe) {
        return res.status(403).json({ error: 'Web intelligence ingestion is currently paused' });
      }
      
      const { source, title, content, url, published_at } = req.body;
      
      if (!source || !title) {
        return res.status(400).json({ error: 'source and title are required' });
      }
      
      const intelligence = await ingestWebIntelligence({
        source,
        title,
        content,
        url,
        published_at
      });
      
      return res.status(200).json({ ok: true, intelligence });
      
    } else if (req.method === 'GET') {
      // Get web intelligence or sentiment
      const { symbol, sentiment, hours, limit } = req.query;
      
      if (sentiment === 'true' && symbol) {
        const sentimentData = await getRecentSentiment(symbol, hours ? parseInt(hours) : 24);
        return res.status(200).json({ ok: true, sentiment: sentimentData });
      }
      
      const intelligence = await getWebIntelligence(symbol, limit ? parseInt(limit) : 50);
      return res.status(200).json({ ok: true, intelligence });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Web intelligence endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
