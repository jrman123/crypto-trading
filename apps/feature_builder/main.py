"""
Feature Builder
Calculates technical indicators (EMA20, EMA50, RSI14, MACD) and stores in features table.
"""
import os
import sys
import time
import logging
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.db import get_latest_prices, insert_feature
from common.indicators import get_latest_indicator_values

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
        return ['BTCUSDT', 'ETHUSDT']


def load_sources_config():
    """Load sources configuration."""
    config_path = os.getenv('SOURCES_CONFIG', '/app/configs/sources.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Error loading sources config: {e}, using defaults")
        return {
            'features': {
                'calculation_interval_sec': 60,
                'min_data_points': 50
            }
        }


def calculate_features_for_symbol(symbol, min_data_points=50):
    """
    Calculate technical indicators for a symbol.
    
    Args:
        symbol: Trading pair symbol
        min_data_points: Minimum number of data points required
        
    Returns:
        Dictionary of calculated features or None
    """
    try:
        # Fetch enough price data for calculations
        # Need at least 50 for EMA50, plus buffer
        prices = get_latest_prices(symbol, limit=100)
        
        if not prices or len(prices) < min_data_points:
            logger.warning(f"Insufficient data for {symbol}: {len(prices) if prices else 0} points")
            return None
        
        # Reverse to get chronological order
        prices = list(reversed(prices))
        
        # Calculate indicators
        indicators = get_latest_indicator_values(prices)
        
        if not indicators:
            logger.warning(f"No indicators calculated for {symbol}")
            return None
        
        # Get latest timestamp
        latest_timestamp = prices[-1]['timestamp']
        
        return {
            'symbol': symbol,
            'timestamp': latest_timestamp,
            'ema20': indicators.get('ema20'),
            'ema50': indicators.get('ema50'),
            'rsi14': indicators.get('rsi14'),
            'macd': indicators.get('macd'),
            'macd_signal': indicators.get('macd_signal'),
            'macd_histogram': indicators.get('macd_histogram'),
        }
        
    except Exception as e:
        logger.error(f"Error calculating features for {symbol}: {e}")
        return None


def store_features(features):
    """
    Store calculated features in database.
    
    Args:
        features: Dictionary of features to store
    """
    try:
        insert_feature(
            symbol=features['symbol'],
            timestamp=features['timestamp'],
            ema20=features['ema20'],
            ema50=features['ema50'],
            rsi14=features['rsi14'],
            macd=features['macd'],
            macd_signal=features['macd_signal'],
            macd_histogram=features['macd_histogram']
        )
        logger.info(f"Stored features for {features['symbol']} at {features['timestamp']}")
    except Exception as e:
        logger.error(f"Error storing features: {e}")


def run_continuous_calculation(symbols, config):
    """
    Continuously calculate and store features.
    
    Args:
        symbols: List of symbols to process
        config: Sources configuration
    """
    logger.info("Starting continuous feature calculation...")
    
    interval = config['features'].get('calculation_interval_sec', 60)
    min_data_points = config['features'].get('min_data_points', 50)
    
    while True:
        try:
            for symbol in symbols:
                features = calculate_features_for_symbol(symbol, min_data_points)
                if features:
                    store_features(features)
                    logger.info(
                        f"{symbol}: EMA20={features.get('ema20', 'N/A'):.2f if features.get('ema20') else 'N/A'}, "
                        f"RSI14={features.get('rsi14', 'N/A'):.2f if features.get('rsi14') else 'N/A'}"
                    )
                else:
                    logger.debug(f"No features calculated for {symbol}")
            
            logger.info(f"Sleeping for {interval} seconds...")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("Shutting down feature builder...")
            break
        except Exception as e:
            logger.error(f"Error in continuous calculation: {e}")
            time.sleep(10)


def main():
    """Main entry point."""
    logger.info("Starting Feature Builder...")
    
    # Load configuration
    symbols = load_symbols()
    config = load_sources_config()
    
    logger.info(f"Processing symbols: {symbols}")
    
    # Start continuous calculation
    run_continuous_calculation(symbols, config)


if __name__ == '__main__':
    main()
