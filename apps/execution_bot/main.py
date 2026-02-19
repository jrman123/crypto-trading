"""
Execution Bot
Paper trading bot that executes signals, respects TRADE_PAUSE flag.
"""
import os
import sys
import time
import logging
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.db import (
    execute_query, insert_order, upsert_position, 
    get_position, get_system_flag, get_latest_prices
)
from common.risk import (
    load_risk_config, calculate_position_size,
    check_signal_strength, check_daily_trade_limit
)
from common.exchange_paper import PaperExchange

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global paper exchange instance
paper_exchange = None


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
            'execution': {
                'check_interval_sec': 30,
                'paper_trading': True,
                'initial_balance': 10000
            }
        }


def initialize_paper_exchange(config):
    """Initialize paper trading exchange."""
    global paper_exchange
    
    initial_balance = config['execution'].get('initial_balance', 10000)
    paper_exchange = PaperExchange(initial_balance)
    logger.info(f"Initialized paper exchange with balance: ${initial_balance}")


def get_unprocessed_signals():
    """
    Get signals that haven't been executed yet.
    
    Returns:
        List of unprocessed signals
    """
    query = """
        SELECT s.* FROM trade_signals s
        LEFT JOIN orders o ON s.id = o.signal_id
        WHERE o.id IS NULL
        AND s.signal_type IN ('BUY', 'SELL')
        ORDER BY s.created_at DESC
        LIMIT 10
    """
    return execute_query(query)


def get_current_price(symbol):
    """
    Get current price for symbol.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Current price or None
    """
    prices = get_latest_prices(symbol, limit=1)
    if prices:
        return float(prices[0]['close'])
    return None


def execute_signal(signal, risk_config):
    """
    Execute a trading signal.
    
    Args:
        signal: Signal dictionary
        risk_config: Risk configuration
        
    Returns:
        True if executed, False otherwise
    """
    global paper_exchange
    
    try:
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        strength = float(signal['strength'])
        signal_id = signal['id']
        
        # Check signal strength
        if not check_signal_strength(strength, risk_config):
            logger.info(f"Signal {signal_id} strength too low: {strength}")
            # Record as rejected
            insert_order(symbol, 'MARKET', signal_type, 0, 0, 'REJECTED', signal_id)
            return False
        
        # Get current price
        current_price = get_current_price(symbol)
        if not current_price:
            logger.warning(f"No price available for {symbol}")
            return False
        
        # Calculate position size
        balance = paper_exchange.get_balance()
        position_size = calculate_position_size(balance, current_price, risk_config)
        
        if position_size <= 0:
            logger.warning(f"Invalid position size calculated: {position_size}")
            return False
        
        # Execute based on signal type
        if signal_type == 'BUY':
            # Check if we already have a position
            existing_pos = paper_exchange.get_position(symbol)
            if existing_pos > 0:
                logger.info(f"Already have position in {symbol}, skipping BUY")
                return False
            
            # Place buy order
            order_result = paper_exchange.place_market_order(
                symbol, 'BUY', position_size, current_price
            )
            
        elif signal_type == 'SELL':
            # Check if we have a position to sell
            existing_pos = paper_exchange.get_position(symbol)
            if existing_pos <= 0:
                logger.info(f"No position in {symbol} to sell, skipping")
                return False
            
            # Sell entire position
            order_result = paper_exchange.place_market_order(
                symbol, 'SELL', existing_pos, current_price
            )
        else:
            return False
        
        # Record order in database
        order_id = insert_order(
            symbol=symbol,
            order_type='MARKET',
            side=signal_type,
            quantity=order_result['quantity'],
            price=current_price,
            status=order_result['status'],
            signal_id=signal_id
        )
        
        # Update position in database if filled
        if order_result['status'] == 'FILLED':
            final_position = paper_exchange.get_position(symbol)
            if final_position > 0:
                upsert_position(
                    symbol=symbol,
                    quantity=final_position,
                    avg_entry_price=current_price,
                    current_price=current_price,
                    unrealized_pnl=0
                )
            else:
                # Position closed, can delete or set to 0
                upsert_position(
                    symbol=symbol,
                    quantity=0,
                    avg_entry_price=0,
                    current_price=current_price,
                    unrealized_pnl=0
                )
            
            logger.info(
                f"Executed {signal_type} order for {symbol}: "
                f"{order_result['quantity']} @ {current_price} (Order ID: {order_id})"
            )
            return True
        else:
            logger.warning(f"Order not filled: {order_result.get('reason', 'Unknown')}")
            return False
        
    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        return False


def get_trades_today():
    """Get number of trades executed today."""
    query = """
        SELECT COUNT(*) as count FROM orders
        WHERE status = 'FILLED'
        AND DATE(executed_at) = CURRENT_DATE
    """
    result = execute_query(query)
    return result[0]['count'] if result else 0


def run_continuous_execution(symbols, config):
    """
    Continuously check for and execute signals.
    
    Args:
        symbols: List of symbols to process
        config: Sources configuration
    """
    logger.info("Starting continuous execution...")
    
    interval = config['execution'].get('check_interval_sec', 30)
    risk_config = load_risk_config()
    
    while True:
        try:
            # Check TRADE_PAUSE flag
            trade_pause = get_system_flag('TRADE_PAUSE')
            
            if trade_pause:
                logger.warning("Trading is PAUSED. Skipping execution cycle.")
                time.sleep(interval)
                continue
            
            # Check daily trade limit
            trades_today = get_trades_today()
            if not check_daily_trade_limit(trades_today, risk_config):
                logger.warning(f"Daily trade limit reached: {trades_today} trades")
                time.sleep(interval)
                continue
            
            # Get unprocessed signals
            signals = get_unprocessed_signals()
            
            if signals:
                logger.info(f"Found {len(signals)} unprocessed signals")
                
                for signal in signals:
                    execute_signal(signal, risk_config)
                    time.sleep(1)  # Small delay between executions
            else:
                logger.debug("No unprocessed signals")
            
            # Log portfolio status
            summary = paper_exchange.get_summary()
            logger.info(f"Portfolio: Balance=${summary['balance']:.2f}, Positions={summary['positions']}")
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("Shutting down execution bot...")
            break
        except Exception as e:
            logger.error(f"Error in continuous execution: {e}")
            time.sleep(10)


def main():
    """Main entry point."""
    logger.info("Starting Execution Bot (Paper Trading)...")
    
    # Load configuration
    symbols = load_symbols()
    config = load_sources_config()
    
    logger.info(f"Trading symbols: {symbols}")
    
    # Initialize paper exchange
    initialize_paper_exchange(config)
    
    # Start continuous execution
    run_continuous_execution(symbols, config)


if __name__ == '__main__':
    main()
