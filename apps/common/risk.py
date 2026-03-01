"""
Risk management utilities for Trade Knowledge System
"""
import logging
from typing import Dict, Optional
import yaml

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk parameters and position sizing"""
    
    def __init__(self, config_path: str = '/app/configs/risk.yaml'):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path: str) -> Dict:
        """Load risk configuration from YAML"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded risk config: {config}")
                return config
        except Exception as e:
            logger.error(f"Failed to load risk config: {e}")
            # Return safe defaults
            return {
                'max_position_usd': 1000,
                'risk_per_trade_pct': 2.0,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 4.0,
                'min_confidence': 60.0
            }
    
    def get_max_position_usd(self) -> float:
        """Get maximum position size in USD"""
        return float(self.config.get('max_position_usd', 1000))
    
    def get_risk_per_trade_pct(self) -> float:
        """Get risk percentage per trade"""
        return float(self.config.get('risk_per_trade_pct', 2.0))
    
    def get_stop_loss_pct(self) -> float:
        """Get stop loss percentage"""
        return float(self.config.get('stop_loss_pct', 2.0))
    
    def get_take_profit_pct(self) -> float:
        """Get take profit percentage"""
        return float(self.config.get('take_profit_pct', 4.0))
    
    def get_min_confidence(self) -> float:
        """Get minimum confidence threshold"""
        return float(self.config.get('min_confidence', 60.0))
    
    def calculate_position_size(self, 
                               entry_price: float,
                               confidence: float,
                               account_balance: float = 10000) -> float:
        """
        Calculate position size based on confidence and risk parameters
        
        Args:
            entry_price: Entry price for the trade
            confidence: Signal confidence (0-100)
            account_balance: Current account balance in USD
            
        Returns:
            Position size in base currency units
        """
        # Max position in USD based on config
        max_position = min(
            self.get_max_position_usd(),
            account_balance * 0.1  # Never more than 10% of account
        )
        
        # Scale by confidence (confidence/100)
        confidence_factor = confidence / 100.0
        position_usd = max_position * confidence_factor
        
        # Convert to quantity
        qty = position_usd / entry_price
        
        logger.info(
            f"Position sizing: entry=${entry_price:.2f}, "
            f"confidence={confidence:.1f}%, qty={qty:.8f}"
        )
        
        return qty
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            Stop loss price
        """
        stop_pct = self.get_stop_loss_pct() / 100.0
        
        if side == 'BUY':
            # For long positions, stop below entry
            stop_price = entry_price * (1 - stop_pct)
        else:
            # For short positions, stop above entry
            stop_price = entry_price * (1 + stop_pct)
            
        return stop_price
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            Take profit price
        """
        tp_pct = self.get_take_profit_pct() / 100.0
        
        if side == 'BUY':
            # For long positions, take profit above entry
            tp_price = entry_price * (1 + tp_pct)
        else:
            # For short positions, take profit below entry
            tp_price = entry_price * (1 - tp_pct)
            
        return tp_price
    
    def validate_trade(self, 
                      confidence: float,
                      qty: float,
                      trading_paused: bool = False) -> tuple[bool, str]:
        """
        Validate if a trade should be executed
        
        Args:
            confidence: Signal confidence
            qty: Position quantity
            trading_paused: Whether trading is paused
            
        Returns:
            (is_valid, reason)
        """
        if trading_paused:
            return False, "Trading is paused by system flag"
        
        if confidence < self.get_min_confidence():
            return False, f"Confidence {confidence:.1f}% below minimum {self.get_min_confidence():.1f}%"
        
        if qty <= 0:
            return False, "Invalid quantity (must be > 0)"
        
        return True, "Trade validated"


# Global risk manager instance (will be initialized by apps)
risk_manager = None


def get_risk_manager(config_path: str = '/app/configs/risk.yaml') -> RiskManager:
    """Get or create risk manager instance"""
    global risk_manager
    if risk_manager is None:
        risk_manager = RiskManager(config_path)
    return risk_manager
