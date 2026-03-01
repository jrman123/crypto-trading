"""
Database connection and utilities for Trade Knowledge System
"""
import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'trade_knowledge'),
            'user': os.getenv('POSTGRES_USER', 'trader'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password')
        }
        self._connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self._connection = psycopg2.connect(**self.config)
            logger.info(f"Connected to database: {self.config['database']}")
            return self._connection
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def disconnect(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
            
    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Context manager for database cursor"""
        conn = self._connection or self.connect()
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
            
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
            
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows"""
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
            
    def upsert_price(self, symbol: str, timeframe: str, ts, 
                     open_price: float, high: float, low: float, 
                     close: float, volume: float):
        """Insert or update price data (idempotent)"""
        query = """
            INSERT INTO prices (symbol, timeframe, ts, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, ts) 
            DO UPDATE SET 
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """
        params = (symbol, timeframe, ts, open_price, high, low, close, volume)
        return self.execute_update(query, params)
        
    def upsert_features(self, symbol: str, timeframe: str, ts,
                       ema20: Optional[float] = None,
                       ema50: Optional[float] = None,
                       rsi14: Optional[float] = None,
                       macd: Optional[float] = None,
                       macd_signal: Optional[float] = None,
                       macd_hist: Optional[float] = None):
        """Insert or update feature data (idempotent)"""
        query = """
            INSERT INTO features (symbol, timeframe, ts, ema20, ema50, rsi14, 
                                 macd, macd_signal, macd_hist)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, ts)
            DO UPDATE SET
                ema20 = EXCLUDED.ema20,
                ema50 = EXCLUDED.ema50,
                rsi14 = EXCLUDED.rsi14,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                macd_hist = EXCLUDED.macd_hist
        """
        params = (symbol, timeframe, ts, ema20, ema50, rsi14, macd, macd_signal, macd_hist)
        return self.execute_update(query, params)
        
    def insert_signal(self, symbol: str, timeframe: str, ts,
                     side: str, confidence: float,
                     entry: Optional[float] = None,
                     stop: Optional[float] = None,
                     take_profit: Optional[float] = None,
                     reason: Optional[str] = None) -> int:
        """Insert trade signal and return ID"""
        query = """
            INSERT INTO trade_signals (symbol, timeframe, ts, side, confidence, 
                                      entry, stop, take_profit, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (symbol, timeframe, ts, side, confidence, entry, stop, take_profit, reason)
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result['id'] if result else None
            
    def insert_order(self, signal_id: int, symbol: str, side: str,
                    qty: float, price: float, mode: str = 'PAPER') -> int:
        """Insert order and return ID"""
        query = """
            INSERT INTO orders (signal_id, symbol, side, qty, price, mode, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'NEW')
            RETURNING id
        """
        params = (signal_id, symbol, side, qty, price, mode)
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result['id'] if result else None
            
    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        query = """
            UPDATE orders 
            SET status = %s, filled_at = CASE WHEN %s = 'FILLED' THEN NOW() ELSE filled_at END
            WHERE id = %s
        """
        return self.execute_update(query, (status, status, order_id))
        
    def upsert_position(self, symbol: str, qty: float, avg_price: float):
        """Insert or update position"""
        query = """
            INSERT INTO positions (symbol, qty, avg_price, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (symbol)
            DO UPDATE SET
                qty = EXCLUDED.qty,
                avg_price = EXCLUDED.avg_price,
                updated_at = NOW()
        """
        return self.execute_update(query, (symbol, qty, avg_price))
        
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for symbol"""
        query = "SELECT * FROM positions WHERE symbol = %s"
        results = self.execute_query(query, (symbol,))
        return results[0] if results else None
        
    def insert_news_event(self, symbol: Optional[str], published_at,
                         title: str, url: str, source: str,
                         summary: Optional[str] = None,
                         impact: Optional[str] = None,
                         confidence: Optional[float] = None):
        """Insert news event (idempotent on URL)"""
        query = """
            INSERT INTO news_events (symbol, published_at, title, url, source, 
                                    summary, impact, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """
        params = (symbol, published_at, title, url, source, summary, impact, confidence)
        return self.execute_update(query, params)
        
    def get_system_flag(self, key: str) -> Optional[str]:
        """Get system flag value"""
        query = "SELECT value FROM system_flags WHERE key = %s"
        results = self.execute_query(query, (key,))
        return results[0]['value'] if results else None
        
    def set_system_flag(self, key: str, value: str):
        """Set system flag value"""
        query = """
            INSERT INTO system_flags (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """
        return self.execute_update(query, (key, value))
        
    def is_trading_paused(self) -> bool:
        """Check if trading is paused"""
        value = self.get_system_flag('TRADE_PAUSE')
        return value and value.lower() == 'true'
        
    def get_latest_prices(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Get latest prices for symbol"""
        query = """
            SELECT * FROM prices 
            WHERE symbol = %s AND timeframe = %s 
            ORDER BY ts DESC 
            LIMIT %s
        """
        return self.execute_query(query, (symbol, timeframe, limit))
        
    def get_latest_features(self, symbol: str, timeframe: str, limit: int = 1) -> List[Dict]:
        """Get latest features for symbol"""
        query = """
            SELECT * FROM features 
            WHERE symbol = %s AND timeframe = %s 
            ORDER BY ts DESC 
            LIMIT %s
        """
        return self.execute_query(query, (symbol, timeframe, limit))
        
    def get_latest_signal(self, symbol: str) -> Optional[Dict]:
        """Get latest signal for symbol"""
        query = """
            SELECT * FROM trade_signals 
            WHERE symbol = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        results = self.execute_query(query, (symbol,))
        return results[0] if results else None


# Global database instance
db = Database()
