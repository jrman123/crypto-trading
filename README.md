# Trade Knowledge System

A production-ready centralized Trading Knowledge Database and Intelligence System that powers crypto trading bots with real-time market data, AI-generated signals, web intelligence, and system-wide safety controls.

## 🎯 System Overview

The Trade Knowledge System serves as the "brain + memory" for trading bots, providing:

- **Real-time Market Data**: OHLCV candlestick data from Binance
- **Technical Analysis**: EMA, RSI, MACD indicators computed automatically
- **AI Trade Signals**: Rule-based + ML-ready signal generation
- **Paper Trading**: Safe execution environment before going live
- **Web Intelligence**: Real-time news monitoring with sentiment analysis
- **Risk Controls**: System-wide TRADE_PAUSE flags and risk management
- **Full Audit Trail**: Every action logged for learning and compliance

## 🏗️ Architecture

The system is built with 6 modular layers:

### Layer 1: Data Ingestion
- Pulls OHLCV candles from Binance public API
- Supports multiple symbols and timeframes
- Idempotent upsert logic (safe to run repeatedly)

### Layer 2: Feature Engineering
- Computes technical indicators:
  - EMA20, EMA50 (trend detection)
  - RSI14 (momentum)
  - MACD (12,26,9) with histogram (acceleration)

### Layer 3: Signal Engine
- Generates BUY/SELL/HOLD signals based on rules:
  - **BUY**: EMA20 > EMA50 + RSI > 50 + MACD histogram rising
  - **SELL**: EMA20 < EMA50 + RSI < 50 + MACD histogram falling
- Calculates confidence scores (0-100)
- Sets entry, stop loss, and take profit levels

### Layer 4: Execution Bot
- Reads latest signals
- Validates against risk parameters
- Checks system flags (TRADE_PAUSE)
- Executes paper trades with position sizing
- Updates positions and order history

### Layer 5: Web Intelligence Agent
- Monitors GDELT news API
- Analyzes sentiment (bullish/bearish/neutral)
- Detects high-impact events
- Auto-pauses trading on critical bearish news

### Layer 6: Database (PostgreSQL)
7 core tables:
- `prices` - OHLCV market data
- `features` - Technical indicators
- `trade_signals` - Generated signals
- `orders` - Executed trades
- `positions` - Current positions
- `news_events` - Market intelligence
- `system_flags` - Global controls

## 📁 Repository Structure

```
trade-knowledge-system/
├── apps/                          # Application services
│   ├── common/                    # Shared modules
│   │   ├── db.py                 # Database connection & queries
│   │   ├── indicators.py         # Technical indicator calculations
│   │   ├── risk.py               # Risk management utilities
│   │   └── exchange_paper.py     # Paper trading exchange adapter
│   ├── ingestor/
│   │   └── main.py               # Data ingestion service
│   ├── feature_builder/
│   │   └── main.py               # Feature computation service
│   ├── signal_engine/
│   │   └── main.py               # Signal generation service
│   ├── execution_bot/
│   │   └── main.py               # Trade execution service
│   └── web_agent/
│       └── main.py               # Web intelligence service
├── db/
│   └── schema.sql                # Database schema with all tables
├── configs/
│   ├── symbols.yaml              # Trading symbols configuration
│   ├── risk.yaml                 # Risk management parameters
│   └── sources.yaml              # News sources configuration
├── docker-compose.yml            # Multi-service orchestration
├── Dockerfile                    # Container definition
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .gitignore                    # Git exclusions
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- 4GB RAM minimum

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/trade-knowledge-system.git
cd trade-knowledge-system
```

### Step 2: Create Environment File

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults are production-safe):
- `POSTGRES_PASSWORD`: Change for production
- `EXECUTION_MODE`: Keep as `PAPER` until ready
- Intervals: Adjust based on your needs

### Step 3: Launch the System

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL database
2. Create all tables and indexes
3. Launch 5 services:
   - Data Ingestor (fetches market data)
   - Feature Builder (computes indicators)
   - Signal Engine (generates signals)
   - Execution Bot (executes trades)
   - Web Agent (monitors news)

### Step 4: Monitor Services

```bash
# View all service logs
docker compose logs -f

# View specific service
docker compose logs -f ingestor
docker compose logs -f execution_bot

# Check service status
docker compose ps
```

## 🔍 Inspecting the System

### Check Database Tables

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U trader -d trade_knowledge

# View latest prices
SELECT symbol, ts, close FROM prices ORDER BY ts DESC LIMIT 10;

# View latest signals
SELECT symbol, side, confidence, reason FROM trade_signals ORDER BY created_at DESC LIMIT 5;

# View orders
SELECT id, symbol, side, qty, price, status FROM orders ORDER BY created_at DESC LIMIT 10;

# View positions
SELECT * FROM positions;

# Check system flags
SELECT * FROM system_flags;

# Exit psql
\q
```

### Query Specific Data

```sql
-- Get latest features for BTC
SELECT * FROM features WHERE symbol = 'BTCUSDT' ORDER BY ts DESC LIMIT 1;

-- Get recent news events
SELECT title, impact, confidence FROM news_events ORDER BY created_at DESC LIMIT 5;

