import { 
  getAllSafetyFlags, 
  getSafetyFlag, 
  setSafetyFlag, 
  isSystemHealthy,
  pauseTrading,
  resumeTrading
} from '../lib/safety.js';
import { log } from '../lib/log.js';

function cors(res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

export default async function handler(req: any, res: any) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  
  try {
    if (req.method === 'GET') {
      // Get safety flags or health status
      const { health, flag } = req.query;
      
      if (health === 'true') {
        const healthStatus = await isSystemHealthy();
        return res.status(200).json({ ok: true, health: healthStatus });
      }
      
      if (flag) {
        const safetyFlag = await getSafetyFlag(flag);
        return res.status(200).json({ ok: true, flag: safetyFlag });
      }
      
      const flags = await getAllSafetyFlags();
      return res.status(200).json({ ok: true, flags });
      
    } else if (req.method === 'POST') {
      // Update safety flag
      const { action, flagName, isPaused, reason, pausedBy } = req.body;
      
      if (action === 'pause_trading') {
        await pauseTrading(reason || 'Manual pause', pausedBy || 'api');
        return res.status(200).json({ ok: true, message: 'Trading paused' });
      }
      
      if (action === 'resume_trading') {
        await resumeTrading(pausedBy || 'api');
        return res.status(200).json({ ok: true, message: 'Trading resumed' });
      }
      
      if (!flagName || isPaused === undefined) {
        return res.status(400).json({ error: 'flagName and isPaused are required' });
      }
      
      const flag = await setSafetyFlag(flagName, isPaused, reason, pausedBy);
      return res.status(200).json({ ok: true, flag });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Safety endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
