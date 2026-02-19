import { query } from './database.js';
import { log } from './log.js';

export interface SafetyFlag {
  id?: number;
  flag_name: string;
  is_paused: boolean;
  reason?: string;
  paused_at?: Date;
  paused_by?: string;
  updated_at?: Date;
}

export async function getSafetyFlag(flagName: string): Promise<SafetyFlag | null> {
  const sql = 'SELECT * FROM safety_flags WHERE flag_name = $1';
  const result = await query<SafetyFlag>(sql, [flagName]);
  return result.rows[0] || null;
}

export async function setSafetyFlag(
  flagName: string,
  isPaused: boolean,
  reason?: string,
  pausedBy?: string
): Promise<SafetyFlag> {
  const sql = `
    INSERT INTO safety_flags (flag_name, is_paused, reason, paused_at, paused_by, updated_at)
    VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
    ON CONFLICT (flag_name) DO UPDATE SET
      is_paused = EXCLUDED.is_paused,
      reason = EXCLUDED.reason,
      paused_at = EXCLUDED.paused_at,
      paused_by = EXCLUDED.paused_by,
      updated_at = CURRENT_TIMESTAMP
    RETURNING *
  `;
  
  const pausedAt = isPaused ? new Date() : null;
  
  const result = await query<SafetyFlag>(sql, [
    flagName,
    isPaused,
    reason,
    pausedAt,
    pausedBy
  ]);
  
  const flag = result.rows[0];
  
  log.info('Safety flag updated', { 
    flagName, 
    isPaused, 
    reason 
  });
  
  return flag;
}

export async function getAllSafetyFlags(): Promise<SafetyFlag[]> {
  const sql = 'SELECT * FROM safety_flags ORDER BY flag_name';
  const result = await query<SafetyFlag>(sql);
  return result.rows;
}

export async function checkSafety(flagName: string): Promise<boolean> {
  const flag = await getSafetyFlag(flagName);
  
  if (!flag) {
    log.warn('Safety flag not found, defaulting to paused', { flagName });
    return false; // Default to paused for safety
  }
  
  return !flag.is_paused; // Return true if NOT paused (i.e., safe to proceed)
}

export async function pauseTrading(reason: string, pausedBy: string = 'system'): Promise<void> {
  await setSafetyFlag('TRADING_ENABLED', true, reason, pausedBy);
  log.warn('Trading paused', { reason, pausedBy });
}

export async function resumeTrading(pausedBy: string = 'system'): Promise<void> {
  await setSafetyFlag('TRADING_ENABLED', false, 'Trading resumed', pausedBy);
  log.info('Trading resumed', { pausedBy });
}

export async function isSystemHealthy(): Promise<{
  healthy: boolean;
  flags: { [key: string]: boolean };
  issues: string[];
}> {
  const flags = await getAllSafetyFlags();
  const flagMap: { [key: string]: boolean } = {};
  const issues: string[] = [];
  
  for (const flag of flags) {
    flagMap[flag.flag_name] = !flag.is_paused;
    
    if (flag.is_paused && flag.reason) {
      issues.push(`${flag.flag_name}: ${flag.reason}`);
    }
  }
  
  const healthy = issues.length === 0;
  
  return { healthy, flags: flagMap, issues };
}
