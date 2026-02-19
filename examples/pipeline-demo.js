#!/usr/bin/env node

/**
 * Example script demonstrating the Trading Knowledge System pipeline
 * 
 * This script shows how to:
 * 1. Ingest market data
 * 2. Build technical features
 * 3. Generate trading signals
 * 4. Execute paper trades
 * 5. Monitor system health
 * 
 * Usage: node examples/pipeline-demo.js
 */

async function runPipelineDemo() {
  const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

  console.log('🚀 Trading Knowledge System Pipeline Demo\n');

  // Step 1: Check system health
  console.log('1️⃣ Checking system health...');
  const healthResponse = await fetch(`${BASE_URL}/api/safety?health=true`);
  const health = await healthResponse.json();
  console.log('   System health:', health.health.healthy ? '✅ Healthy' : '❌ Issues detected');
  if (!health.health.healthy) {
    console.log('   Issues:', health.health.issues);
  }
  console.log();

  // Step 2: Ingest market data
  console.log('2️⃣ Ingesting market data...');
  const marketData = {
    symbol: 'BTCUSDT',
    timestamp: Date.now(),
    close: 50500,
    open: 50000,
    high: 51000,
    low: 49500,
    volume: 1000
  };

  const pipelineResponse = await fetch(`${BASE_URL}/api/pipeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      marketData,
      autoTrade: true,
      usdAmount: 100
    })
  });

  const result = await pipelineResponse.json();

  if (!result.ok) {
    console.error('   ❌ Pipeline failed:', result.error);
    return;
  }

  console.log('   ✅ Pipeline completed');
  console.log();

  // Step 3: Review results
  console.log('3️⃣ Pipeline Results:');
  result.results.steps.forEach(step => {
    const status = step.status === 'completed' ? '✅' : 
                   step.status === 'skipped' ? '⏭️' : '❌';
    console.log(`   ${status} ${step.step}: ${step.status}`);
    if (step.reason) console.log(`      Reason: ${step.reason}`);
  });
  console.log();

  // Step 4: Display signal
  if (result.results.signal) {
    const signal = result.results.signal;
    console.log('4️⃣ Trading Signal Generated:');
    console.log(`   Symbol: ${signal.symbol}`);
    console.log(`   Type: ${signal.signal_type}`);
    console.log(`   Strength: ${(signal.strength * 100).toFixed(2)}%`);
    console.log(`   Confidence: ${(signal.confidence * 100).toFixed(2)}%`);
    console.log(`   Reasons: ${signal.reasons.join(', ')}`);
    console.log();
  }

  // Step 5: Display trade
  if (result.results.trade) {
    const trade = result.results.trade;
    console.log('5️⃣ Paper Trade Executed:');
    console.log(`   Side: ${trade.side}`);
    console.log(`   Quantity: ${trade.quantity.toFixed(8)}`);
    console.log(`   Price: $${trade.price.toFixed(2)}`);
    console.log(`   Total Value: $${trade.total_value.toFixed(2)}`);
    console.log();
  }

  // Step 6: Get portfolio
  console.log('6️⃣ Portfolio Status:');
  const portfolioResponse = await fetch(`${BASE_URL}/api/paperTrade?portfolio=true`);
  const portfolio = await portfolioResponse.json();

  if (portfolio.ok && portfolio.portfolio) {
    console.log(`   Total Value: $${portfolio.portfolio.totalValue.toFixed(2)}`);
    console.log(`   Total P&L: $${portfolio.portfolio.totalPnL.toFixed(2)}`);
    console.log('   Positions:');
    Object.entries(portfolio.portfolio.positions).forEach(([symbol, pos]) => {
      console.log(`     ${symbol}: ${pos.quantity.toFixed(8)} @ $${pos.avgPrice.toFixed(2)}`);
    });
  }
  console.log();

  console.log('✨ Demo completed successfully!');
}

// Run demo
if (typeof window === 'undefined') {
  runPipelineDemo().catch(console.error);
}

export { runPipelineDemo };
