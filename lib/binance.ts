import crypto from 'crypto';
import { log } from './log.js';

export type OrderInput = {
  symbol: string;
  side: 'BUY'|'SELL';
  type: 'MARKET'|'LIMIT';
  quoteOrderQty?: string | number;
  quantity?: string | number;
  price?: string | number;
  clientId?: string;
};

export function baseUrl(): string {
  const base = process.env.BINANCE_BASE_URL || 'https://api.binance.us';
  const testnet = (process.env.BINANCE_TESTNET || 'false').toLowerCase() === 'true';
  // Binance Spot testnet exists only for .com (not .us)
  if (testnet && base.includes('binance.com')) return 'https://testnet.binance.vision';
  return base;
}

function sign(params: string, secret: string) {
  return crypto.createHmac('sha256', secret).update(params).digest('hex');
}

function toQuery(obj: Record<string, any>): string {
  return Object.entries(obj)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
}

export async function signedRequest(method: 'GET'|'POST'|'DELETE', path: string, qp: Record<string, any>) {
  const apiKey = process.env.BINANCE_API_KEY || '';
  const secret = process.env.BINANCE_API_SECRET || '';
  if (!apiKey || !secret) throw new Error('Server API keys missing');

  const recvWindow = qp.recvWindow ?? 5000;
  const timestamp = Date.now();
  const params = toQuery({ ...qp, recvWindow, timestamp });
  const url = `${baseUrl()}${path}?${params}&signature=${sign(params, secret)}`;

  const r = await fetch(url, {
    method,
    headers: { 'X-MBX-APIKEY': apiKey, 'Content-Type': 'application/json' }
  });
  const data = await r.json().catch(() => ({}));

  if (!r.ok) {
    log.warn('Binance error', method, path, data);
    const errorData = data as any;
    throw Object.assign(new Error(errorData?.msg || `HTTP ${r.status}`), { code: errorData?.code, status: r.status });
  }
  return data;
}

export async function placeOrder(input: OrderInput) {
  const body: any = {
    symbol: input.symbol.toUpperCase(),
    side: input.side,
    type: input.type || 'MARKET',
    newClientOrderId: input.clientId,
    quoteOrderQty: input.quoteOrderQty,
    quantity: input.quantity,
    price: input.price,
  };
  return signedRequest('POST', '/api/v3/order', body);
}

export async function cancelOrder(symbol: string, orderId?: string, clientId?: string) {
  const qp: any = { symbol: symbol.toUpperCase() };
  if (orderId) qp.orderId = orderId;
  if (clientId) qp.origClientOrderId = clientId;
  return signedRequest('DELETE', '/api/v3/order', qp);
}

export async function openOrders(symbol?: string) {
  const qp: any = {};
  if (symbol) qp.symbol = symbol.toUpperCase();
  return signedRequest('GET', '/api/v3/openOrders', qp);
}