-- Check if trading is paused
SELECT * FROM system_flags WHERE key = 'TRADE_PAUSE';
```

## 📊 How Bots Access Knowledge

External bots can access the knowledge system via:

1. **Direct Database Queries** (read-only recommended):
```python
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='trade_knowledge',
    user='trader',
    password='your_password'
)
cursor = conn.cursor()
cursor.execute("SELECT * FROM latest_signals WHERE symbol = 'BTCUSDT'")
signal = cursor.fetchone()
```

2. **Read System Flags**:
```sql
-- Check if safe to trade
SELECT value FROM system_flags WHERE key = 'TRADE_PAUSE';
```

3. **Access Latest Indicators**:
```sql
-- Get latest technical analysis
SELECT ema20, ema50, rsi14, macd_hist 
FROM features 
WHERE symbol = 'BTCUSDT' 
ORDER BY ts DESC 
LIMIT 1;
```

## ⚙️ Configuration

### Trading Symbols (`configs/symbols.yaml`)
```yaml
timeframe: 1h
symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT
```

### Risk Parameters (`configs/risk.yaml`)
```yaml
max_position_usd: 1000
risk_per_trade_pct: 2.0
stop_loss_pct: 2.0
take_profit_pct: 4.0
min_confidence: 60.0
```

### News Sources (`configs/sources.yaml`)
```yaml
lookback_hours: 24
pause_confidence_threshold: 80
high_impact_bearish_keywords:
  - crash
  - hack
  - fraud
  # ... more keywords
```

## 🔒 Safety Features

The system includes multiple safety mechanisms:

1. **TRADE_PAUSE Flag**: Global kill switch
   - Set by web agent on high-impact bearish news
   - Can be manually set via database
   - Execution bot respects this flag

2. **Paper Trading First**: 
   - Default mode is PAPER (no real money)
   - All trades simulated and logged
   - Positions tracked in database

3. **Risk Limits**:
   - Maximum position size
   - Confidence thresholds
   - Stop loss and take profit levels

4. **Full Audit Trail**:
   - Every price, signal, order logged
   - Timestamps on all records
   - Reason tracking for signals

## 🛠️ Common Operations

### Stop All Services
```bash
docker compose down
```

### Restart Specific Service
```bash
docker compose restart execution_bot
```

### View Service Logs
```bash
docker compose logs -f signal_engine
```

### Backup Database
```bash
docker compose exec postgres pg_dump -U trader trade_knowledge > backup.sql
```

### Manually Pause Trading
```bash
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "UPDATE system_flags SET value = 'true' WHERE key = 'TRADE_PAUSE'"
```

### Resume Trading
```bash
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "UPDATE system_flags SET value = 'false' WHERE key = 'TRADE_PAUSE'"
```

## 📈 Future Upgrade Path

This system is designed for scalability. Planned enhancements:

### Phase 2: Machine Learning
- [ ] ML model training pipeline
- [ ] Feature importance analysis
- [ ] Ensemble signal generation
- [ ] Reinforcement learning agents

### Phase 3: API Layer
- [ ] FastAPI signal server
- [ ] WebSocket real-time feeds
- [ ] REST endpoints for bots
- [ ] Authentication & rate limiting

### Phase 4: Live Trading
- [ ] Live exchange adapter (Binance)
- [ ] Order management system
- [ ] Position reconciliation
- [ ] Real-time risk monitoring

### Phase 5: Analytics
- [ ] Backtesting engine
- [ ] Performance metrics dashboard
- [ ] Strategy comparison tools
- [ ] Profit/loss tracking

### Phase 6: Advanced Intelligence
- [ ] Social media sentiment analysis
- [ ] On-chain data integration
- [ ] Cross-exchange arbitrage detection
- [ ] Market regime classification

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check logs for errors
docker compose logs

# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up
```

### Database Connection Issues
```bash
# Verify PostgreSQL is healthy
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Restart database
docker compose restart postgres
```

### No Data Being Ingested
```bash
# Check ingestor logs
docker compose logs ingestor

# Manually trigger ingestion (exec into container)
docker compose exec ingestor python /app/apps/ingestor/main.py
```

### Trading Not Executing
Check in order:
1. Is TRADE_PAUSE set? `SELECT * FROM system_flags WHERE key = 'TRADE_PAUSE'`
2. Are signals being generated? `SELECT * FROM trade_signals ORDER BY created_at DESC LIMIT 5`
3. Do signals meet confidence threshold? Check `configs/risk.yaml`
4. Are there any errors? `docker compose logs execution_bot`

## 📝 Development

### Adding New Indicators
1. Add calculation function to `apps/common/indicators.py`
2. Update `compute_all_indicators()` to include new indicator
3. Add column to `features` table in `db/schema.sql`
4. Update `apps/feature_builder/main.py` to store new indicator

### Adding New Signal Rules
1. Edit `apps/signal_engine/main.py`
2. Modify `generate_signal()` method
3. Add new conditions to buy/sell logic
4. Test with paper trading first

### Custom Execution Logic
1. Edit `apps/execution_bot/main.py`
2. Modify position sizing in `execute_signal()`
3. Add custom validation rules
4. Update risk parameters in `configs/risk.yaml`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test thoroughly
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Open a Pull Request

## 📄 License

MIT License - Use at your own risk. Not financial advice.

## ⚠️ Disclaimer

This system is for educational and research purposes. Trading cryptocurrencies carries significant risk. Always:
- Test thoroughly with paper trading
- Start with small amounts
- Never invest more than you can afford to lose
- Understand the code before using it
- Monitor your systems continuously

## 🙏 Acknowledgments

- Binance API for market data
- GDELT Project for news data
- PostgreSQL for reliable data storage
- Docker for containerization

---

**Built with ❤️ for the trading community**

For questions, issues, or contributions, please open an issue on GitHub.
