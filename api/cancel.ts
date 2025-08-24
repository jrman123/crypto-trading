import { cancelOrder } from '../lib/binance.js';

export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });

  const { symbol, orderId, clientId } = req.body || {};
  if (!symbol || (!orderId && !clientId)) {
    return res.status(400).json({ error: 'symbol and (orderId or clientId) required' });
  }
  try {
    const data = await cancelOrder(symbol, orderId, clientId);
    return res.status(200).json(data);
  } catch (e: any) {
    return res.status(500).json({ error: e.message || 'Unknown error', code: e.code, status: e.status });
  }
}
