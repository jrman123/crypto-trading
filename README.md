# Crypto Trading Knowledge System

A complete Python-based crypto trading system with price ingestion, technical analysis, signal generation, paper trading execution, and news monitoring.

## System Architecture

This trading knowledge system consists of:

- **PostgreSQL Database**: Stores prices, features, signals, orders, positions, news events, and system flags
- **Price Ingestor**: Fetches kline data from Binance public API
- **Feature Builder**: Calculates technical indicators (EMA20, EMA50, RSI14, MACD)
- **Signal Engine**: Generates BUY/SELL signals based on indicator rules
- **Execution Bot**: Paper trades based on signals with risk management
- **Web Agent**: Monitors GDELT news and sets TRADE_PAUSE flag on bearish news

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git installed
- GitHub account (for repository creation)

### Step 1: Create Repository on GitHub

1. Go to [GitHub](https://github.com) and log in
2. Click the **+** icon in the top right, then **New repository**
3. Repository name: `crypto-trading` (or your preferred name)
4. Choose Public or Private
5. Do **not** initialize with README (we already have one)
6. Click **Create repository**

### Step 2: Clone Repository Locally

If you created a new empty repository:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-trading.git
cd crypto-trading

# If the repo is empty, you'll need to add this code
# (Skip this if you're working with this existing repo)
```

If you're using this existing repository:

```bash
git clone https://github.com/YOUR_USERNAME/crypto-trading.git
cd crypto-trading
```

### Step 3: Run Docker Compose

Build and start all services:

```bash
# Build and start all containers
docker compose up --build

# Or run in detached mode (background)
docker compose up --build -d
```

The system will:
1. Start PostgreSQL and initialize the schema
2. Backfill initial price data from Binance
3. Calculate technical indicators
4. Generate trading signals
5. Execute paper trades
6. Monitor news sources

### Step 4: View Data in PostgreSQL

Connect to the database to view data:

```bash
# Connect to PostgreSQL container
docker compose exec postgres psql -U trader -d trading
```

Once connected, run these queries:

```sql
-- View recent prices
SELECT symbol, timestamp, close, volume 
FROM prices 
ORDER BY timestamp DESC 
LIMIT 10;

-- View recent features (technical indicators)
SELECT symbol, timestamp, ema20, ema50, rsi14, macd 
FROM features 
ORDER BY timestamp DESC 
LIMIT 10;

-- View recent signals
SELECT symbol, signal_type, strength, reason, created_at 
FROM trade_signals 
ORDER BY created_at DESC 
LIMIT 10;

-- View recent orders
SELECT symbol, side, quantity, price, status, executed_at 
FROM orders 
ORDER BY created_at DESC 
LIMIT 10;

-- View current positions
SELECT symbol, quantity, avg_entry_price, unrealized_pnl 
FROM positions;

-- View recent news events
SELECT source, sentiment, impact_score, title 
FROM news_events 
ORDER BY published_at DESC 
LIMIT 10;

-- View system flags
SELECT flag_name, flag_value, reason, updated_at 
FROM system_flags;

-- Exit psql
\q
```

Alternatively, use psql from your host machine:

```bash
# If you have psql installed locally
psql -h localhost -U trader -d trading -c "SELECT * FROM trade_signals ORDER BY created_at DESC LIMIT 10;"
```

### Step 5: Monitor Logs

View logs from all services:

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f ingestor
docker compose logs -f feature_builder
docker compose logs -f signal_engine
docker compose logs -f execution_bot
docker compose logs -f web_agent
```

### Step 6: Push Code Updates

After making changes to the code:

```bash
# Check status
git status

# Add changed files
git add .

# Commit changes
git commit -m "Your commit message describing changes"

# Push to GitHub
git push origin main
```

If pushing for the first time to an empty repository:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/crypto-trading.git
git push -u origin main
```

## Configuration

### Symbols Configuration (`configs/symbols.yaml`)

Control which trading pairs to monitor:

```yaml
symbols:
  - symbol: BTCUSDT
    enabled: true
  - symbol: ETHUSDT
    enabled: true
```

### Risk Configuration (`configs/risk.yaml`)

Adjust risk parameters:

```yaml
max_position_size_usd: 1000
max_position_pct: 0.10
stop_loss_pct: 0.05
take_profit_pct: 0.10
max_daily_trades: 10
min_signal_strength: 0.6
```

### Sources Configuration (`configs/sources.yaml`)

Configure data sources and intervals:

```yaml
price_ingestion:
  interval: 1m
  poll_interval_sec: 60

features:
  calculation_interval_sec: 60

signals:
  generation_interval_sec: 60

execution:
  check_interval_sec: 30
  paper_trading: true
  initial_balance: 10000
```

## Database Schema

### Tables

- **prices**: Raw OHLCV data from exchanges
- **features**: Computed technical indicators
- **trade_signals**: Buy/sell signals with strength and reasoning
- **orders**: Executed paper trades
- **positions**: Current holdings
- **news_events**: News articles with sentiment analysis
- **system_flags**: Control flags (e.g., TRADE_PAUSE)

## Trading Logic

### Signal Generation Rules

**BUY Signals:**
- RSI < 30 (oversold)
- EMA20 > EMA50 with RSI < 50
- MACD histogram positive

**SELL Signals:**
- RSI > 70 (overbought)
- EMA20 < EMA50 with RSI > 50
- MACD histogram negative

### Risk Management

- Position sizing based on portfolio percentage and max USD
- Daily trade limits
- Minimum signal strength threshold
- Stop loss and take profit levels

### TRADE_PAUSE Mechanism

The web_agent monitors news and sets the TRADE_PAUSE flag when:
- High-impact bearish news detected (impact_score > 0.6)
- The execution_bot respects this flag and skips trading

## Stopping the System

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

## Development

### Project Structure

```
crypto-trading/
├── apps/
│   ├── common/
│   │   ├── db.py              # Database utilities
│   │   ├── indicators.py      # Technical indicators
│   │   ├── risk.py           # Risk management
│   │   └── exchange_paper.py # Paper trading simulator
│   ├── ingestor/main.py       # Price data ingestion
│   ├── feature_builder/main.py # Indicator calculation
│   ├── signal_engine/main.py  # Signal generation
│   ├── execution_bot/main.py  # Order execution
│   └── web_agent/main.py      # News monitoring
├── configs/
│   ├── symbols.yaml           # Trading pairs
│   ├── risk.yaml             # Risk parameters
│   └── sources.yaml          # Data sources config
├── schema.sql                 # Database schema
├── docker-compose.yml         # Container orchestration
├── Dockerfile                 # Python app container
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

### Adding New Features

1. Modify the relevant Python app in `apps/`
2. Update configuration files if needed
3. Rebuild containers: `docker compose up --build`
4. Test changes by monitoring logs and database

### Troubleshooting

**Problem: Containers not starting**
```bash
# Check logs
docker compose logs

# Restart services
docker compose restart
```

**Problem: Database connection errors**
```bash
# Verify postgres is healthy
docker compose ps

# Check database logs
docker compose logs postgres
```

**Problem: No price data**
```bash
# Check ingestor logs
docker compose logs ingestor

# Verify Binance API is accessible
curl https://api.binance.com/api/v3/ping
```

## License

MIT

## Disclaimer

This is a paper trading system for educational purposes only. Do not use with real money without proper testing and understanding of the risks involved in cryptocurrency trading.
