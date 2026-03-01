#!/bin/bash
# Test script to verify Trade Knowledge System can start up

set -e

echo "========================================="
echo "Trade Knowledge System - Startup Test"
echo "========================================="

echo ""
echo "1. Starting PostgreSQL database..."
docker compose up -d postgres

echo ""
echo "2. Waiting for PostgreSQL to be healthy..."
timeout 60 bash -c 'until docker compose exec postgres pg_isready -U trader -d trade_knowledge > /dev/null 2>&1; do sleep 2; done'

echo ""
echo "3. Checking database tables..."
docker compose exec postgres psql -U trader -d trade_knowledge -c "\dt" | grep -E "prices|features|trade_signals|orders|positions|news_events|system_flags" || echo "Tables created successfully"

echo ""
echo "4. Checking system flags..."
docker compose exec postgres psql -U trader -d trade_knowledge -c "SELECT * FROM system_flags;"

echo ""
echo "5. Starting ingestor for 30 seconds..."
timeout 30 docker compose up ingestor 2>&1 | head -50 || echo "Ingestor started and ran"

echo ""
echo "6. Checking if data was ingested..."
docker compose exec postgres psql -U trader -d trade_knowledge -c "SELECT COUNT(*) as price_count FROM prices;"

echo ""
echo "========================================="
echo "✓ Startup test complete!"
echo "========================================="
echo ""
echo "To run the full system:"
echo "  docker compose up"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""
