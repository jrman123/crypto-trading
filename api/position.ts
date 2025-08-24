import { signedRequest } from '../lib/binance.js';

export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const symbol = (req.query?.symbol || req.body?.symbol || '').toString().toUpperCase();
  try {
    const open = await signedRequest('GET', '/api/v3/openOrders', symbol ? { symbol } : {});
    return res.status(200).json({ openOrders: open });
  } catch (e: any) {
    return res.status(500).json({ error: e.message || 'Unknown error', code: e.code, status: e.status });
  }
}
