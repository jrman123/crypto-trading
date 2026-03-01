# Trading Knowledge System

A PostgreSQL-backed dataset and web-intelligence pipeline that powers crypto trading bots. This system ingests market data, builds technical features, generates trading signals, executes paper trades, and updates datasets via real-time news/web intelligence with safety pause flags.

## System Architecture

The Trading Knowledge System consists of the following components:

### 1. **Data Layer (PostgreSQL)**
- Market data storage (OHLCV candles)
- Technical features/indicators
- Trading signals
- Paper trade execution records
- Web intelligence data
- Safety flags
- Performance metrics

### 2. **Feature Engineering**
Technical indicators automatically calculated:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- EMA (Exponential Moving Averages: 12, 26)
- SMA (Simple Moving Averages: 50, 200)
- Volatility (standard deviation of returns)

### 3. **Signal Generation**
Automated trading signal generation based on:
- RSI levels (oversold/overbought)
- MACD crossovers
- EMA trends
- SMA golden/death crosses
- Volatility-adjusted confidence scores

### 4. **Paper Trading**
- Simulated trade execution
- Portfolio tracking
- P&L calculation
- Position management

### 5. **Web Intelligence**
- News article ingestion
- Sentiment analysis (positive/negative/neutral)
- Symbol extraction
- Real-time sentiment tracking

### 6. **Safety System**
Multiple safety flags to pause operations:
- `TRADING_ENABLED` - Controls trade execution
- `DATA_INGESTION_ENABLED` - Controls market data ingestion
- `SIGNAL_GENERATION_ENABLED` - Controls signal generation
- `WEB_INTELLIGENCE_ENABLED` - Controls news ingestion

## Database Setup

### Prerequisites
- PostgreSQL 12+ installed and running
- Database user with CREATE privileges

### Initialize Database

```bash
# Create database
createdb crypto_trading

# Run schema
psql crypto_trading < lib/schema.sql
```

### Environment Variables

Add to `.env` or Vercel environment variables:

```bash
# PostgreSQL Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/crypto_trading
# OR use individual variables:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_trading
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# Web Intelligence
WEB_INTELLIGENCE_ENABLED=true
NEWS_UPDATE_INTERVAL_MS=300000
```

## API Endpoints

### Market Data

**Ingest Market Data**
```bash
POST /api/marketData
{
  "symbol": "BTCUSDT",
  "timestamp": 1708300800000,
  "open": 50000,
  "high": 51000,
  "low": 49500,
  "close": 50500,
  "volume": 1000
}
```

**Get Market Data**
```bash
GET /api/marketData?symbol=BTCUSDT&limit=100
```

### Features

**Build Features**
```bash
POST /api/features
{
  "symbol": "BTCUSDT",
  "timestamp": 1708300800000
}
```

**Get Features**
```bash
GET /api/features?symbol=BTCUSDT
```

### Signals

**Generate Signal**
```bash
POST /api/signals
{
  "symbol": "BTCUSDT",
  "timestamp": 1708300800000
}
```

**Get Latest Signal**
```bash
GET /api/signals?symbol=BTCUSDT&latest=true
```

**Get Signal History**
```bash
GET /api/signals?symbol=BTCUSDT&limit=50
```

### Paper Trading

**Execute Paper Trade**
```bash
POST /api/paperTrade
{
  "symbol": "BTCUSDT",
  "usdAmount": 100
}
```

**Get Portfolio**
```bash
GET /api/paperTrade?portfolio=true
```

**Get Trade History**
```bash
GET /api/paperTrade?symbol=BTCUSDT
```

### Web Intelligence

**Ingest News/Article**
```bash
POST /api/webIntelligence
{
  "source": "CoinDesk",
  "title": "Bitcoin surges to new highs",
  "content": "Bitcoin reaches $50,000...",
  "url": "https://example.com/article",
  "published_at": 1708300800000
}
```

**Get Web Intelligence**
```bash
GET /api/webIntelligence?symbol=BTCUSDT&limit=50
```

**Get Recent Sentiment**
```bash
GET /api/webIntelligence?symbol=BTCUSDT&sentiment=true&hours=24
```

### Safety Controls

**Get System Health**
```bash
GET /api/safety?health=true
```

**Pause Trading**
```bash
POST /api/safety
{
  "action": "pause_trading",
  "reason": "High volatility detected",
  "pausedBy": "risk_manager"
}
```

**Resume Trading**
```bash
POST /api/safety
{
  "action": "resume_trading",
  "pausedBy": "admin"
}
```

