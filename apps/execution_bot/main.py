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
