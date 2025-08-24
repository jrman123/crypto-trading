export const log = {
  info: (...a: any[]) => { if (process.env.LOG_LEVEL !== 'silent') console.log('[INFO]', ...a); },
  warn: (...a: any[]) => { if (process.env.LOG_LEVEL !== 'silent') console.warn('[WARN]', ...a); },
  error: (...a: any[]) => console.error('[ERROR]', ...a),
};
