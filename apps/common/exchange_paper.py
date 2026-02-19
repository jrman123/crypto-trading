"""Paper trading exchange simulator."""
import logging
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PaperExchange:
    """Simulates exchange operations for paper trading."""
    
    def __init__(self, initial_balance: float = 10000.0):
        """
        Initialize paper exchange.
        
        Args:
            initial_balance: Starting balance in quote currency (e.g., USDT)
        """
        self.balance = Decimal(str(initial_balance))
        self.positions = {}  # symbol -> quantity
        self.orders = []
        self.trades = []
        
    def get_balance(self) -> float:
        """Get current balance."""
        return float(self.balance)
    
    def get_position(self, symbol: str) -> float:
        """Get position quantity for symbol."""
        return float(self.positions.get(symbol, Decimal('0')))
    
    def place_market_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict:
        """
        Place a market order (simulated).
        
        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Quantity to trade
            price: Current market price
            
        Returns:
            Order result dictionary
        """
        quantity_decimal = Decimal(str(quantity))
        price_decimal = Decimal(str(price))
        cost = quantity_decimal * price_decimal
        
        order = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
            'price': price,
            'status': 'PENDING',
            'timestamp': datetime.now()
        }
        
        try:
            if side == 'BUY':
                if cost > self.balance:
                    order['status'] = 'REJECTED'
                    order['reason'] = 'Insufficient balance'
                    logger.warning(f"Order rejected: insufficient balance. Cost: {cost}, Balance: {self.balance}")
                else:
                    # Execute buy
                    self.balance -= cost
                    current_pos = self.positions.get(symbol, Decimal('0'))
                    self.positions[symbol] = current_pos + quantity_decimal
                    order['status'] = 'FILLED'
                    logger.info(f"BUY order filled: {quantity} {symbol} @ {price}")
                    
            elif side == 'SELL':
                current_pos = self.positions.get(symbol, Decimal('0'))
                if quantity_decimal > current_pos:
                    order['status'] = 'REJECTED'
                    order['reason'] = 'Insufficient position'
                    logger.warning(f"Order rejected: insufficient position. Requested: {quantity}, Available: {current_pos}")
                else:
                    # Execute sell
                    self.balance += cost
                    self.positions[symbol] = current_pos - quantity_decimal
                    order['status'] = 'FILLED'
                    logger.info(f"SELL order filled: {quantity} {symbol} @ {price}")
            
            self.orders.append(order)
            
            if order['status'] == 'FILLED':
                self.trades.append({
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'timestamp': order['timestamp'],
                    'balance_after': float(self.balance)
                })
            
            return order
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            order['status'] = 'REJECTED'
            order['reason'] = str(e)
            return order
    
    def get_order_history(self, symbol: Optional[str] = None) -> list:
        """Get order history, optionally filtered by symbol."""
        if symbol:
            return [o for o in self.orders if o['symbol'] == symbol]
        return self.orders
    
    def get_trade_history(self, symbol: Optional[str] = None) -> list:
        """Get trade history, optionally filtered by symbol."""
        if symbol:
            return [t for t in self.trades if t['symbol'] == symbol]
        return self.trades
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value.
        
        Args:
            current_prices: Dictionary of symbol -> current price
            
        Returns:
            Total portfolio value in quote currency
        """
        portfolio_value = self.balance
        
        for symbol, quantity in self.positions.items():
            if symbol in current_prices and quantity > 0:
                position_value = quantity * Decimal(str(current_prices[symbol]))
                portfolio_value += position_value
        
        return float(portfolio_value)
    
    def get_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict:
        """Get portfolio summary."""
        summary = {
            'balance': float(self.balance),
            'positions': {symbol: float(qty) for symbol, qty in self.positions.items() if qty > 0},
            'total_orders': len(self.orders),
            'total_trades': len(self.trades),
        }
        
        if current_prices:
            summary['portfolio_value'] = self.get_portfolio_value(current_prices)
        
        return summary
