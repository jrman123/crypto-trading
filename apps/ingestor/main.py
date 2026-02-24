"""
Ingestor Service
Pulls candle data from exchange API and writes to prices table
"""
import sys
import os
import time
from datetime import datetime, timedelta
import ccxt

# Add parent directory to path to import common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import (
    db, setup_logging, get_symbols_config, 
    parse_timeframe_to_seconds, get_current_timestamp
)


class Ingestor:
    """Ingests price data from exchange"""
    
    def __init__(self):
        self.logger = setup_logging('ingestor')
        self.exchange = self._setup_exchange()
        self.symbols_config = get_symbols_config()
        
    def _setup_exchange(self):
        """Setup exchange connection"""
        exchange_name = os.getenv('EXCHANGE', 'binance')
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # Set testnet if specified
        if os.getenv('BINANCE_TESTNET', 'false').lower() == 'true':
            exchange.set_sandbox_mode(True)
        
        self.logger.info(f"Connected to {exchange_name}")
        return exchange
    
    def fetch_candles(self, symbol, timeframe, limit=100):
        """Fetch OHLCV candles from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            self.logger.info(f"Fetched {len(ohlcv)} candles", symbol=symbol, timeframe=timeframe)
            return ohlcv
        except Exception as e:
            self.logger.error("Failed to fetch candles", symbol=symbol, timeframe=timeframe, error=str(e))
            db.log_audit('ingestor', 'fetch_candles', 'price', None, 
                        {'symbol': symbol, 'timeframe': timeframe}, 'failure', str(e))
            return []
    
    def store_candles(self, symbol, timeframe, ohlcv_data):
        """Store candles in database"""
        stored_count = 0
        for candle in ohlcv_data:
            timestamp_ms, open_price, high, low, close, volume = candle
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            
            try:
                db.insert_price(symbol, timeframe, timestamp, open_price, high, low, close, volume)
                stored_count += 1
            except Exception as e:
                self.logger.error("Failed to store candle", 
                                symbol=symbol, timestamp=timestamp, error=str(e))
        
        self.logger.info(f"Stored {stored_count} candles", symbol=symbol, timeframe=timeframe)
        db.log_audit('ingestor', 'store_candles', 'price', None,
                    {'symbol': symbol, 'timeframe': timeframe, 'count': stored_count}, 'success')
        return stored_count
    
    def run_once(self):
        """Run one ingestion cycle for all symbols and timeframes"""
        self.logger.info("Starting ingestion cycle")
        
        for symbol_config in self.symbols_config['symbols']:
            symbol = symbol_config['symbol']
            timeframes = symbol_config.get('timeframes', ['1h'])
            
            for timeframe in timeframes:
                try:
                    ohlcv = self.fetch_candles(symbol, timeframe, limit=100)
                    if ohlcv:
                        self.store_candles(symbol, timeframe, ohlcv)
                    
                    # Small delay to respect rate limits
                    time.sleep(0.5)
                except Exception as e:
                    self.logger.error("Ingestion error", symbol=symbol, timeframe=timeframe, error=str(e))
        
        self.logger.info("Ingestion cycle complete")
    
    def run_continuous(self, interval_seconds=60):
        """Run ingestion continuously"""
        self.logger.info(f"Starting continuous ingestion (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                self.logger.info("Stopping ingestor")
                break
            except Exception as e:
                self.logger.error("Unexpected error in ingestion loop", error=str(e))
                time.sleep(10)  # Wait before retrying


if __name__ == '__main__':
    ingestor = Ingestor()
    
    # Get update interval from config or environment
    interval = int(os.getenv('INGESTOR_INTERVAL_SECONDS', '60'))
    
    # Run continuously
    ingestor.run_continuous(interval_seconds=interval)
