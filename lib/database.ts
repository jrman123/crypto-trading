import pg from 'pg';
import { log } from './log.js';

const { Pool } = pg;

let pool: pg.Pool | null = null;

export function getPool(): pg.Pool {
  if (!pool) {
    const config: pg.PoolConfig = process.env.DATABASE_URL 
      ? { connectionString: process.env.DATABASE_URL }
      : {
          host: process.env.POSTGRES_HOST || 'localhost',
          port: parseInt(process.env.POSTGRES_PORT || '5432'),
          database: process.env.POSTGRES_DB || 'crypto_trading',
          user: process.env.POSTGRES_USER || 'user',
          password: process.env.POSTGRES_PASSWORD || 'password',
        };

    pool = new Pool(config);

    pool.on('error', (err) => {
      log.warn('Unexpected database error', err.message);
    });
  }

  return pool;
}

export async function query<T = any>(text: string, params?: any[]): Promise<pg.QueryResult<T>> {
  const client = getPool();
  try {
    return await client.query(text, params);
  } catch (error: any) {
    log.warn('Database query error', error.message);
    throw error;
  }
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
