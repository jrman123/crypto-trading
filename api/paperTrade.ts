import { executePaperTrade, getPaperTrades, calculatePortfolio } from '../lib/paperTrading.js';
import { getLatestSignal } from '../lib/signals.js';
import { checkSafety } from '../lib/safety.js';
import { log } from '../lib/log.js';

function cors(res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

export default async function handler(req: any, res: any) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  
  try {
    if (req.method === 'POST') {
      // Execute paper trade
      const { symbol, usdAmount } = req.body;
      
      if (!symbol) {
        return res.status(400).json({ error: 'symbol is required' });
      }
      
      // Check safety flag
      const isSafe = await checkSafety('TRADING_ENABLED');
      if (!isSafe) {
        return res.status(403).json({ error: 'Trading is currently paused for safety' });
      }
      
      // Get latest signal
      const signal = await getLatestSignal(symbol);
      if (!signal) {
        return res.status(400).json({ error: 'No signal available for this symbol' });
      }
      
      if (signal.signal_type === 'HOLD') {
        return res.status(200).json({ ok: true, message: 'Signal is HOLD, no trade executed' });
      }
      
      const trade = await executePaperTrade(signal, usdAmount || 100);
      return res.status(200).json({ ok: true, trade });
      
    } else if (req.method === 'GET') {
      // Get paper trades or portfolio
      const { symbol, portfolio } = req.query;
      
      if (portfolio === 'true') {
        const portfolioData = await calculatePortfolio();
        return res.status(200).json({ ok: true, portfolio: portfolioData });
      }
      
      const trades = await getPaperTrades(symbol);
      return res.status(200).json({ ok: true, trades });
      
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (e: any) {
    log.warn('Paper trading endpoint error', e.message);
    return res.status(500).json({ error: e.message || 'Internal error' });
  }
}
