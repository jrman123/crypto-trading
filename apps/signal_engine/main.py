"""
Signal Engine
Generates trade signals based on technical indicators using simple rules.
"""
import os
import sys
import time
import logging
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.db import execute_query, insert_signal

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
            'signals': {
                'generation_interval_sec': 60
            }
        }


def get_latest_features(symbol):
    """
    Get latest features for a symbol.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Dictionary of features or None
    """
    query = """
        SELECT * FROM features
        WHERE symbol = %s
        ORDER BY timestamp DESC
        LIMIT 1
    """
    results = execute_query(query, (symbol,))
    return results[0] if results else None


def generate_signal(symbol, features):
    """
    Generate trading signal based on features.
    
    Simple rules:
    1. BUY signal:
       - RSI < 30 (oversold) OR
       - EMA20 crosses above EMA50 (golden cross) AND RSI < 50
       - MACD histogram positive and increasing
    
    2. SELL signal:
       - RSI > 70 (overbought) OR
       - EMA20 crosses below EMA50 (death cross) AND RSI > 50
       - MACD histogram negative and decreasing
    
    3. HOLD otherwise
    
    Args:
        symbol: Trading pair symbol
        features: Dictionary of features
        
    Returns:
        Tuple of (signal_type, strength, reason)
    """
    if not features:
        return 'HOLD', 0.0, 'No features available'
    
    ema20 = features.get('ema20')
    ema50 = features.get('ema50')
    rsi14 = features.get('rsi14')
    macd = features.get('macd')
    macd_signal = features.get('macd_signal')
    macd_histogram = features.get('macd_histogram')
    
    # Check if we have required data
    if None in [ema20, ema50, rsi14]:
        return 'HOLD', 0.0, 'Insufficient indicator data'
    
    reasons = []
    buy_score = 0.0
    sell_score = 0.0
    
    # RSI signals
    if rsi14 < 30:
        buy_score += 0.4
        reasons.append(f"RSI oversold ({rsi14:.2f})")
    elif rsi14 > 70:
        sell_score += 0.4
        reasons.append(f"RSI overbought ({rsi14:.2f})")
    
    # EMA crossover signals
    if ema20 > ema50:
        if rsi14 < 50:
            buy_score += 0.3
            reasons.append(f"EMA20 > EMA50 with RSI < 50")
    elif ema20 < ema50:
        if rsi14 > 50:
            sell_score += 0.3
            reasons.append(f"EMA20 < EMA50 with RSI > 50")
    
    # MACD signals
    if macd_histogram is not None:
        if macd_histogram > 0:
            buy_score += 0.2
            reasons.append(f"MACD histogram positive")
        elif macd_histogram < 0:
            sell_score += 0.2
            reasons.append(f"MACD histogram negative")
    
    # Determine signal
    if buy_score > sell_score and buy_score >= 0.5:
        return 'BUY', min(buy_score, 1.0), '; '.join(reasons)
    elif sell_score > buy_score and sell_score >= 0.5:
        return 'SELL', min(sell_score, 1.0), '; '.join(reasons)
    else:
        return 'HOLD', max(buy_score, sell_score), 'No strong signal'


def process_symbol(symbol):
    """
    Process a symbol and generate signal if appropriate.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Signal dictionary or None
    """
    try:
        # Get latest features
        features = get_latest_features(symbol)
        
        if not features:
            logger.debug(f"No features available for {symbol}")
            return None
        
        # Generate signal
        signal_type, strength, reason = generate_signal(symbol, features)
        
        # Only store if not HOLD or if significant strength
        if signal_type != 'HOLD' or strength > 0.3:
            timestamp = features['timestamp']
            
            # Create features snapshot
            features_dict = {
                'ema20': float(features['ema20']) if features['ema20'] else None,
                'ema50': float(features['ema50']) if features['ema50'] else None,
                'rsi14': float(features['rsi14']) if features['rsi14'] else None,
                'macd': float(features['macd']) if features['macd'] else None,
                'macd_signal': float(features['macd_signal']) if features['macd_signal'] else None,
                'macd_histogram': float(features['macd_histogram']) if features['macd_histogram'] else None,
            }
            
            # Insert signal
            signal_id = insert_signal(symbol, timestamp, signal_type, strength, reason, features_dict)
            
            logger.info(f"{symbol}: {signal_type} signal (strength={strength:.2f}) - {reason}")
            
            return {
                'id': signal_id,
                'symbol': symbol,
                'signal_type': signal_type,
                'strength': strength,
                'reason': reason
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        return None


def run_continuous_generation(symbols, config):
    """
    Continuously generate signals.
    
    Args:
        symbols: List of symbols to process
        config: Sources configuration
    """
    logger.info("Starting continuous signal generation...")
    
    interval = config['signals'].get('generation_interval_sec', 60)
    
    while True:
        try:
            for symbol in symbols:
                signal = process_symbol(symbol)
                if signal and signal['signal_type'] != 'HOLD':
                    logger.info(f"Generated {signal['signal_type']} signal for {symbol}")
            
            logger.info(f"Sleeping for {interval} seconds...")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("Shutting down signal engine...")
            break
        except Exception as e:
            logger.error(f"Error in continuous generation: {e}")
            time.sleep(10)


def main():
    """Main entry point."""
    logger.info("Starting Signal Engine...")
    
    # Load configuration
    symbols = load_symbols()
    config = load_sources_config()
    
    logger.info(f"Processing symbols: {symbols}")
    
    # Start continuous generation
    run_continuous_generation(symbols, config)


if __name__ == '__main__':
    main()
