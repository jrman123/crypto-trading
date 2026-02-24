# Trading Knowledge System

A comprehensive **Trading Knowledge Database** that enables multiple crypto trading bots to access shared intelligence, place trades using ML/AI-generated signals, and keep datasets updated with real-time web/news intelligence.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                          │
│                  (Single Source of Truth)                       │
│                                                                 │
│  ┌──────────┬──────────┬────────────┬──────────┬────────────┐ │
│  │ prices   │ features │ trade_     │ orders   │ news_      │ │
│  │          │          │ signals    │          │ events     │ │
│  └──────────┴──────────┴────────────┴──────────┴────────────┘ │
│  ┌──────────┬──────────┬────────────┐                         │
│  │positions │ system_  │ audit_log  │                         │
│  │          │ flags    │            │                         │
│  └──────────┴──────────┴────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
           ↑              ↑              ↑              ↑
           │              │              │              │
    ┌──────┴──┐    ┌─────┴─────┐  ┌────┴────┐   ┌─────┴──────┐
    │Ingestor │    │  Feature  │  │ Signal  │   │    Web     │
    │         │───→│  Builder  │─→│ Engine  │─→ │   Agent    │
    └─────────┘    └───────────┘  └────┬────┘   └────────────┘
                                        │
                                        ↓
                                  ┌───────────┐
                                  │Execution  │
                                  │   Bot     │
                                  └───────────┘
```

### Core Components

1. **PostgreSQL Database** - Single source of truth containing:
   - `prices`: OHLCV candle data
   - `features`: Technical indicators (EMA, RSI, MACD, Bollinger Bands)
   - `trade_signals`: BUY/SELL/HOLD signals with confidence scores
   - `orders`: Executed orders (paper and live)
   - `positions`: Current and historical positions
   - `news_events`: Web/news intelligence with sentiment analysis
   - `system_flags`: System-wide controls (e.g., TRADE_PAUSE)
   - `audit_log`: Complete audit trail of all system actions

2. **Services** (Separate containerized applications):
   - **Ingestor**: Pulls candle data from exchange API → writes to `prices`
   - **Feature Builder**: Computes technical indicators → writes to `features`
   - **Signal Engine**: Analyzes features → generates `trade_signals`
   - **Execution Bot**: Reads signals → executes trades → writes `orders`/`positions`
   - **Web Agent**: Monitors news/web → writes `news_events` → sets `TRADE_PAUSE` flags

### Data Flow

```
Exchange API → Ingestor → prices table
                            ↓
            Feature Builder → features table
                            ↓
             Signal Engine → trade_signals table
                            ↓
            Execution Bot → orders & positions tables
            (respects system_flags.TRADE_PAUSE)

News/Web → Web Agent → news_events table
                     → system_flags table (TRADE_PAUSE)
```

## 🔒 Safety Design

### Separation of Concerns
- **Brain (Signal Generation)**: Signal Engine analyzes data and creates signals
- **Hands (Execution)**: Execution Bot executes trades based on signals
- Services are completely independent and can be stopped/started individually

### Safety Mechanisms
1. **System Flags**: 
   - `TRADE_PAUSE`: Halts all trading when set (e.g., during high-impact news)
   - Execution Bot **must** check this flag before placing orders
   
2. **Risk Controls** (configs/risk.yaml):
   - `max_position_usd`: Maximum position size per trade
   - `max_open_positions`: Maximum concurrent positions
   - `min_confidence`: Minimum signal confidence to execute (0-100)
   - `default_stop_loss_pct`: Default stop loss percentage
   - `default_take_profit_pct`: Default take profit percentage
   - Circuit breakers for rapid losses

3. **Paper Trading First**:
   - Default mode is PAPER (simulation)
   - All orders are marked `is_paper: true`
   - Switch to LIVE only after thorough testing

## 📊 How Bots Access Knowledge

### Database Access
All bots connect to the PostgreSQL database and query tables directly:

```python
from apps.common import db

# Get latest prices
prices = db.get_latest_prices('BTCUSDT', '1h', limit=100)

# Get latest signals
signals = db.get_latest_signals('BTCUSDT', limit=10)

