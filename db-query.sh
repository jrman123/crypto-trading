#!/bin/bash
# Database query helper script
# Provides quick access to common database queries

set -e

echo "=========================================="
echo "Trading Knowledge Database - Query Helper"
echo "=========================================="
echo ""

# Function to run SQL query
run_query() {
    docker-compose exec -T postgres psql -U postgres -d trading_knowledge -c "$1"
}

# Check if postgres is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "❌ Error: PostgreSQL container is not running"
    echo "Start it with: docker-compose up -d postgres"
    exit 1
fi

echo "Select a query:"
echo ""
echo "1) List all tables"
echo "2) Count prices by symbol"
echo "3) Latest 10 prices for BTCUSDT"
echo "4) Latest 10 features for BTCUSDT"
echo "5) Latest 10 trade signals"
echo "6) Latest 10 orders"
echo "7) Check system flags"
echo "8) Recent high-impact news"
echo "9) Trading statistics (paper trading)"
echo "10) Open PostgreSQL shell"
echo ""
read -p "Enter choice (1-10): " choice

echo ""

case $choice in
    1)
        echo "📋 All Tables:"
        run_query "\dt"
        ;;
    2)
        echo "📊 Price Count by Symbol:"
        run_query "SELECT symbol, timeframe, COUNT(*) as count FROM prices GROUP BY symbol, timeframe ORDER BY symbol, timeframe;"
        ;;
    3)
        echo "💰 Latest 10 Prices for BTCUSDT:"
        run_query "SELECT timestamp, open, high, low, close, volume FROM prices WHERE symbol = 'BTCUSDT' ORDER BY timestamp DESC LIMIT 10;"
        ;;
    4)
        echo "📈 Latest 10 Features for BTCUSDT:"
        run_query "SELECT timestamp, ema_9, ema_21, rsi_14, macd FROM features WHERE symbol = 'BTCUSDT' ORDER BY timestamp DESC LIMIT 10;"
        ;;
    5)
        echo "🎯 Latest 10 Trade Signals:"
        run_query "SELECT timestamp, symbol, signal_type, confidence, reason FROM trade_signals ORDER BY timestamp DESC LIMIT 10;"
        ;;
    6)
        echo "📝 Latest 10 Orders:"
        run_query "SELECT placed_at, symbol, side, status, quantity, price, is_paper FROM orders ORDER BY placed_at DESC LIMIT 10;"
        ;;
    7)
        echo "🚦 System Flags:"
        run_query "SELECT flag_name, flag_value, reason, set_by, set_at FROM system_flags;"
        ;;
    8)
        echo "📰 Recent High-Impact News:"
        run_query "SELECT published_at, title, source, sentiment, impact_level FROM news_events WHERE impact_level = 'high' ORDER BY published_at DESC LIMIT 10;"
        ;;
    9)
        echo "📊 Trading Statistics (Paper Trading):"
        run_query "SELECT COUNT(*) as total_orders, COUNT(DISTINCT symbol) as symbols_traded, SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_orders FROM orders WHERE is_paper = true;"
        ;;
    10)
        echo "🔧 Opening PostgreSQL shell..."
        echo "   Type \q to exit"
        echo ""
        docker-compose exec postgres psql -U postgres -d trading_knowledge
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
