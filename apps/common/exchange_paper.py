"""
Paper trading exchange adapter for Trade Knowledge System
Simulates order execution without real money
"""
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PaperExchange:
    """Paper trading exchange that simulates order execution"""
    
    def __init__(self, db_instance):
        """
        Initialize paper exchange
        
        Args:
            db_instance: Database instance for tracking positions
        """
        self.db = db_instance
        
    def execute_market_order(self, 
                            symbol: str,
                            side: str,
                            qty: float,
                            current_price: float) -> Dict:
        """
        Execute a paper market order
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            qty: Quantity to trade
            current_price: Current market price
            
        Returns:
            Dict with execution details
        """
        logger.info(
            f"[PAPER] Executing {side} order: {qty} {symbol} @ ${current_price:.2f}"
        )
        
        # Get current position
        position = self.db.get_position(symbol) or {
            'symbol': symbol,
            'qty': 0,
            'avg_price': 0
        }
        
        current_qty = float(position['qty'])
        current_avg = float(position['avg_price'])
        
        # Calculate new position
        if side == 'BUY':
            new_qty = current_qty + qty
            # Update average price
            if new_qty > 0:
                total_cost = (current_qty * current_avg) + (qty * current_price)
                new_avg = total_cost / new_qty
            else:
                new_avg = current_price
        else:  # SELL
            new_qty = current_qty - qty
            # Keep same average for sells, or reset if closing
            new_avg = current_avg if new_qty > 0 else 0
        
        # Update position in database
        self.db.upsert_position(symbol, new_qty, new_avg)
        
        result = {
            'status': 'FILLED',
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'price': current_price,
            'filled_at': datetime.now(),
            'prev_qty': current_qty,
            'new_qty': new_qty,
            'avg_price': new_avg
        }
        
        logger.info(
            f"[PAPER] Order filled: {symbol} position "
            f"{current_qty} -> {new_qty} @ avg ${new_avg:.2f}"
        )
        
        return result
    
    def get_current_price(self, symbol: str, timeframe: str = '1h') -> Optional[float]:
        """
        Get current market price from latest candle
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            
        Returns:
            Current price or None
        """
        prices = self.db.get_latest_prices(symbol, timeframe, limit=1)
        if prices:
            return float(prices[0]['close'])
        return None
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current position for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position dict or None
        """
        return self.db.get_position(symbol)
    
    def get_account_balance(self) -> float:
        """
        Get simulated account balance
        For paper trading, returns a fixed amount
        
        Returns:
            Account balance in USD
        """
        # In a real system, this would calculate based on positions
        # For now, return a fixed paper trading balance
        return 10000.0
    
    def close_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Close entire position for a symbol
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Execution result or None if no position
        """
        position = self.get_position(symbol)
        if not position or position['qty'] == 0:
            logger.info(f"[PAPER] No position to close for {symbol}")
            return None
        
        qty = float(position['qty'])
        side = 'SELL' if qty > 0 else 'BUY'
        abs_qty = abs(qty)
        
        return self.execute_market_order(symbol, side, abs_qty, current_price)
