import { placeOrder } from '../lib/binance.js';
import { getSymbolFilters } from '../lib/exchangeInfo.js';
import { seenRecently } from '../lib/idempotency.js';
import { baseUrl } from '../lib/binance.js';
import { log } from '../lib/log.js';

function cors(res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

export default async function handler(req: any, res: any) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });

  try {
    const { symbol, side, type = 'MARKET', quoteOrderQty, quantity, price, clientId } = req.body || {};

    if (!symbol || !side) return res.status(400).json({ error: 'symbol and side are required' });
    if (type === 'MARKET' && !quoteOrderQty && !quantity) {
      return res.status(400).json({ error: 'Provide quoteOrderQty or quantity for MARKET orders' });
    }
    if (type === 'LIMIT' && (!quantity || !price)) {
      return res.status(400).json({ error: 'LIMIT orders require quantity and price' });
    }

    // Basic guards
    const allow = (process.env.ALLOWED_SYMBOLS || '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
    if (allow.length && !allow.includes(String(symbol).toUpperCase())) {
      return res.status(400).json({ error: 'Symbol not allowed' });
    }
    const maxQuote = Number(process.env.MAX_QUOTE_PER_TRADE_USD || '0');
    if (quoteOrderQty && maxQuote > 0 && Number(quoteOrderQty) > maxQuote) {
      return res.status(400).json({ error: `quoteOrderQty exceeds limit (${maxQuote})` });
    }

    // Idempotency
    if (seenRecently(clientId)) {
      return res.status(200).json({ ok: true, info: 'duplicate suppressed (idempotent)', clientId });
    }

    // (Optional) check exchange filters for minNotional (best-effort)
    try {
      if (quoteOrderQty) {
        const f = await getSymbolFilters(baseUrl(), String(symbol).toUpperCase());
        if (f.minNotional && Number(quoteOrderQty) < f.minNotional) {
          return res.status(400).json({ error: `quoteOrderQty below minNotional ${f.minNotional}` });
        }
      }
    } catch (e) {
      log.warn('exchangeInfo check failed - continuing', (e as any)?.message);
    }

    const data = await placeOrder({ symbol, side, type, quoteOrderQty, quantity, price, clientId });
    return res.status(200).json(data);
  } catch (e: any) {
    return res.status(500).json({ error: e.message || 'Unknown error', code: e.code, status: e.status });
  }
}
