"""
Technical indicator calculations for Trade Knowledge System
"""
import logging
from typing import List, Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average
    Returns the latest EMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
        
    prices_array = np.array(prices)
    return pd.Series(prices_array).ewm(span=period, adjust=False).mean().iloc[-1]


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index
    Returns RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None
        
    prices_series = pd.Series(prices)
    delta = prices_series.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]


def calculate_macd(prices: List[float], 
                  fast_period: int = 12, 
                  slow_period: int = 26, 
                  signal_period: int = 9) -> Dict[str, Optional[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    Returns dict with macd, signal, and histogram values
    """
    result = {
        'macd': None,
        'signal': None,
        'histogram': None
    }
    
    if len(prices) < slow_period + signal_period:
        return result
        
    prices_series = pd.Series(prices)
    
    # Calculate EMAs
    ema_fast = prices_series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = prices_series.ewm(span=slow_period, adjust=False).mean()
    
    # MACD line
    macd_line = ema_fast - ema_slow
    
    # Signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    result['macd'] = macd_line.iloc[-1]
    result['signal'] = signal_line.iloc[-1]
    result['histogram'] = histogram.iloc[-1]
    
    return result


def compute_all_indicators(price_data: List[Dict]) -> Dict[str, Optional[float]]:
    """
    Compute all indicators from price data
    
    Args:
        price_data: List of dicts with 'close' prices (oldest to newest)
        
    Returns:
        Dict with all indicator values
    """
    if not price_data:
        return {
            'ema20': None,
            'ema50': None,
            'rsi14': None,
            'macd': None,
            'macd_signal': None,
            'macd_hist': None
        }
    
    # Extract close prices
    closes = [float(p['close']) for p in price_data]
    
    # Calculate indicators
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    rsi14 = calculate_rsi(closes, 14)
    macd_data = calculate_macd(closes, 12, 26, 9)
    
    return {
        'ema20': ema20,
        'ema50': ema50,
        'rsi14': rsi14,
        'macd': macd_data['macd'],
        'macd_signal': macd_data['signal'],
        'macd_hist': macd_data['histogram']
    }


def get_previous_macd_hist(price_data: List[Dict]) -> Optional[float]:
    """
    Get the previous MACD histogram value for trend detection
    
    Args:
        price_data: List of dicts with 'close' prices (oldest to newest)
        
    Returns:
        Previous MACD histogram value or None
    """
    if len(price_data) < 2:
        return None
        
    # Use all but last price to get previous value
    closes = [float(p['close']) for p in price_data[:-1]]
    macd_data = calculate_macd(closes, 12, 26, 9)
    
    return macd_data['histogram']
