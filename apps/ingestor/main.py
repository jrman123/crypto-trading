"""
Data Ingestor - Fetches OHLCV data from Binance and stores in database
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
import requests
import yaml

# Add parent directory to path for imports
sys.path.insert(0, '/app/apps')
from common.db import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BinanceIngestor:
    """Fetches candlestick data from Binance public API"""
    
    def __init__(self, symbols_config_path: str = '/app/configs/symbols.yaml'):
        self.base_url = 'https://api.binance.com/api/v3'
        self.config = self._load_config(symbols_config_path)
        
    def _load_config(self, path: str) -> dict:
        """Load symbols configuration"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded symbols config: {config}")
                return config
        except Exception as e:
            logger.error(f"Failed to load symbols config: {e}")
            return {'timeframe': '1h', 'symbols': ['BTCUSDT']}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> list:
        """
        Fetch candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch (max 1000)
            
        Returns:
            List of kline data
        """
        endpoint = f"{self.base_url}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            return []
    
    def parse_kline(self, kline: list) -> dict:
        """
        Parse Binance kline data
        
        Binance kline format:
        [
            open_time, open, high, low, close, volume,
            close_time, quote_volume, trades, taker_buy_base, taker_buy_quote, ignore
        ]
        """
        return {
            'ts': datetime.fromtimestamp(kline[0] / 1000),
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5])
        }
    
    def ingest_symbol(self, symbol: str, timeframe: str, limit: int = 100):
        """
        Ingest candlestick data for a symbol
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles to fetch
        """
        logger.info(f"Ingesting {symbol} {timeframe} (limit={limit})")
        
        klines = self.get_klines(symbol, timeframe, limit)
        if not klines:
            logger.warning(f"No data received for {symbol}")
            return
        
        inserted = 0
        for kline in klines:
            try:
                parsed = self.parse_kline(kline)
                db.upsert_price(
                    symbol=symbol,
                    timeframe=timeframe,
                    ts=parsed['ts'],
                    open_price=parsed['open'],
                    high=parsed['high'],
                    low=parsed['low'],
                    close=parsed['close'],
                    volume=parsed['volume']
                )
                inserted += 1
            except Exception as e:
                logger.error(f"Failed to insert kline: {e}")
        
        logger.info(f"Ingested {inserted}/{len(klines)} candles for {symbol}")
    
    def run_once(self):
        """Run one ingestion cycle for all configured symbols"""
        symbols = self.config.get('symbols', ['BTCUSDT'])
        timeframe = self.config.get('timeframe', '1h')
        
        for symbol in symbols:
            try:
                self.ingest_symbol(symbol, timeframe)
            except Exception as e:
                logger.error(f"Failed to ingest {symbol}: {e}")
        
        logger.info("Ingestion cycle complete")


def main():
    """Main entry point"""
    logger.info("=== Data Ingestor Starting ===")
    
    # Connect to database
    db.connect()
    
    # Initialize ingestor
    ingestor = BinanceIngestor()
    
    # Get interval from environment
    interval_seconds = int(os.getenv('INGEST_EVERY', 3600))  # Default 1 hour
    
    try:
        while True:
            try:
                ingestor.run_once()
            except Exception as e:
                logger.error(f"Ingestion error: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down ingestor...")
    finally:
        db.disconnect()


if __name__ == '__main__':
    main()
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
