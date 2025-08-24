/**
 * Simple in-memory idempotency store with TTL. 
 * NOTE: Serverless instances may not share memory; use this as a best-effort guard.
 */
const store = new Map<string, number>(); // key -> expiresAt (ms)
const TTL_MS = 60_000; // 60s

export function seenRecently(key?: string): boolean {
  if (!key) return false;
  const now = Date.now();
  // purge
  for (const [k, exp] of store) {
    if (exp <= now) store.delete(k);
  }
  const exp = store.get(key);
  if (exp && exp > now) return true;
  store.set(key, now + TTL_MS);
  return false;
}
