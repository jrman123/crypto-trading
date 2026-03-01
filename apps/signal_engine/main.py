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
Signal Engine Service
Reads features and generates trade signals (BUY/SELL/HOLD)
"""
import sys
import os
import time
import json
from datetime import datetime, timedelta

# Add parent directory to path to import common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import (
    db, setup_logging, get_symbols_config, get_risk_config,
    get_current_timestamp, calculate_stop_loss, calculate_take_profit
)


class SignalEngine:
    """Generates trading signals from features"""
    
    def __init__(self):
        self.logger = setup_logging('signal_engine')
        self.symbols_config = get_symbols_config()
        self.risk_config = get_risk_config()
        
    def fetch_latest_features(self, symbol, timeframe):
        """Fetch latest features for analysis"""
        try:
            features = db.get_latest_features(symbol, timeframe, limit=1)
            if not features:
                self.logger.warning("No features found", symbol=symbol, timeframe=timeframe)
                return None
            return features[0]
        except Exception as e:
            self.logger.error("Failed to fetch features", symbol=symbol, error=str(e))
            return None
    
    def analyze_trend(self, features):
        """Analyze trend using EMAs"""
        ema_9 = features.get('ema_9')
        ema_21 = features.get('ema_21')
        ema_50 = features.get('ema_50')
        
        if not all([ema_9, ema_21, ema_50]):
            return 'UNKNOWN', 0
        
        # Bullish: short EMAs above long EMAs
        if ema_9 > ema_21 > ema_50:
            return 'BULLISH', 80
        # Bearish: short EMAs below long EMAs
        elif ema_9 < ema_21 < ema_50:
            return 'BEARISH', 80
        # Mixed
        else:
            return 'NEUTRAL', 50
    
    def analyze_momentum(self, features):
        """Analyze momentum using RSI and MACD"""
        rsi = features.get('rsi_14')
        macd = features.get('macd')
        macd_signal = features.get('macd_signal')
        
        strategy = self.risk_config.get('strategy', {})
        rsi_oversold = strategy.get('rsi_oversold', 30)
        rsi_overbought = strategy.get('rsi_overbought', 70)
        
        signals = []
        confidence = 50
        
        if rsi:
            if rsi < rsi_oversold:
                signals.append('OVERSOLD')
                confidence += 15
            elif rsi > rsi_overbought:
                signals.append('OVERBOUGHT')
                confidence += 15
        
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                signals.append('MACD_BULLISH')
                confidence += 10
            else:
                signals.append('MACD_BEARISH')
                confidence -= 10
        
        return signals, min(confidence, 100)
    
    def generate_signal(self, symbol, timeframe, features):
        """Generate a trading signal based on features"""
        try:
            # Analyze trend and momentum
            trend, trend_confidence = self.analyze_trend(features)
            momentum_signals, momentum_confidence = self.analyze_momentum(features)
            
            # Combine signals
            signal_type = 'HOLD'
            confidence = 50
            reason_parts = []
            
            # Determine signal type
            if trend == 'BULLISH' and 'OVERSOLD' in momentum_signals:
                signal_type = 'BUY'
                confidence = (trend_confidence + momentum_confidence) / 2
                reason_parts.append(f"Bullish trend with oversold RSI")
            elif trend == 'BULLISH' and 'MACD_BULLISH' in momentum_signals:
                signal_type = 'BUY'
                confidence = (trend_confidence + momentum_confidence) / 2
                reason_parts.append(f"Bullish trend with MACD crossover")
            elif trend == 'BEARISH' and 'OVERBOUGHT' in momentum_signals:
                signal_type = 'SELL'
                confidence = (trend_confidence + momentum_confidence) / 2
                reason_parts.append(f"Bearish trend with overbought RSI")
            elif trend == 'BEARISH' and 'MACD_BEARISH' in momentum_signals:
                signal_type = 'SELL'
                confidence = (trend_confidence + momentum_confidence) / 2
                reason_parts.append(f"Bearish trend with MACD crossover")
            else:
                reason_parts.append(f"No clear signal: {trend} trend")
            
            # Add momentum details
            if momentum_signals:
                reason_parts.append(f"Momentum: {', '.join(momentum_signals)}")
            
            reason = '; '.join(reason_parts)
            
            # Check if confidence meets minimum threshold
            min_confidence = self.risk_config.get('risk_limits', {}).get('min_confidence', 70)
            
            if confidence < min_confidence and signal_type != 'HOLD':
                self.logger.info("Signal below confidence threshold",
                               symbol=symbol, signal=signal_type, 
                               confidence=confidence, threshold=min_confidence)
                signal_type = 'HOLD'
                reason = f"Confidence too low ({confidence:.1f}% < {min_confidence}%)"
            
            return {
                'signal_type': signal_type,
                'confidence': confidence,
                'reason': reason,
                'trend': trend,
                'momentum': momentum_signals
            }
            
        except Exception as e:
            self.logger.error("Failed to generate signal", symbol=symbol, error=str(e))
            return None
    
    def create_signal_entry(self, symbol, timeframe, features, signal_data):
        """Create a signal entry in the database"""
        try:
            # Get current price (use EMA as proxy if available)
            current_price = features.get('ema_9') or features.get('bb_middle')
            if not current_price:
                self.logger.error("Cannot determine current price", symbol=symbol)
                return None
            
            # Calculate risk parameters
            risk_limits = self.risk_config.get('risk_limits', {})
            stop_pct = risk_limits.get('default_stop_loss_pct', 2.0)
            tp_pct = risk_limits.get('default_take_profit_pct', 4.0)
            max_position = risk_limits.get('max_position_usd', 100.0)
            
            # Calculate stop loss and take profit
            stop_loss = calculate_stop_loss(current_price, signal_data['signal_type'], stop_pct)
            take_profit = calculate_take_profit(current_price, signal_data['signal_type'], tp_pct)
            
            # Create indicators snapshot
            indicators_snapshot = {
                'ema_9': features.get('ema_9'),
                'ema_21': features.get('ema_21'),
                'ema_50': features.get('ema_50'),
                'rsi_14': features.get('rsi_14'),
                'macd': features.get('macd'),
                'macd_signal': features.get('macd_signal'),
                'trend': signal_data.get('trend'),
                'momentum': signal_data.get('momentum')
            }
            
            # Insert signal
            signal_id = db.insert_signal(
                symbol=symbol,
                signal_type=signal_data['signal_type'],
                confidence=signal_data['confidence'],
                timestamp=features['timestamp'],
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size_usd=max_position,
                strategy='ema_rsi_macd',
                timeframe=timeframe,
                reason=signal_data['reason'],
                indicators_snapshot=json.dumps(indicators_snapshot)
            )
            
            self.logger.info("Signal created",
                           symbol=symbol,
                           signal_type=signal_data['signal_type'],
                           confidence=signal_data['confidence'],
                           signal_id=signal_id)
            
            return signal_id
            
        except Exception as e:
            self.logger.error("Failed to create signal entry", symbol=symbol, error=str(e))
            return None
    
    def process_symbol_timeframe(self, symbol, timeframe):
        """Process signal generation for a symbol and timeframe"""
        try:
            # Check for recent signals to avoid duplicates
            recent_signals = db.get_latest_signals(symbol, limit=1)
            if recent_signals:
                last_signal = recent_signals[0]
                cooldown_minutes = self.risk_config.get('strategy', {}).get('signal_cooldown_minutes', 15)
                time_since_last = datetime.now() - last_signal['timestamp']
                if time_since_last.total_seconds() < cooldown_minutes * 60:
                    self.logger.debug("Signal cooldown active", symbol=symbol)
                    return False
            
            # Fetch latest features
            features = self.fetch_latest_features(symbol, timeframe)
            if not features:
                return False
            
            # Generate signal
            signal_data = self.generate_signal(symbol, timeframe, features)
            if not signal_data:
                return False
            
            # Only store non-HOLD signals
            if signal_data['signal_type'] != 'HOLD':
                signal_id = self.create_signal_entry(symbol, timeframe, features, signal_data)
                
                db.log_audit('signal_engine', 'generate_signal', 'signal', signal_id,
                           {'symbol': symbol, 'signal_type': signal_data['signal_type']},
                           'success')
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to process signal", 
                            symbol=symbol, timeframe=timeframe, error=str(e))
            db.log_audit('signal_engine', 'generate_signal', 'signal', None,
                        {'symbol': symbol, 'timeframe': timeframe}, 'failure', str(e))
            return False
    
    def run_once(self):
        """Run one signal generation cycle"""
        self.logger.info("Starting signal generation cycle")
        
        for symbol_config in self.symbols_config['symbols']:
            symbol = symbol_config['symbol']
            # Use primary timeframe for signals
            timeframe = symbol_config.get('timeframes', ['1h'])[0]
            
            self.process_symbol_timeframe(symbol, timeframe)
            time.sleep(0.1)
        
        self.logger.info("Signal generation cycle complete")
    
    def run_continuous(self, interval_seconds=120):
        """Run signal generation continuously"""
        self.logger.info(f"Starting continuous signal generation (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                self.logger.info("Stopping signal engine")
                break
            except Exception as e:
                self.logger.error("Unexpected error in signal engine loop", error=str(e))
                time.sleep(10)


if __name__ == '__main__':
    engine = SignalEngine()
    
    # Get update interval from environment
    interval = int(os.getenv('SIGNAL_ENGINE_INTERVAL_SECONDS', '120'))
    
    # Run continuously
    engine.run_continuous(interval_seconds=interval)
