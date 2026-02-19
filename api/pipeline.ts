import { ingestMarketData, MarketDataPoint } from '../lib/marketData.js';
import { buildFeatures } from '../lib/features.js';
import { generateSignal } from '../lib/signals.js';
import { executePaperTrade } from '../lib/paperTrading.js';
import { checkSafety } from '../lib/safety.js';
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
    const { marketData, autoTrade, usdAmount } = req.body;
    
    if (!marketData || !marketData.symbol) {
      return res.status(400).json({ error: 'marketData with symbol is required' });
    }
    
    const results: any = {
      steps: [],
      success: true
    };
    
    // Step 1: Ingest market data
    const isSafe = await checkSafety('DATA_INGESTION_ENABLED');
    if (!isSafe) {
      return res.status(403).json({ error: 'Data ingestion is currently paused for safety' });
    }
    
    const dataPoint: MarketDataPoint = {
      symbol: marketData.symbol,
      timestamp: marketData.timestamp || Date.now(),
      open: marketData.open || marketData.close,
      high: marketData.high || marketData.close,
      low: marketData.low || marketData.close,
      close: marketData.close,
      volume: marketData.volume || 0
    };
    
    await ingestMarketData(dataPoint);
    results.steps.push({ step: 'ingest', status: 'completed' });
    
    // Step 2: Build features
    const features = await buildFeatures(dataPoint.symbol, dataPoint.timestamp);
    results.steps.push({ step: 'features', status: 'completed', data: features });
    
    // Step 3: Generate signal
    const signalSafe = await checkSafety('SIGNAL_GENERATION_ENABLED');
    if (!signalSafe) {
      results.steps.push({ step: 'signal', status: 'skipped', reason: 'Signal generation paused' });
    } else {
      const signal = await generateSignal(dataPoint.symbol, dataPoint.timestamp);
      results.steps.push({ step: 'signal', status: 'completed', data: signal });
      results.signal = signal;
      
      // Step 4: Execute paper trade if requested and signal is actionable
      if (autoTrade && signal.signal_type !== 'HOLD') {
        const tradingSafe = await checkSafety('TRADING_ENABLED');
        if (!tradingSafe) {
          results.steps.push({ step: 'trade', status: 'skipped', reason: 'Trading paused' });
        } else {
          const trade = await executePaperTrade(signal, usdAmount || 100);
          results.steps.push({ step: 'trade', status: 'completed', data: trade });
          results.trade = trade;
        }
      } else if (autoTrade) {
        results.steps.push({ step: 'trade', status: 'skipped', reason: 'Signal is HOLD' });
      }
    }
    
    log.info('Pipeline executed', { symbol: dataPoint.symbol, steps: results.steps.length });
    
    return res.status(200).json({ ok: true, results });
    
  } catch (e: any) {
    log.warn('Pipeline error', e.message);
    return res.status(500).json({ 
      error: e.message || 'Pipeline execution failed',
      success: false 
    });
  }
}
