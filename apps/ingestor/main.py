"""
Binance Price Ingestor
Fetches kline (candlestick) data from Binance public API and stores in database.
"""
import os
import sys
import time
import logging
import yaml
import requests
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.db import insert_price, get_latest_prices

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_symbols():
    """Load symbols from configuration."""
    config_path = os.getenv('SYMBOLS_CONFIG', '/app/configs/symbols.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return [s['symbol'] for s in config['symbols'] if s.get('enabled', True)]
    except Exception as e:
        logger.error(f"Error loading symbols config: {e}")
        return ['BTCUSDT', 'ETHUSDT']  # Defaults


def load_sources_config():
    """Load sources configuration."""
    config_path = os.getenv('SOURCES_CONFIG', '/app/configs/sources.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Error loading sources config: {e}, using defaults")
        return {
            'exchange': {'base_url': 'https://api.binance.com'},
            'price_ingestion': {
                'interval': '1m',
                'lookback_hours': 168,
                'poll_interval_sec': 60
            }
        }


def fetch_klines(symbol, interval='1m', limit=100, base_url='https://api.binance.com'):
    """
    Fetch kline/candlestick data from Binance.
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        interval: Kline interval (1m, 5m, 15m, 1h, etc.)
        limit: Number of klines to fetch (max 1000)
        base_url: Binance API base URL
        
    Returns:
        List of kline data
    """
    url = f"{base_url}/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching klines for {symbol}: {e}")
        return []


def process_klines(symbol, klines):
    """
    Process and store kline data.
    
    Args:
        symbol: Trading pair symbol
        klines: List of kline data from Binance
    """
    stored_count = 0
    
    for kline in klines:
        try:
            # Binance kline format:
            # [open_time, open, high, low, close, volume, close_time, ...]
            timestamp = datetime.fromtimestamp(kline[0] / 1000)
            open_price = float(kline[1])
            high = float(kline[2])
            low = float(kline[3])
            close = float(kline[4])
            volume = float(kline[5])
            
            insert_price(symbol, timestamp, open_price, high, low, close, volume)
            stored_count += 1
            
        except Exception as e:
            logger.error(f"Error processing kline for {symbol}: {e}")
    
    logger.info(f"Stored {stored_count} klines for {symbol}")


def run_initial_backfill(symbols, config):
    """
    Perform initial backfill of historical data.
    
    Args:
        symbols: List of symbols to backfill
        config: Sources configuration
    """
    logger.info("Starting initial backfill...")
    
    base_url = config['exchange']['base_url']
    interval = config['price_ingestion']['interval']
    lookback_hours = config['price_ingestion'].get('lookback_hours', 168)
    
    # Calculate how many klines we need (approximate)
    # 1m interval = 60 per hour, 5m = 12 per hour, etc.
    interval_minutes = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440
    }
    minutes = interval_minutes.get(interval, 1)
    limit = min(1000, int(lookback_hours * 60 / minutes))
    
    for symbol in symbols:
        logger.info(f"Backfilling {symbol}...")
        klines = fetch_klines(symbol, interval, limit, base_url)
        if klines:
            process_klines(symbol, klines)
        time.sleep(0.5)  # Rate limiting


def run_continuous_ingestion(symbols, config):
    """
    Continuously fetch and store new price data.
    
    Args:
        symbols: List of symbols to monitor
        config: Sources configuration
    """
    logger.info("Starting continuous ingestion...")
    
    base_url = config['exchange']['base_url']
    interval = config['price_ingestion']['interval']
    poll_interval = config['price_ingestion'].get('poll_interval_sec', 60)
    
    while True:
        try:
            for symbol in symbols:
                # Fetch latest klines (small batch)
                klines = fetch_klines(symbol, interval, limit=10, base_url=base_url)
                if klines:
                    process_klines(symbol, klines)
                
                time.sleep(0.5)  # Rate limiting between symbols
            
            logger.info(f"Sleeping for {poll_interval} seconds...")
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            logger.info("Shutting down ingestor...")
            break
        except Exception as e:
            logger.error(f"Error in continuous ingestion: {e}")
            time.sleep(10)


def main():
    """Main entry point."""
    logger.info("Starting Binance Price Ingestor...")
    
    # Load configuration
    symbols = load_symbols()
    config = load_sources_config()
    
    logger.info(f"Monitoring symbols: {symbols}")
    
    # Check if we need to do initial backfill
    # Simple check: if we have no data, do backfill
    try:
        latest = get_latest_prices(symbols[0], limit=1)
        if not latest:
            run_initial_backfill(symbols, config)
    except Exception as e:
        logger.warning(f"Could not check for existing data: {e}")
        logger.info("Attempting initial backfill...")
        try:
            run_initial_backfill(symbols, config)
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
    
    # Start continuous ingestion
    run_continuous_ingestion(symbols, config)


if __name__ == '__main__':
    main()
