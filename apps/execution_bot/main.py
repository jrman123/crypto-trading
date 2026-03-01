"""
Execution Bot - Executes trades based on signals in PAPER mode
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
from common.exchange_paper import PaperExchange

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExecutionBot:
    """Executes trades based on signals with risk management"""
    
    def __init__(self, symbols_config_path: str = '/app/configs/symbols.yaml'):
        self.config = self._load_config(symbols_config_path)
        self.risk_manager = get_risk_manager()
        self.exchange = PaperExchange(db)
        self.execution_mode = os.getenv('EXECUTION_MODE', 'PAPER')
        
    def _load_config(self, path: str) -> dict:
        """Load symbols configuration"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Failed to load symbols config: {e}")
            return {'timeframe': '1h', 'symbols': ['BTCUSDT']}
    
    def execute_signal(self, symbol: str, timeframe: str):
        """
        Execute trade based on latest signal
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
        """
        # Check if trading is paused
        if db.is_trading_paused():
            reason = db.get_system_flag('TRADE_PAUSE_REASON') or 'Unknown'
            logger.warning(f"Trading paused: {reason}")
            return
        
        # Get latest signal
        signal = db.get_latest_signal(symbol)
        
        if not signal:
            logger.info(f"No signal available for {symbol}")
            return
        
        # Only execute BUY/SELL signals, not HOLD
        if signal['side'] == 'HOLD':
            logger.info(f"Signal is HOLD for {symbol}, skipping execution")
            return
        
        # Validate signal confidence
        confidence = float(signal['confidence'])
        
        # Get current price
        current_price = self.exchange.get_current_price(symbol, timeframe)
        if not current_price:
            logger.error(f"Cannot get current price for {symbol}")
            return
        
        # Calculate position size
        account_balance = self.exchange.get_account_balance()
        qty = self.risk_manager.calculate_position_size(
            entry_price=current_price,
            confidence=confidence,
            account_balance=account_balance
        )
        
        # Validate trade
        is_valid, validation_reason = self.risk_manager.validate_trade(
            confidence=confidence,
            qty=qty,
            trading_paused=False  # Already checked above
        )
        
        if not is_valid:
            logger.warning(f"Trade validation failed: {validation_reason}")
            return
        
        # Execute trade
        logger.info(
            f"Executing {signal['side']} {symbol}: "
            f"qty={qty:.8f} @ ${current_price:.2f} "
            f"(confidence={confidence:.1f}%)"
        )
        
        try:
            # Execute on paper exchange
            execution_result = self.exchange.execute_market_order(
                symbol=symbol,
                side=signal['side'],
                qty=qty,
                current_price=current_price
            )
            
            # Record order in database
            order_id = db.insert_order(
                signal_id=signal['id'],
                symbol=symbol,
                side=signal['side'],
                qty=qty,
                price=current_price,
                mode=self.execution_mode
            )
            
            # Update order status to FILLED
            if order_id:
                db.update_order_status(order_id, 'FILLED')
            
            logger.info(
                f"✓ Order executed: {symbol} {signal['side']} "
                f"{qty:.8f} @ ${current_price:.2f} "
                f"[Order ID: {order_id}]"
            )
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
    
    def run_once(self):
        """Execute trades for all configured symbols"""
        symbols = self.config.get('symbols', ['BTCUSDT'])
        timeframe = self.config.get('timeframe', '1h')
        
        logger.info(f"=== Execution cycle starting (mode={self.execution_mode}) ===")
        
        for symbol in symbols:
            try:
                self.execute_signal(symbol, timeframe)
            except Exception as e:
                logger.error(f"Failed to execute for {symbol}: {e}")
        
        logger.info("Execution cycle complete")


def main():
    """Main entry point"""
    logger.info("=== Execution Bot Starting ===")
    
    # Connect to database
    db.connect()
    
    # Initialize bot
    bot = ExecutionBot()
    
    # Get interval from environment
    interval_seconds = int(os.getenv('EXECUTE_EVERY', 3600))  # Default 1 hour
    
    logger.info(f"Execution mode: {bot.execution_mode}")
    
    try:
        while True:
            try:
                bot.run_once()
            except Exception as e:
                logger.error(f"Execution error: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down execution bot...")
    finally:
        db.disconnect()


if __name__ == '__main__':
    main()
