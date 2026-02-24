"""
Common utilities module
Shared utilities for all services
"""
import os
import time
import structlog
from datetime import datetime, timezone
from functools import wraps


def setup_logging(service_name):
    """Setup structured logging for a service"""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name)
    return logger


def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60, exceptions=(Exception,)):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = structlog.get_logger()
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    logger.warning(
                        f"Attempt {retries}/{max_retries} failed, retrying in {delay}s",
                        error=str(e),
                        function=func.__name__
                    )
                    time.sleep(delay)
        return wrapper
    return decorator


def get_current_timestamp():
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


def parse_timeframe_to_seconds(timeframe):
    """Convert timeframe string to seconds"""
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        raise ValueError(f"Unknown timeframe unit: {unit}")


def format_price(price, decimals=8):
    """Format price with proper decimals"""
    return round(float(price), decimals)


def calculate_stop_loss(entry_price, side, stop_pct):
    """Calculate stop loss price"""
    if side == 'BUY' or side == 'LONG':
        return entry_price * (1 - stop_pct / 100)
    else:  # SELL or SHORT
        return entry_price * (1 + stop_pct / 100)


def calculate_take_profit(entry_price, side, tp_pct):
    """Calculate take profit price"""
    if side == 'BUY' or side == 'LONG':
        return entry_price * (1 + tp_pct / 100)
    else:  # SELL or SHORT
        return entry_price * (1 - tp_pct / 100)


def is_paper_trading():
    """Check if running in paper trading mode"""
    return os.getenv('TRADING_MODE', 'paper').lower() == 'paper'
