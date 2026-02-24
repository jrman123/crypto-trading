"""
Common database module
Provides database connection and query utilities for all services
"""
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager
import structlog

logger = structlog.get_logger()


class Database:
    """Database connection manager with connection pooling for better performance"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'trading_knowledge'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        }
        # Initialize connection pool for better performance
        self._pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self.connection_params
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error("Failed to initialize connection pool", error=str(e))
            # Fallback to direct connections if pool fails
            self._pool = None
        
    @contextmanager
    def get_connection(self):
        """Get a database connection context manager with pooling support"""
        conn = None
        from_pool = False
        try:
            if self._pool:
                conn = self._pool.getconn()
                from_pool = True
            else:
                conn = psycopg2.connect(**self.connection_params)
            
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Database error", error=str(e))
            raise
        finally:
            if conn:
                if from_pool and self._pool:
                    self._pool.putconn(conn)
                else:
                    conn.close()
    
    def health_check(self):
        """Check database connection health"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query and optionally fetch results"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                return cursor.rowcount
    
    def execute_many(self, query, params_list):
        """Execute a query with multiple parameter sets"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, query, params_list)
                return cursor.rowcount
    
    def insert_price(self, symbol, timeframe, timestamp, open_price, high, low, close, volume):
        """Insert a price candle"""
        query = """
            INSERT INTO prices (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE
            SET open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            RETURNING id
        """
        result = self.execute_query(query, (symbol, timeframe, timestamp, open_price, high, low, close, volume))
        return result[0]['id'] if result else None
    
    def insert_prices_batch(self, prices_data):
        """Insert multiple price candles efficiently using batch insert"""
        if not prices_data:
            return 0
        
        query = """
            INSERT INTO prices (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE
            SET open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, prices_data, page_size=100)
                    return cursor.rowcount
        except Exception as e:
            logger.error("Batch insert failed", error=str(e))
            return 0
    
    def get_latest_prices(self, symbol, timeframe, limit=100):
        """Get latest price candles for a symbol"""
        query = """
            SELECT * FROM prices
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return self.execute_query(query, (symbol, timeframe, limit))
    
    def insert_features(self, symbol, timeframe, timestamp, features_dict):
        """Insert computed features"""
        columns = ['symbol', 'timeframe', 'timestamp'] + list(features_dict.keys())
        values = [symbol, timeframe, timestamp] + list(features_dict.values())
        placeholders = ', '.join(['%s'] * len(values))
        
        query = f"""
            INSERT INTO features ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE
            SET {', '.join([f"{col} = EXCLUDED.{col}" for col in features_dict.keys()])}
            RETURNING id
        """
        result = self.execute_query(query, values)
        return result[0]['id'] if result else None
    
    def get_latest_features(self, symbol, timeframe, limit=100):
        """Get latest features for a symbol"""
        query = """
            SELECT * FROM features
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return self.execute_query(query, (symbol, timeframe, limit))
    
    def insert_signal(self, symbol, signal_type, confidence, timestamp, **kwargs):
        """Insert a trade signal"""
        query = """
            INSERT INTO trade_signals 
            (symbol, signal_type, confidence, timestamp, entry_price, stop_loss, 
             take_profit, position_size_usd, strategy, timeframe, reason, indicators_snapshot)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            symbol, signal_type, confidence, timestamp,
            kwargs.get('entry_price'), kwargs.get('stop_loss'),
            kwargs.get('take_profit'), kwargs.get('position_size_usd'),
            kwargs.get('strategy'), kwargs.get('timeframe'),
            kwargs.get('reason'), kwargs.get('indicators_snapshot')
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def get_latest_signals(self, symbol=None, limit=10):
        """Get latest trade signals"""
        if symbol:
            query = """
                SELECT * FROM trade_signals
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            return self.execute_query(query, (symbol, limit))
        else:
            query = """
                SELECT * FROM trade_signals
                ORDER BY timestamp DESC
                LIMIT %s
            """
            return self.execute_query(query, (limit,))
    
    def get_system_flag(self, flag_name):
        """Get a system flag value"""
        query = "SELECT flag_value FROM system_flags WHERE flag_name = %s"
        result = self.execute_query(query, (flag_name,))
        return result[0]['flag_value'] if result else None
    
    def set_system_flag(self, flag_name, flag_value, reason=None, set_by=None):
        """Set a system flag"""
        query = """
            INSERT INTO system_flags (flag_name, flag_value, reason, set_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (flag_name) DO UPDATE
            SET flag_value = EXCLUDED.flag_value,
                reason = EXCLUDED.reason,
                set_by = EXCLUDED.set_by,
                set_at = NOW()
        """
        self.execute_query(query, (flag_name, flag_value, reason, set_by), fetch=False)
    
    def insert_order(self, order_data):
        """Insert an order record"""
        query = """
            INSERT INTO orders 
            (order_id, signal_id, symbol, side, order_type, status, quantity, 
             price, is_paper, placed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            order_data.get('order_id'),
            order_data.get('signal_id'),
            order_data.get('symbol'),
            order_data.get('side'),
            order_data.get('order_type'),
            order_data.get('status', 'NEW'),
            order_data.get('quantity'),
            order_data.get('price'),
            order_data.get('is_paper', True),
            order_data.get('placed_at')
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def update_order_status(self, order_id, status, filled_quantity=None, avg_fill_price=None):
        """Update order status"""
        query = """
            UPDATE orders
            SET status = %s,
                filled_quantity = COALESCE(%s, filled_quantity),
                avg_fill_price = COALESCE(%s, avg_fill_price),
                filled_at = CASE WHEN %s IN ('FILLED', 'PARTIALLY_FILLED') THEN NOW() ELSE filled_at END
            WHERE order_id = %s
        """
        self.execute_query(query, (status, filled_quantity, avg_fill_price, status, order_id), fetch=False)
    
    def insert_news_event(self, news_data):
        """Insert a news event"""
        query = """
            INSERT INTO news_events
            (source, title, content, url, sentiment, sentiment_score, 
             symbols, impact_level, category, keywords, published_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            news_data.get('source'),
            news_data.get('title'),
            news_data.get('content'),
            news_data.get('url'),
            news_data.get('sentiment'),
            news_data.get('sentiment_score'),
            news_data.get('symbols', []),
            news_data.get('impact_level'),
            news_data.get('category'),
            news_data.get('keywords', []),
            news_data.get('published_at')
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def log_audit(self, service, action, entity_type=None, entity_id=None, 
                  details=None, status='success', error_message=None):
        """Log an audit event"""
        query = """
            INSERT INTO audit_log
            (service, action, entity_type, entity_id, details, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.execute_query(
            query, 
            (service, action, entity_type, entity_id, details, status, error_message),
            fetch=False
        )


# Global database instance
db = Database()