# Check system flags
is_paused = db.get_system_flag('TRADE_PAUSE')
```

### API Access (Future Enhancement)
A REST API can be added later to provide:
- Read-only access to signals, prices, features
- Webhook endpoints for external services
- WebSocket feeds for real-time updates

## 📰 How Web Agent Keeps Data Updated

The Web Agent runs continuously and:

1. **Fetches News**: 
   - Polls RSS feeds from crypto news sources (CoinTelegraph, CoinDesk, etc.)
   - Can integrate with Reddit, Twitter APIs (optional)
   
2. **Analyzes Content**:
   - Extracts relevant crypto symbols mentioned
   - Performs sentiment analysis (positive/negative/neutral)
   - Determines impact level (high/medium/low)
   - Extracts keywords
   
3. **Stores Intelligence**:
   - Writes to `news_events` table with full metadata
   
4. **Triggers Safety Mechanisms**:
   - Sets `TRADE_PAUSE` flag when multiple high-impact events detected
   - Allows manual or automated un-pausing based on rules

## 🎯 PAPER → LIVE Trading

The system uses the **Adapter Pattern** for easy switching:

### Current Mode (Paper Trading)
```yaml
# In .env
TRADING_MODE=paper
```
- All orders simulated
- Marked with `is_paper: true` in database
- No real money at risk
- Full system testing possible

### Switching to Live Trading

1. **Verify Paper Trading Results**:
   ```sql
   -- Check paper trading performance
   SELECT symbol, 
          COUNT(*) as trade_count,
          SUM(realized_pnl) as total_pnl
   FROM positions 
   WHERE is_paper = true
   GROUP BY symbol;
   ```

2. **Update Configuration**:
   ```bash
   # In .env file
   TRADING_MODE=live
   BINANCE_TESTNET=false  # Use real Binance (not testnet)
   ```

3. **Review Risk Limits**:
   ```yaml
   # configs/risk.yaml
   risk_limits:
     max_position_usd: 50.0  # Start small!
     max_open_positions: 2
     min_confidence: 80.0    # Higher threshold for live
   ```

4. **Restart Services**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Code Adaptation
The execution bot automatically detects the mode:
```python
# In execution_bot/main.py
if is_paper_trading():
    execute_paper_order(signal)
else:
    execute_live_order(signal)  # Uses real exchange API
```

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose installed
- Binance API credentials (or use testnet)
- Basic understanding of PostgreSQL

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/crypto-trading.git
cd crypto-trading
```

### Step 2: Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

Required variables:
```bash
# Database (can leave as defaults for local development)
POSTGRES_DB=trading_knowledge
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Exchange API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true

# Trading mode (ALWAYS start with paper!)
TRADING_MODE=paper
```

### Step 3: Start the System
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### Step 4: Verify Services Are Running
```bash
# Check running containers
docker-compose ps

# Should see:
# - trading_postgres
# - trading_ingestor
# - trading_feature_builder
# - trading_signal_engine
# - trading_execution_bot
# - trading_web_agent
```

### Step 5: Check Database Tables
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d trading_knowledge

# List tables
\dt

# Check prices
SELECT symbol, timeframe, COUNT(*) 
FROM prices 
GROUP BY symbol, timeframe;

# Check features
SELECT * FROM features ORDER BY timestamp DESC LIMIT 5;

# Check signals
SELECT * FROM trade_signals ORDER BY timestamp DESC LIMIT 10;

# Check system flags
SELECT * FROM system_flags;

# Exit
\q
```

### Step 6: Monitor Activity
```bash
# Watch logs from all services
docker-compose logs -f

# Watch specific service
docker-compose logs -f ingestor
docker-compose logs -f signal_engine
docker-compose logs -f web_agent

# Run health check to verify system status
./health-check.sh
```

## 🎯 Performance Optimizations

The system includes several optimizations for production use:

1. **Connection Pooling**: Database connections are pooled (1-10 connections) for better performance
2. **Batch Inserts**: Price data is inserted in batches rather than one-by-one
3. **Retry Logic**: API calls use exponential backoff retry (3 attempts with 2s base delay)
4. **Health Checks**: Built-in health monitoring for services and database
5. **Graceful Error Handling**: Services continue running even if individual operations fail

### Monitoring System Health

Use the health check script to verify everything is running optimally:
```bash
./health-check.sh
```

This will show:
- Service status for all 6 containers
- Database connectivity
- Record counts for all tables
- TRADE_PAUSE flag status
- Recent activity (last 5 minutes)
- Recent errors from logs

## 🔧 Configuration

### Symbols (configs/symbols.yaml)
Define which crypto pairs to track:
```yaml
symbols:
  - symbol: BTCUSDT
    enabled: true
    timeframes: [1m, 5m, 1h, 4h, 1d]
```

### Risk Management (configs/risk.yaml)
Control trading behavior:
```yaml
risk_limits:
  max_position_usd: 100.0
  min_confidence: 70.0
  default_stop_loss_pct: 2.0
  default_take_profit_pct: 4.0
```

### Data Sources (configs/sources.yaml)
Configure news sources:
```yaml
news_sources:
  - name: cointelegraph
    type: rss
    url: https://cointelegraph.com/rss
    enabled: true
```

## 📈 Querying the Knowledge Base

### Get Latest Market Data
```sql
-- Latest prices for BTC
SELECT * FROM prices 
WHERE symbol = 'BTCUSDT' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Latest technical indicators
SELECT timestamp, ema_9, ema_21, rsi_14, macd 
FROM features 
WHERE symbol = 'BTCUSDT' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Analyze Signals
```sql
-- Recent trading signals
SELECT symbol, signal_type, confidence, reason, timestamp
FROM trade_signals 
WHERE signal_type != 'HOLD'
ORDER BY timestamp DESC 
LIMIT 20;

-- Signal performance (for paper trading)
SELECT s.symbol, s.signal_type, s.confidence,
       o.status, o.filled_quantity, o.avg_fill_price
FROM trade_signals s
LEFT JOIN orders o ON s.id = o.signal_id
WHERE o.is_paper = true
ORDER BY s.timestamp DESC;
```