Execution Bot Service
Reads trade signals and executes trades (paper or live)
Respects system flags like TRADE_PAUSE
"""
import sys
import os
import time
import json
import uuid
from datetime import datetime
import ccxt

# Add parent directory to path to import common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import (
    db, setup_logging, get_symbols_config, get_risk_config,
    get_current_timestamp, is_paper_trading
)


class ExecutionBot:
    """Executes trades based on signals"""
    
    def __init__(self):
        self.logger = setup_logging('execution_bot')
        self.symbols_config = get_symbols_config()
        self.risk_config = get_risk_config()
        self.exchange = self._setup_exchange()
        self.is_paper = is_paper_trading()
        
        self.logger.info(f"Execution bot initialized",
                        mode='PAPER' if self.is_paper else 'LIVE')
        
    def _setup_exchange(self):
        """Setup exchange connection"""
        if is_paper_trading():
            # For paper trading, we still setup the exchange but won't execute
            self.logger.info("Paper trading mode - orders will be simulated")
        
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
        
        return exchange
    
    def check_safety_flags(self):
        """Check system flags for trading restrictions"""
        try:
            # Check TRADE_PAUSE flag
            trade_pause = db.get_system_flag('TRADE_PAUSE')
            if trade_pause:
                self.logger.warning("Trading paused by system flag")
                return False
            
            return True
        except Exception as e:
            self.logger.error("Failed to check safety flags", error=str(e))
            # Fail safe - don't trade if we can't check flags
            return False
    
    def check_risk_limits(self):
        """Check if we're within risk limits"""
        try:
            risk_limits = self.risk_config.get('risk_limits', {})
            max_open_positions = risk_limits.get('max_open_positions', 3)
            
            # Count open positions
            # In a full implementation, query positions table
            # For now, we'll allow trading
            
            return True
        except Exception as e:
            self.logger.error("Failed to check risk limits", error=str(e))
            return False
    
    def get_pending_signals(self):
        """Get signals that haven't been executed yet"""
        try:
            # Get recent signals
            signals = db.get_latest_signals(limit=10)
            
            # Filter for signals that meet confidence threshold
            risk_limits = self.risk_config.get('risk_limits', {})
            min_confidence = risk_limits.get('min_confidence', 70)
            
            pending = []
            for signal in signals:
                # Skip HOLD signals
                if signal['signal_type'] == 'HOLD':
                    continue
                
                # Check confidence
                if signal['confidence'] < min_confidence:
                    continue
                
                # Check if already executed (simplified check)
                # In full implementation, check orders table for this signal_id
                pending.append(signal)
            
            return pending[:1]  # Only process one signal at a time
            
        except Exception as e:
            self.logger.error("Failed to get pending signals", error=str(e))
            return []
    
    def execute_paper_order(self, signal):
        """Execute a paper (simulated) order"""
        try:
            order_id = f"PAPER_{uuid.uuid4().hex[:12]}"
            
            # Simulate order placement
            order_data = {
                'order_id': order_id,
                'signal_id': signal['id'],
                'symbol': signal['symbol'],
                'side': 'BUY' if signal['signal_type'] == 'BUY' else 'SELL',
                'order_type': 'MARKET',
                'status': 'FILLED',
                'quantity': signal['position_size_usd'] / signal['entry_price'],
                'price': signal['entry_price'],
                'is_paper': True,
                'placed_at': datetime.now()
            }
            
            # Store in database
            db_order_id = db.insert_order(order_data)
            
            # Update as filled immediately (paper order)
            db.update_order_status(
                order_id,
                'FILLED',
                filled_quantity=order_data['quantity'],
                avg_fill_price=signal['entry_price']
            )
            
            self.logger.info("Paper order executed",
                           order_id=order_id,
                           symbol=signal['symbol'],
                           side=order_data['side'],
                           price=signal['entry_price'],
                           quantity=order_data['quantity'])
            
            db.log_audit('execution_bot', 'execute_order', 'order', db_order_id,
                        {'order_id': order_id, 'type': 'paper'}, 'success')
            
            return order_id
            
        except Exception as e:
            self.logger.error("Failed to execute paper order", error=str(e))
            db.log_audit('execution_bot', 'execute_order', 'order', None,
                        {'signal_id': signal['id'], 'type': 'paper'}, 'failure', str(e))
            return None
    
    def execute_live_order(self, signal):
        """Execute a live order on the exchange"""
        try:
            # This is a placeholder for live trading
            # In production, this would use the exchange API
            
            symbol = signal['symbol']
            side = 'buy' if signal['signal_type'] == 'BUY' else 'sell'
            quantity = signal['position_size_usd'] / signal['entry_price']
            
            # Example: Market order
            # order = self.exchange.create_market_order(symbol, side, quantity)
            
            self.logger.warning("Live trading not fully implemented - would execute:",
                              symbol=symbol, side=side, quantity=quantity)
            
            # For safety, we'll treat as paper order for now
            return self.execute_paper_order(signal)
            
        except Exception as e:
            self.logger.error("Failed to execute live order", error=str(e))
            db.log_audit('execution_bot', 'execute_order', 'order', None,
                        {'signal_id': signal['id'], 'type': 'live'}, 'failure', str(e))
            return None
    
    def execute_signal(self, signal):
        """Execute a trade based on a signal"""
        try:
            self.logger.info("Processing signal",
                           signal_id=signal['id'],
                           symbol=signal['symbol'],
                           signal_type=signal['signal_type'],
                           confidence=signal['confidence'])
            
            # Execute based on mode
            if self.is_paper:
                return self.execute_paper_order(signal)
            else:
                return self.execute_live_order(signal)
                
        except Exception as e:
            self.logger.error("Failed to execute signal", 
                            signal_id=signal['id'], error=str(e))
            return None
    
    def run_once(self):
        """Run one execution cycle"""
        self.logger.info("Starting execution cycle")
        
        # Check safety flags
        if not self.check_safety_flags():
            self.logger.warning("Trading halted - safety flags active")
            return
        
        # Check risk limits
        if not self.check_risk_limits():
            self.logger.warning("Trading halted - risk limits exceeded")
            return
        
        # Get pending signals
        signals = self.get_pending_signals()
        
        if not signals:
            self.logger.debug("No pending signals to execute")
            return
        
        # Execute signals
        for signal in signals:
            self.execute_signal(signal)
            time.sleep(1)  # Small delay between orders
        
        self.logger.info("Execution cycle complete")
    
    def run_continuous(self, interval_seconds=30):
        """Run execution continuously"""
        self.logger.info(f"Starting continuous execution (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                self.logger.info("Stopping execution bot")
                break
            except Exception as e:
                self.logger.error("Unexpected error in execution loop", error=str(e))
                time.sleep(10)


if __name__ == '__main__':
    bot = ExecutionBot()
    
    # Get update interval from environment
    interval = int(os.getenv('EXECUTION_BOT_INTERVAL_SECONDS', '30'))
    
    # Run continuously
    bot.run_continuous(interval_seconds=interval)
