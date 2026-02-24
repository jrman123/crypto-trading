#!/bin/bash
# System health check and monitoring script
# Verifies all services are running properly and database is responsive

set -e

echo "=========================================="
echo "Trading Knowledge System - Health Check"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "❌ Error: Docker is not running or you don't have permissions"
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if services are running
echo "📊 Service Status:"
echo ""

services=("postgres" "ingestor" "feature_builder" "signal_engine" "execution_bot" "web_agent")
all_healthy=true

for service in "${services[@]}"; do
    container_name="trading_${service}"
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        status=$(docker inspect --format='{{.State.Status}}' ${container_name} 2>/dev/null || echo "unknown")
        
        if [ "$status" = "running" ]; then
            # Check if container has been restarting
            restarts=$(docker inspect --format='{{.RestartCount}}' ${container_name} 2>/dev/null || echo "0")
            
            if [ ${restarts} -gt 5 ]; then
                echo "  ⚠️  ${service}: Running but has restarted ${restarts} times"
                all_healthy=false
            else
                echo "  ✓ ${service}: Running"
            fi
        else
            echo "  ❌ ${service}: ${status}"
            all_healthy=false
        fi
    else
        echo "  ❌ ${service}: Not found"
        all_healthy=false
    fi
done

echo ""

# Check database connectivity
echo "🔍 Database Health:"
echo ""

if docker-compose exec -T postgres psql -U postgres -d trading_knowledge -c "SELECT 1;" &> /dev/null; then
    echo "  ✓ Database is responsive"
    
    # Check table counts
    echo ""
    echo "📈 Database Statistics:"
    
    # Prices count
    price_count=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM prices;" 2>/dev/null | tr -d ' ')
    echo "  • Prices: ${price_count} records"
    
    # Features count
    feature_count=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM features;" 2>/dev/null | tr -d ' ')
    echo "  • Features: ${feature_count} records"
    
    # Signals count
    signal_count=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM trade_signals;" 2>/dev/null | tr -d ' ')
    echo "  • Signals: ${signal_count} records"
    
    # Orders count
    order_count=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM orders;" 2>/dev/null | tr -d ' ')
    echo "  • Orders: ${order_count} records"
    
    # News count
    news_count=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM news_events;" 2>/dev/null | tr -d ' ')
    echo "  • News Events: ${news_count} records"
    
    # Check TRADE_PAUSE flag
    trade_pause=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT flag_value FROM system_flags WHERE flag_name = 'TRADE_PAUSE';" 2>/dev/null | tr -d ' ')
    
    echo ""
    if [ "$trade_pause" = "t" ]; then
        echo "  🚨 TRADE_PAUSE: ENABLED (Trading is paused)"
    else
        echo "  ✓ TRADE_PAUSE: DISABLED (Trading is active)"
    fi
else
    echo "  ❌ Database is not responsive"
    all_healthy=false
fi

echo ""

# Check recent activity
echo "🔄 Recent Activity (last 5 minutes):"
echo ""

recent_prices=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM prices WHERE created_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
echo "  • New prices: ${recent_prices}"

recent_features=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM features WHERE created_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
echo "  • New features: ${recent_features}"

recent_signals=$(docker-compose exec -T postgres psql -U postgres -d trading_knowledge -t -c "SELECT COUNT(*) FROM trade_signals WHERE created_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
echo "  • New signals: ${recent_signals}"

echo ""

# Check for errors in logs
echo "⚠️  Recent Errors (last 10):"
echo ""
docker-compose logs --tail=100 | grep -i "error" | tail -10 || echo "  No recent errors found"

echo ""
echo "=========================================="

if [ "$all_healthy" = true ] && [ "$price_count" -gt "0" ]; then
    echo "✅ System Health: GOOD"
    echo ""
    echo "All services are running and data is flowing."
else
    echo "⚠️  System Health: NEEDS ATTENTION"
    echo ""
    
    if [ "$price_count" = "0" ]; then
        echo "⚠️  No price data found. System may be starting up."
        echo "   Wait 2-3 minutes and run this check again."
    fi
    
    if [ "$all_healthy" = false ]; then
        echo "⚠️  Some services are not healthy."
        echo "   Check logs with: docker-compose logs -f"
    fi
fi

echo "=========================================="
echo ""
echo "For detailed logs: docker-compose logs -f [service_name]"
echo "To restart a service: docker-compose restart [service_name]"
echo "To view live database: ./db-query.sh"
echo ""
