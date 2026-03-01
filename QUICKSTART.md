# Trade Knowledge System - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Clone and Setup
```bash
git clone https://github.com/YOUR_USERNAME/trade-knowledge-system.git
cd trade-knowledge-system
cp .env.example .env
```

### Step 2: Launch Everything
```bash
docker compose up --build
```

That's it! The system will:
- ✅ Start PostgreSQL database
- ✅ Create all 7 tables (prices, features, signals, orders, positions, news, flags)
- ✅ Launch 5 services:
  - **Ingestor**: Fetches BTC/ETH/BNB prices every hour
  - **Feature Builder**: Computes EMA/RSI/MACD every 30 min
  - **Signal Engine**: Generates BUY/SELL signals every 30 min
  - **Execution Bot**: Executes paper trades every hour
  - **Web Agent**: Monitors news every 2 hours

## 📊 Check It's Working

### View Logs
```bash
docker compose logs -f ingestor
```

### Check Database
```bash
docker compose exec postgres psql -U trader -d trade_knowledge

# See latest prices
SELECT symbol, ts, close FROM prices ORDER BY ts DESC LIMIT 5;

# See latest signals
SELECT symbol, side, confidence, reason FROM trade_signals ORDER BY created_at DESC LIMIT 5;

# Exit
\q
```

## ⚙️ Configuration

Edit these files before starting:

### `configs/symbols.yaml` - Trading pairs
```yaml
timeframe: 1h
symbols:
  - BTCUSDT
  - ETHUSDT
```

### `configs/risk.yaml` - Risk limits
```yaml
max_position_usd: 1000
min_confidence: 60.0
stop_loss_pct: 2.0
```

## 🛑 System Control

### Pause Trading Manually
```bash
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "UPDATE system_flags SET value = 'true' WHERE key = 'TRADE_PAUSE'"
```

### Resume Trading
```bash
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "UPDATE system_flags SET value = 'false' WHERE key = 'TRADE_PAUSE'"
```

### Stop Everything
```bash
docker compose down
```

## 📈 What Happens Next

**First Hour:**
1. Ingestor fetches 100 historical candles for BTC, ETH, BNB
2. Feature builder computes indicators
3. Signal engine generates first signals
4. Execution bot executes paper trades

**Ongoing:**
- New prices fetched every hour
- Features recomputed every 30 minutes
- Signals generated every 30 minutes
- Trades executed every hour
- News monitored every 2 hours

## 🔍 Understanding the Data Flow

```
Binance API → Ingestor → prices table
                             ↓
              Feature Builder → features table
                             ↓
               Signal Engine → trade_signals table
                             ↓
              Execution Bot → orders + positions tables
              
GDELT News API → Web Agent → news_events + system_flags tables
```

## ⚠️ Safety Features

**The system is safe by default:**
- ✅ PAPER trading mode (no real money)
- ✅ Small position sizes
- ✅ Auto stop-loss and take-profit
- ✅ News-based auto-pause
- ✅ All actions logged

## 🔧 Troubleshooting

**Services won't start?**
```bash
docker compose logs
docker compose build --no-cache
```

**No data being ingested?**
```bash
docker compose logs ingestor
# Look for "Ingested X candles"
```

**Trading not executing?**
```bash
# Check if paused
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "SELECT * FROM system_flags WHERE key = 'TRADE_PAUSE'"
  
# Check signals
docker compose exec postgres psql -U trader -d trade_knowledge -c \
  "SELECT * FROM trade_signals ORDER BY created_at DESC LIMIT 5"
```

## 📚 Learn More

- Read full documentation: [README.md](README.md)
- Understand the architecture: [README.md#architecture](README.md#architecture)
- Future enhancements: [README.md#future-upgrade-path](README.md#future-upgrade-path)

## 🎯 Next Steps

1. **Monitor for 24 hours** - Let it run and collect data
2. **Review signals** - Check quality of generated signals
3. **Analyze positions** - See what trades were executed
4. **Tune parameters** - Adjust risk settings in `configs/risk.yaml`
5. **Add indicators** - Extend with your own technical indicators
6. **Build ML models** - Train on collected data
7. **Create dashboard** - Visualize performance

---

**Remember:** This is PAPER trading. No real money is at risk. Perfect for learning and testing!
