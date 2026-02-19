"""Database connection and utility functions."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


def get_db_config():
    """Get database configuration from environment."""
    return {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'trading'),
        'user': os.getenv('DB_USER', 'trader'),
        'password': os.getenv('DB_PASSWORD', 'trader123'),
    }


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        config = get_db_config()
        conn = psycopg2.connect(**config)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally fetch results."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()
            return None


def insert_price(symbol, timestamp, open_price, high, low, close, volume):
    """Insert price data."""
    query = """
        INSERT INTO prices (symbol, timestamp, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timestamp) DO UPDATE
        SET open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    execute_query(query, (symbol, timestamp, open_price, high, low, close, volume), fetch=False)


def get_latest_prices(symbol, limit=100):
    """Get latest prices for a symbol."""
    query = """
        SELECT * FROM prices
        WHERE symbol = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """
    return execute_query(query, (symbol, limit))


def insert_feature(symbol, timestamp, ema20=None, ema50=None, rsi14=None, 
                   macd=None, macd_signal=None, macd_histogram=None):
    """Insert feature data."""
    query = """
        INSERT INTO features (symbol, timestamp, ema20, ema50, rsi14, macd, macd_signal, macd_histogram)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timestamp) DO UPDATE
        SET ema20 = EXCLUDED.ema20,
            ema50 = EXCLUDED.ema50,
            rsi14 = EXCLUDED.rsi14,
            macd = EXCLUDED.macd,
            macd_signal = EXCLUDED.macd_signal,
            macd_histogram = EXCLUDED.macd_histogram
    """
    execute_query(query, (symbol, timestamp, ema20, ema50, rsi14, macd, macd_signal, macd_histogram), fetch=False)


def insert_signal(symbol, timestamp, signal_type, strength, reason, features_dict):
    """Insert trade signal."""
    import json
    query = """
        INSERT INTO trade_signals (symbol, timestamp, signal_type, strength, reason, features)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_query(query, (symbol, timestamp, signal_type, strength, reason, json.dumps(features_dict)))
    return result[0]['id'] if result else None


def insert_order(symbol, order_type, side, quantity, price, status, signal_id=None):
    """Insert order."""
    query = """
        INSERT INTO orders (symbol, order_type, side, quantity, price, status, signal_id, executed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
    """
    result = execute_query(query, (symbol, order_type, side, quantity, price, status, signal_id))
    return result[0]['id'] if result else None


def upsert_position(symbol, quantity, avg_entry_price, current_price=None, unrealized_pnl=None):
    """Insert or update position."""
    query = """
        INSERT INTO positions (symbol, quantity, avg_entry_price, current_price, unrealized_pnl, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (symbol) DO UPDATE
        SET quantity = EXCLUDED.quantity,
            avg_entry_price = EXCLUDED.avg_entry_price,
            current_price = EXCLUDED.current_price,
            unrealized_pnl = EXCLUDED.unrealized_pnl,
            updated_at = NOW()
    """
    execute_query(query, (symbol, quantity, avg_entry_price, current_price, unrealized_pnl), fetch=False)


def get_position(symbol):
    """Get current position for symbol."""
    query = "SELECT * FROM positions WHERE symbol = %s"
    result = execute_query(query, (symbol,))
    return result[0] if result else None


def insert_news_event(source, title, url, published_at, sentiment, impact_score, keywords, raw_data):
    """Insert news event."""
    import json
    query = """
        INSERT INTO news_events (source, title, url, published_at, sentiment, impact_score, keywords, raw_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_query(query, (source, title, url, published_at, sentiment, impact_score, keywords, json.dumps(raw_data)))
    return result[0]['id'] if result else None


def get_system_flag(flag_name):
    """Get system flag value."""
    query = "SELECT flag_value FROM system_flags WHERE flag_name = %s"
    result = execute_query(query, (flag_name,))
    return result[0]['flag_value'] if result else False


def set_system_flag(flag_name, flag_value, reason, set_by):
    """Set system flag value."""
    query = """
        INSERT INTO system_flags (flag_name, flag_value, reason, set_by, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (flag_name) DO UPDATE
        SET flag_value = EXCLUDED.flag_value,
            reason = EXCLUDED.reason,
            set_by = EXCLUDED.set_by,
            updated_at = NOW()
    """
    execute_query(query, (flag_name, flag_value, reason, set_by), fetch=False)
