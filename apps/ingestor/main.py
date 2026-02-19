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