### Check News Impact
```sql
-- Recent high-impact news
SELECT title, source, sentiment, impact_level, symbols, published_at
FROM news_events 
WHERE impact_level = 'high'
ORDER BY published_at DESC 
LIMIT 10;

-- News by sentiment
SELECT sentiment, COUNT(*) as count
FROM news_events 
WHERE published_at > NOW() - INTERVAL '24 hours'
GROUP BY sentiment;
```

## 🔄 Updating and Pushing to GitHub

### Make Code Changes
```bash
# Edit files as needed
nano apps/signal_engine/main.py

# Test locally
docker-compose down
docker-compose up --build
```

### Commit and Push
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Enhanced signal engine with additional indicators"

# Push to GitHub
git push origin main
```

### Pull Updates on Server
```bash
# On production server
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

## 🐛 Troubleshooting

### Services Won't Start

**Problem**: Docker containers exit immediately

**Solutions**:
```bash
# Check logs
docker-compose logs

# Verify .env file exists and has correct values
cat .env

# Check if PostgreSQL is healthy
docker-compose ps postgres

# Restart specific service
docker-compose restart ingestor
```

### PostgreSQL Connection Errors

**Problem**: Services can't connect to database

**Solutions**:
```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# Check if port 5432 is available
netstat -an | grep 5432

# Reset database
docker-compose down -v  # WARNING: Deletes all data!
docker-compose up --build
```

### Missing or Empty Tables

**Problem**: Tables don't exist or have no data

**Solutions**:
```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d trading_knowledge

# Check if tables exist
\dt

# If tables missing, run schema manually
docker-compose exec postgres psql -U postgres -d trading_knowledge -f /docker-entrypoint-initdb.d/schema.sql

# Check if ingestor is running
docker-compose logs ingestor

# Manually trigger data fetch (if needed)
docker-compose restart ingestor
```

### No Signals Generated

**Problem**: `trade_signals` table is empty

**Checklist**:
1. ✓ Prices table has data? `SELECT COUNT(*) FROM prices;`
2. ✓ Features table has data? `SELECT COUNT(*) FROM features;`
3. ✓ Signal engine running? `docker-compose ps signal_engine`
4. ✓ Check confidence threshold in configs/risk.yaml
5. ✓ View signal engine logs: `docker-compose logs signal_engine`

### TRADE_PAUSE Flag Stuck

**Problem**: Trading paused and won't resume

**Solution**:
```sql
-- Connect to database
docker-compose exec postgres psql -U postgres -d trading_knowledge

-- Check flag status
SELECT * FROM system_flags WHERE flag_name = 'TRADE_PAUSE';

-- Manually unpause (if safe to do so)
UPDATE system_flags 
SET flag_value = false, 
    reason = 'Manually unpaused',
    set_by = 'admin'
WHERE flag_name = 'TRADE_PAUSE';
```

### Services Using Too Much Memory/CPU

**Solutions**:
```bash
# Check resource usage
docker stats

# Reduce update frequencies in .env
INGESTOR_INTERVAL_SECONDS=300       # Every 5 min instead of 1 min
FEATURE_BUILDER_INTERVAL_SECONDS=300
SIGNAL_ENGINE_INTERVAL_SECONDS=600  # Every 10 min

# Restart services
docker-compose down
docker-compose up -d
```

### Can't Access Binance API

**Problem**: API key errors or rate limits

**Solutions**:
```bash
# Verify API credentials
echo $BINANCE_API_KEY
echo $BINANCE_API_SECRET

# Check if using testnet (if available)
# In .env:
BINANCE_TESTNET=true

# Reduce API call frequency
INGESTOR_INTERVAL_SECONDS=120

# Check Binance API status
curl https://api.binance.com/api/v3/ping
```

## 📚 Additional Resources

### Extending the System

1. **Add New Indicators**: Edit `apps/feature_builder/main.py`
2. **Custom Signal Strategies**: Modify `apps/signal_engine/main.py`
3. **Additional News Sources**: Update `configs/sources.yaml`
4. **REST API**: Add FastAPI service for external access
5. **Web Dashboard**: Create visualization service with Grafana

### Database Maintenance

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres trading_knowledge > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres trading_knowledge < backup.sql

# Clean old data (keep last 30 days)
docker-compose exec postgres psql -U postgres -d trading_knowledge -c \
  "DELETE FROM prices WHERE timestamp < NOW() - INTERVAL '30 days';"
```

## 📄 License

This project is provided as-is for educational purposes. Use at your own risk.

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Crypto trading involves substantial risk of loss
- Past performance does not guarantee future results
- Always start with paper trading
- Never trade with money you cannot afford to lose
- The authors are not responsible for any financial losses

---

**Built with**: Python, PostgreSQL, Docker, CCXT, Pandas, TA-Lib

**Questions?** Open an issue on GitHub or check the troubleshooting section above.
