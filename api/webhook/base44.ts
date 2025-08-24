import { placeOrder } from '../../lib/binance.js';

// Accepts Base44-style payload and maps it to an order
export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });

  const p = req.body || {};
  const symbol = p.symbol || p.pair;
  const side = p.side;
  const type = p.type || 'MARKET';
  const quoteOrderQty = p.quoteOrderQty ?? p.usd_to_spend ?? p.amount;
  const clientId = p.clientId ?? p.run_id ?? p.id;

  if (!symbol || !side || !quoteOrderQty) {
    return res.status(400).json({ error: 'symbol, side, quoteOrderQty required' });
  }

  try {
    const data = await placeOrder({ symbol, side, type, quoteOrderQty, clientId });
    return res.status(200).json(data);
  } catch (e: any) {
    return res.status(500).json({ error: e.message || 'Unknown error', code: e.code, status: e.status });
  }
}