**Update Safety Flag**
```bash
POST /api/safety
{
  "flagName": "SIGNAL_GENERATION_ENABLED",
  "isPaused": true,
  "reason": "Maintenance",
  "pausedBy": "admin"
}
```

### Complete Pipeline

**Execute Full Pipeline** (Ingest → Features → Signal → Trade)
```bash
POST /api/pipeline
{
  "marketData": {
    "symbol": "BTCUSDT",
    "close": 50500,
    "volume": 1000,
    "timestamp": 1708300800000
  },
  "autoTrade": true,
  "usdAmount": 100
}
```

Response:
```json
{
  "ok": true,
  "results": {
    "steps": [
      { "step": "ingest", "status": "completed" },
      { "step": "features", "status": "completed", "data": {...} },
      { "step": "signal", "status": "completed", "data": {...} },
      { "step": "trade", "status": "completed", "data": {...} }
    ],
    "signal": {
      "signal_type": "BUY",
      "strength": 0.75,
      "confidence": 0.82,
      "reasons": ["RSI oversold", "MACD bullish crossover"]
    },
    "trade": {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "quantity": 0.00198,
      "price": 50500
    }
  }
}
```

## Usage Examples

### 1. Basic Trading Bot Workflow

```javascript
// 1. Ingest market data from exchange
const marketData = {
  symbol: "BTCUSDT",
  close: 50500,
  volume: 1000,
  timestamp: Date.now()
};

// 2. Run complete pipeline
const response = await fetch('/api/pipeline', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    marketData,
    autoTrade: true,
    usdAmount: 100
  })
});

const result = await response.json();
console.log('Trade executed:', result.results.trade);
```

### 2. Manual Analysis

```javascript
// Get latest signal
const signal = await fetch('/api/signals?symbol=BTCUSDT&latest=true')
  .then(r => r.json());

// Check sentiment
const sentiment = await fetch('/api/webIntelligence?symbol=BTCUSDT&sentiment=true')
  .then(r => r.json());

// Make decision
if (signal.signal.signal_type === 'BUY' && sentiment.sentiment.averageSentiment > 0.6) {
  // Execute trade
}
```

### 3. Safety Monitoring

```javascript
// Check system health
const health = await fetch('/api/safety?health=true')
  .then(r => r.json());

if (!health.health.healthy) {
  console.log('Issues detected:', health.health.issues);
  // Pause trading
  await fetch('/api/safety', {
    method: 'POST',
    body: JSON.stringify({
      action: 'pause_trading',
      reason: 'System health check failed'
    })
  });
}
```

## Integration with Existing Trading System

The Trading Knowledge System extends the existing Binance trading infrastructure:

### Real Trading Integration

```javascript
// 1. Get signal from knowledge system
const signal = await fetch('/api/signals?symbol=BTCUSDT&latest=true')
  .then(r => r.json());

// 2. If signal is strong enough, execute real trade via existing API
if (signal.signal.strength > 0.7 && signal.signal.signal_type !== 'HOLD') {
  await fetch('/api/order', {
    method: 'POST',
    body: JSON.stringify({
      symbol: 'BTCUSDT',
      side: signal.signal.signal_type,
      type: 'MARKET',
      quoteOrderQty: '20'
    })
  });
}
```

## Performance Metrics

Track trading performance over time:

```sql
-- Calculate win rate
SELECT 
  symbol,
  COUNT(*) as total_trades,
  SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sells,
  SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buys
FROM paper_trades
WHERE status = 'EXECUTED'
GROUP BY symbol;
```

## Safety Best Practices

1. **Always monitor safety flags** before executing trades
2. **Set pause flags during maintenance** or system updates
3. **Monitor web intelligence sentiment** for market conditions
4. **Use paper trading** to validate strategies before real trading
5. **Review performance metrics** regularly

## Development

### Run Tests
```bash
npm test
```

### Build
```bash
npm run build
```

### Local Development
```bash
# Start Vercel dev server
npm run dev

# Access endpoints at http://localhost:3000/api/*
```

## Security Considerations

- All database credentials should be in environment variables
- Never commit `.env` files
- Use read-only database users for query-only endpoints
- Implement rate limiting on public endpoints
- Monitor for unusual trading patterns
- Set up alerts for safety flag changes

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check tables
psql $DATABASE_URL -c "\dt"
```

### Missing Dependencies
```bash
npm install
```

### Clear Test Data
```sql
TRUNCATE market_data, features, signals, paper_trades, web_intelligence RESTART IDENTITY CASCADE;
```

## License

© 2025 - MIT License
