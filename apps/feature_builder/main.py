"""
Feature Builder - Computes technical indicators from price data
"""
import os
import sys
import time
import logging
import yaml

# Add parent directory to path for imports
sys.path.insert(0, '/app/apps')
from common.db import db
from common.indicators import compute_all_indicators

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureBuilder:
    """Computes technical indicators and stores them"""
    
    def __init__(self, symbols_config_path: str = '/app/configs/symbols.yaml'):
        self.config = self._load_config(symbols_config_path)
        
    def _load_config(self, path: str) -> dict:
        """Load symbols configuration"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Failed to load symbols config: {e}")
            return {'timeframe': '1h', 'symbols': ['BTCUSDT']}
    
    def build_features_for_symbol(self, symbol: str, timeframe: str):
        """
        Compute and store features for a symbol
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
        """
        logger.info(f"Building features for {symbol} {timeframe}")
        
        # Fetch enough historical data for indicators
        # Need at least 50 candles for EMA50, more for MACD
        price_data = db.get_latest_prices(symbol, timeframe, limit=100)
        
        if not price_data:
            logger.warning(f"No price data available for {symbol}")
            return
        
        # Reverse to get oldest-to-newest order
        price_data.reverse()
        
        if len(price_data) < 50:
            logger.warning(f"Insufficient data for {symbol}: {len(price_data)} candles")
            return
        
        # Compute indicators for each candle (using all previous data)
        for i in range(50, len(price_data)):
            historical_data = price_data[:i+1]
            current_candle = price_data[i]
            
            # Compute all indicators
            indicators = compute_all_indicators(historical_data)
            
            # Store features
            try:
                db.upsert_features(
                    symbol=symbol,
                    timeframe=timeframe,
                    ts=current_candle['ts'],
                    ema20=indicators['ema20'],
                    ema50=indicators['ema50'],
                    rsi14=indicators['rsi14'],
                    macd=indicators['macd'],
                    macd_signal=indicators['macd_signal'],
                    macd_hist=indicators['macd_hist']
                )
            except Exception as e:
                logger.error(f"Failed to store features: {e}")
        
        logger.info(f"Features built for {symbol}")
    
    def run_once(self):
        """Run one feature building cycle for all symbols"""
        symbols = self.config.get('symbols', ['BTCUSDT'])
        timeframe = self.config.get('timeframe', '1h')
        
        for symbol in symbols:
            try:
                self.build_features_for_symbol(symbol, timeframe)
            except Exception as e:
                logger.error(f"Failed to build features for {symbol}: {e}")
        
        logger.info("Feature building cycle complete")


def main():
    """Main entry point"""
    logger.info("=== Feature Builder Starting ===")
    
    # Connect to database
    db.connect()
    
    # Initialize builder
    builder = FeatureBuilder()
    
    # Get interval from environment
    interval_seconds = int(os.getenv('FEATURES_EVERY', 1800))  # Default 30 min
    
    try:
        while True:
            try:
                builder.run_once()
            except Exception as e:
                logger.error(f"Feature building error: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down feature builder...")
    finally:
        db.disconnect()


if __name__ == '__main__':
    main()
