#!/bin/bash
# Quick start script for Testing Knowledge System
# This script helps you quickly test the system with Docker

set -e

echo "=========================================="
echo "Trading Knowledge System - Quick Start"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your Binance API credentials"
    echo "   You can use testnet credentials for testing"
    echo ""
    read -p "Press Enter when you've updated .env file (or press Ctrl+C to exit)..."
fi

echo ""
echo "🚀 Starting Trading Knowledge System..."
echo ""

# Build and start services
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ System Started Successfully!"
echo "=========================================="
echo ""
echo "Useful commands:"
echo ""
echo "  # View logs from all services"
echo "  docker-compose logs -f"
echo ""
echo "  # View logs from specific service"
echo "  docker-compose logs -f ingestor"
echo ""
echo "  # Connect to PostgreSQL"
echo "  docker-compose exec postgres psql -U postgres -d trading_knowledge"
echo ""
echo "  # Check system status"
echo "  docker-compose ps"
echo ""
echo "  # Stop all services"
echo "  docker-compose down"
echo ""
echo "  # Stop and remove all data (⚠️  WARNING: deletes database!)"
echo "  docker-compose down -v"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Monitor the logs:"
echo "   docker-compose logs -f"
echo ""
echo "2. Wait ~2-3 minutes for data to populate"
echo ""
echo "3. Check the database:"
echo "   docker-compose exec postgres psql -U postgres -d trading_knowledge"
echo "   Then run: SELECT COUNT(*) FROM prices;"
echo ""
echo "4. View signals:"
echo "   SELECT * FROM trade_signals ORDER BY timestamp DESC LIMIT 5;"
echo ""
echo "=========================================="
