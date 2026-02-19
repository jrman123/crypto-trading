"""
Signal Engine - Generates trade signals based on technical indicators
"""
import os
import sys
import time
import logging
import yaml

# Add parent directory to path for imports
sys.path.insert(0, '/app/apps')
from common.db import db
from common.risk import get_risk_manager
from common.indicators import get_previous_macd_hist

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalEngine:
    """Generates trade signals based on rule-based logic"""
    
    def __init__(self, symbols_config_path: str = '/app/configs/symbols.yaml'):
        self.config = self._load_config(symbols_config_path)
        self.risk_manager = get_risk_manager()
        
    def _load_config(self, path: str) -> dict:
        """Load symbols configuration"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Failed to load symbols config: {e}")
            return {'timeframe': '1h', 'symbols': ['BTCUSDT']}
    
    def generate_signal(self, symbol: str, timeframe: str) -> dict:
        """
        Generate trade signal for a symbol
        
        Signal Logic:
        BUY if:
          - EMA20 > EMA50 (uptrend)
          - RSI > 50 (momentum)
          - MACD histogram rising (acceleration)
        
        SELL if:
          - EMA20 < EMA50 (downtrend)
          - RSI < 50 (weakness)
          - MACD histogram falling (deceleration)
        
        HOLD otherwise
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Signal dict
        """
        # Get latest features
        features = db.get_latest_features(symbol, timeframe, limit=1)
        
        if not features:
            logger.warning(f"No features available for {symbol}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'side': 'HOLD',
                'confidence': 0,
                'reason': 'No feature data available'
            }
        
        feat = features[0]
        
        # Check if all required indicators are available
        if not all([
            feat['ema20'], feat['ema50'], 
            feat['rsi14'], feat['macd_hist']
        ]):
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'side': 'HOLD',
                'confidence': 0,
                'reason': 'Incomplete indicator data'
            }
        
        # Get current price for entry
        latest_price = db.get_latest_prices(symbol, timeframe, limit=1)
        if not latest_price:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'side': 'HOLD',
                'confidence': 0,
                'reason': 'No price data available'
            }
        
        entry_price = float(latest_price[0]['close'])
        ts = latest_price[0]['ts']
        
        # Extract indicators
        ema20 = float(feat['ema20'])
        ema50 = float(feat['ema50'])
        rsi = float(feat['rsi14'])
        macd_hist = float(feat['macd_hist'])
        
        # Get previous MACD histogram for trend detection
        price_data = db.get_latest_prices(symbol, timeframe, limit=50)
        price_data.reverse()
        prev_macd_hist = get_previous_macd_hist(price_data)
        macd_rising = prev_macd_hist is not None and macd_hist > prev_macd_hist
        macd_falling = prev_macd_hist is not None and macd_hist < prev_macd_hist
        
        # Initialize signal
        side = 'HOLD'
        confidence = 0
        reasons = []
        
        # BUY conditions
        buy_conditions = {
            'ema_uptrend': ema20 > ema50,
            'rsi_bullish': rsi > 50,
            'macd_rising': macd_rising
        }
        
        # SELL conditions  
        sell_conditions = {
            'ema_downtrend': ema20 < ema50,
            'rsi_bearish': rsi < 50,
            'macd_falling': macd_falling
        }
        
        # Calculate BUY signal
        buy_score = sum(buy_conditions.values())
        if buy_score >= 2:  # At least 2 conditions met
            side = 'BUY'
            confidence = (buy_score / 3) * 100  # 66% or 100%
            reasons = [k for k, v in buy_conditions.items() if v]
        
        # Calculate SELL signal
        sell_score = sum(sell_conditions.values())
        if sell_score >= 2:  # At least 2 conditions met
            # SELL overrides BUY if stronger
            if sell_score > buy_score:
                side = 'SELL'
                confidence = (sell_score / 3) * 100
                reasons = [k for k, v in sell_conditions.items() if v]
        
        # Calculate stop loss and take profit
        stop = self.risk_manager.calculate_stop_loss(entry_price, side)
        take_profit = self.risk_manager.calculate_take_profit(entry_price, side)
        
        reason = f"{side}: {', '.join(reasons)}" if reasons else 'HOLD: No clear signal'
        
        signal = {
            'symbol': symbol,
            'timeframe': timeframe,
            'ts': ts,
            'side': side,
            'confidence': confidence,
            'entry': entry_price if side != 'HOLD' else None,
            'stop': stop if side != 'HOLD' else None,
            'take_profit': take_profit if side != 'HOLD' else None,
            'reason': reason
        }
        
        logger.info(
            f"Signal: {symbol} {side} confidence={confidence:.1f}% "
            f"entry=${entry_price:.2f} - {reason}"
        )
        
        return signal
    
    def run_once(self):
        """Generate signals for all configured symbols"""
        symbols = self.config.get('symbols', ['BTCUSDT'])
        timeframe = self.config.get('timeframe', '1h')
        
        for symbol in symbols:
            try:
                signal = self.generate_signal(symbol, timeframe)
                
                # Store signal in database
                if signal['side'] != 'HOLD' or signal['confidence'] > 0:
                    db.insert_signal(
                        symbol=signal['symbol'],
                        timeframe=signal['timeframe'],
                        ts=signal['ts'],
                        side=signal['side'],
                        confidence=signal['confidence'],
                        entry=signal.get('entry'),
                        stop=signal.get('stop'),
                        take_profit=signal.get('take_profit'),
                        reason=signal['reason']
                    )
                    
            except Exception as e:
                logger.error(f"Failed to generate signal for {symbol}: {e}")
        
        logger.info("Signal generation cycle complete")


def main():
    """Main entry point"""
    logger.info("=== Signal Engine Starting ===")
    
    # Connect to database
    db.connect()
    
    # Initialize engine
    engine = SignalEngine()
    
    # Get interval from environment
    interval_seconds = int(os.getenv('SIGNALS_EVERY', 1800))  # Default 30 min
    
    try:
        while True:
            try:
                engine.run_once()
            except Exception as e:
                logger.error(f"Signal generation error: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down signal engine...")
    finally:
        db.disconnect()


if __name__ == '__main__':
    main()
