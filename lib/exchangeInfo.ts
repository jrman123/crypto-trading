type Filters = {
  minNotional?: number;
  minQty?: number;
  stepSize?: number;
};

const cache = new Map<string, { at: number; filters: Filters }>();
const TTL = 15 * 60 * 1000; // 15 minutes

function parseFilters(symbolInfo: any): Filters {
  const f: Filters = {};
  for (const filter of symbolInfo.filters || []) {
    if (filter.filterType === 'NOTIONAL' || filter.filterType === 'MIN_NOTIONAL') {
      f.minNotional = Number(filter.minNotional || filter.minNotional);
    }
    if (filter.filterType === 'LOT_SIZE') {
      f.minQty = Number(filter.minQty);
      f.stepSize = Number(filter.stepSize);
    }
  }
  return f;
}

export async function getSymbolFilters(baseUrl: string, symbol: string): Promise<Filters> {
  const key = symbol.toUpperCase();
  const now = Date.now();
  const hit = cache.get(key);
  if (hit && (now - hit.at) < TTL) return hit.filters;
  const url = `${baseUrl}/api/v3/exchangeInfo?symbol=${key}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`exchangeInfo failed: ${r.status}`);
  const data = await r.json() as any;
  const info = (data.symbols && data.symbols[0]) || {};
  const filters = parseFilters(info);
  cache.set(key, { at: now, filters });
  return filters;
}
