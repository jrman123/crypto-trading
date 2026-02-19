"""Risk management utilities."""
import os
import yaml
from decimal import Decimal
from typing import Dict, Optional


def load_risk_config() -> Dict:
    """Load risk configuration from YAML file."""
    config_path = os.getenv('RISK_CONFIG', '/app/configs/risk.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Return defaults if file not found
        return {
            'max_position_size_usd': 1000,
            'max_position_pct': 0.1,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10,
            'max_daily_trades': 10,
            'min_signal_strength': 0.6
        }


def calculate_position_size(balance: float, price: float, risk_config: Optional[Dict] = None) -> float:
    """
    Calculate appropriate position size based on risk parameters.
    
    Args:
        balance: Available balance in quote currency
        price: Current price of asset
        risk_config: Risk configuration dictionary
        
    Returns:
        Position size in base currency
    """
    if risk_config is None:
        risk_config = load_risk_config()
    
    max_size_usd = risk_config.get('max_position_size_usd', 1000)
    max_pct = risk_config.get('max_position_pct', 0.1)
    
    # Calculate based on max USD
    size_from_usd = max_size_usd / price
    
    # Calculate based on percentage
    size_from_pct = (balance * max_pct) / price
    
    # Return the smaller of the two
    return min(size_from_usd, size_from_pct)


def check_signal_strength(strength: float, risk_config: Optional[Dict] = None) -> bool:
    """
    Check if signal strength meets minimum threshold.
    
    Args:
        strength: Signal strength (0.0 to 1.0)
        risk_config: Risk configuration dictionary
        
    Returns:
        True if signal is strong enough
    """
    if risk_config is None:
        risk_config = load_risk_config()
    
    min_strength = risk_config.get('min_signal_strength', 0.6)
    return strength >= min_strength


def calculate_stop_loss(entry_price: float, side: str, risk_config: Optional[Dict] = None) -> float:
    """
    Calculate stop loss price.
    
    Args:
        entry_price: Entry price
        side: 'BUY' or 'SELL'
        risk_config: Risk configuration dictionary
        
    Returns:
        Stop loss price
    """
    if risk_config is None:
        risk_config = load_risk_config()
    
    stop_loss_pct = risk_config.get('stop_loss_pct', 0.05)
    
    if side == 'BUY':
        return entry_price * (1 - stop_loss_pct)
    else:  # SELL
        return entry_price * (1 + stop_loss_pct)


def calculate_take_profit(entry_price: float, side: str, risk_config: Optional[Dict] = None) -> float:
    """
    Calculate take profit price.
    
    Args:
        entry_price: Entry price
        side: 'BUY' or 'SELL'
        risk_config: Risk configuration dictionary
        
    Returns:
        Take profit price
    """
    if risk_config is None:
        risk_config = load_risk_config()
    
    take_profit_pct = risk_config.get('take_profit_pct', 0.10)
    
    if side == 'BUY':
        return entry_price * (1 + take_profit_pct)
    else:  # SELL
        return entry_price * (1 - take_profit_pct)


def check_daily_trade_limit(trades_today: int, risk_config: Optional[Dict] = None) -> bool:
    """
    Check if we've exceeded daily trade limit.
    
    Args:
        trades_today: Number of trades executed today
        risk_config: Risk configuration dictionary
        
    Returns:
        True if we can still trade
    """
    if risk_config is None:
        risk_config = load_risk_config()
    
    max_daily = risk_config.get('max_daily_trades', 10)
    return trades_today < max_daily
