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
Feature Builder Service
Computes technical indicators/features and writes to features table
"""
import sys
import os
import time
import pandas as pd
import ta

# Add parent directory to path to import common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import (
    db, setup_logging, get_symbols_config, get_risk_config,
    get_current_timestamp
)


class FeatureBuilder:
    """Builds technical indicator features from price data"""
    
    def __init__(self):
        self.logger = setup_logging('feature_builder')
        self.symbols_config = get_symbols_config()
        self.risk_config = get_risk_config()
        
    def fetch_price_data(self, symbol, timeframe, limit=200):
        """Fetch price data from database"""
        try:
            prices = db.get_latest_prices(symbol, timeframe, limit=limit)
            if not prices:
                self.logger.warning("No price data found", symbol=symbol, timeframe=timeframe)
                return None
            
            # Convert to DataFrame (reverse to get chronological order)
            df = pd.DataFrame(prices[::-1])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            return df
        except Exception as e:
            self.logger.error("Failed to fetch price data", symbol=symbol, error=str(e))
            return None
    
    def calculate_features(self, df):
        """Calculate technical indicators"""
        try:
            # Get indicator parameters from config
            strategy = self.risk_config.get('strategy', {})
            ema_periods = strategy.get('ema_periods', [9, 21, 50, 200])
            rsi_period = strategy.get('rsi_period', 14)
            macd_fast = strategy.get('macd_fast', 12)
            macd_slow = strategy.get('macd_slow', 26)
            macd_signal = strategy.get('macd_signal', 9)
            bb_period = strategy.get('bb_period', 20)
            bb_std = strategy.get('bb_std_dev', 2)
            
            # Ensure we have numeric columns
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            features = {}
            
            # Calculate EMAs
            for period in ema_periods:
                if len(df) >= period:
                    features[f'ema_{period}'] = ta.trend.ema_indicator(df['close'], window=period).iloc[-1]
            
            # Calculate RSI
            if len(df) >= rsi_period:
                features['rsi_14'] = ta.momentum.rsi(df['close'], window=rsi_period).iloc[-1]
            
            # Calculate MACD
            if len(df) >= macd_slow:
                macd_indicator = ta.trend.MACD(
                    df['close'], 
                    window_fast=macd_fast,
                    window_slow=macd_slow,
                    window_sign=macd_signal
                )
                features['macd'] = macd_indicator.macd().iloc[-1]
                features['macd_signal'] = macd_indicator.macd_signal().iloc[-1]
                features['macd_histogram'] = macd_indicator.macd_diff().iloc[-1]
            
            # Calculate Bollinger Bands
            if len(df) >= bb_period:
                bb_indicator = ta.volatility.BollingerBands(
                    df['close'],
                    window=bb_period,
                    window_dev=bb_std
                )
                features['bb_upper'] = bb_indicator.bollinger_hband().iloc[-1]
                features['bb_middle'] = bb_indicator.bollinger_mavg().iloc[-1]
                features['bb_lower'] = bb_indicator.bollinger_lband().iloc[-1]
            
            # Calculate Volume SMA
            if len(df) >= 20:
                features['volume_sma_20'] = df['volume'].rolling(window=20).mean().iloc[-1]
            
            return features
        except Exception as e:
            self.logger.error("Failed to calculate features", error=str(e))
            return None
    
    def process_symbol_timeframe(self, symbol, timeframe):
        """Process features for a symbol and timeframe"""
        try:
            # Fetch price data
            df = self.fetch_price_data(symbol, timeframe, limit=200)
            if df is None or len(df) < 50:
                self.logger.warning("Insufficient price data", symbol=symbol, timeframe=timeframe)
                return False
            
            # Calculate features
            features = self.calculate_features(df)
            if features is None:
                return False
            
            # Get latest timestamp
            latest_timestamp = df['timestamp'].iloc[-1]
            
            # Store features
            db.insert_features(symbol, timeframe, latest_timestamp, features)
            
            self.logger.info("Features calculated and stored", 
                           symbol=symbol, timeframe=timeframe, 
                           feature_count=len(features))
            
            db.log_audit('feature_builder', 'calculate_features', 'features', None,
                        {'symbol': symbol, 'timeframe': timeframe, 'features': list(features.keys())},
                        'success')
            
            return True
        except Exception as e:
            self.logger.error("Failed to process features", 
                            symbol=symbol, timeframe=timeframe, error=str(e))
            db.log_audit('feature_builder', 'calculate_features', 'features', None,
                        {'symbol': symbol, 'timeframe': timeframe}, 'failure', str(e))
            return False
    
    def run_once(self):
        """Run one feature building cycle"""
        self.logger.info("Starting feature building cycle")
        
        for symbol_config in self.symbols_config['symbols']:
            symbol = symbol_config['symbol']
            timeframes = symbol_config.get('timeframes', ['1h'])
            
            for timeframe in timeframes:
                self.process_symbol_timeframe(symbol, timeframe)
                time.sleep(0.1)  # Small delay
        
        self.logger.info("Feature building cycle complete")
    
    def run_continuous(self, interval_seconds=60):
        """Run feature building continuously"""
        self.logger.info(f"Starting continuous feature building (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                self.logger.info("Stopping feature builder")
                break
            except Exception as e:
                self.logger.error("Unexpected error in feature builder loop", error=str(e))
                time.sleep(10)


if __name__ == '__main__':
    builder = FeatureBuilder()
    
    # Get update interval from environment
    interval = int(os.getenv('FEATURE_BUILDER_INTERVAL_SECONDS', '60'))
    
    # Run continuously
    builder.run_continuous(interval_seconds=interval)
