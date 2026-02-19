"""Technical indicators calculation."""
import numpy as np
import pandas as pd
from typing import List, Dict


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return [None] * len(prices)
    
    df = pd.DataFrame({'price': prices})
    ema = df['price'].ewm(span=period, adjust=False).mean()
    return ema.tolist()


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    df = pd.DataFrame({'price': prices})
    delta = df['price'].diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.tolist()


def calculate_macd(prices: List[float], fast=12, slow=26, signal=9) -> Dict[str, List[float]]:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    if len(prices) < slow:
        return {
            'macd': [None] * len(prices),
            'signal': [None] * len(prices),
            'histogram': [None] * len(prices)
        }
    
    df = pd.DataFrame({'price': prices})
    
    ema_fast = df['price'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['price'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line.tolist(),
        'signal': signal_line.tolist(),
        'histogram': histogram.tolist()
    }


def get_latest_indicator_values(prices_data: List[Dict]) -> Dict:
    """
    Calculate all indicators from price data.
    
    Args:
        prices_data: List of price dictionaries with 'close' key
        
    Returns:
        Dictionary with latest indicator values
    """
    if not prices_data:
        return {}
    
    closes = [float(p['close']) for p in prices_data]
    
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    rsi14 = calculate_rsi(closes, 14)
    macd_data = calculate_macd(closes)
    
    return {
        'ema20': ema20[-1],
        'ema50': ema50[-1],
        'rsi14': rsi14[-1],
        'macd': macd_data['macd'][-1],
        'macd_signal': macd_data['signal'][-1],
        'macd_histogram': macd_data['histogram'][-1],
    }
