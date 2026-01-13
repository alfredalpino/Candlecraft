"""
RSI (Relative Strength Index) Indicator

This module provides an RSI indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing RSI indicator values aligned by timestamp.
"""

import sys
from typing import List, Dict, Any

# Import OHLCV from candlecraft library
try:
    from candlecraft import OHLCV
except ImportError:
    # Fallback: try importing from parent directory (for backward compatibility)
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    try:
        from candlecraft import OHLCV
    except ImportError:
        # Last resort: try pull_ohlcv (for legacy support)
        from pull_ohlcv import OHLCV


def calculate(ohlcv_data: List[OHLCV], period: int = 14) -> List[Dict[str, Any]]:
    """
    Calculate RSI (Relative Strength Index) indicator values for OHLCV data.
    
    Uses Wilder's smoothing method:
    - RS = avg_gain / avg_loss
    - RSI = 100 - (100 / (1 + RS))
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: RSI period (default: 14)
    
    Returns:
        List of dictionaries with key: 'rsi'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period + 1:
        # Not enough data for RSI calculation
        return [{"rsi": None} for _ in ohlcv_data]
    
    closes = [candle.close for candle in ohlcv_data]
    result = [{"rsi": None} for _ in range(period)]
    
    # Calculate price changes
    price_changes = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        price_changes.append(change)
    
    # Initial average gain and loss (first period)
    gains = [max(0, change) for change in price_changes[:period]]
    losses = [max(0, -change) for change in price_changes[:period]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    # Calculate first RSI value
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
    
    result.append({"rsi": round(rsi, 2)})
    
    # Calculate subsequent RSI values using Wilder's smoothing
    for i in range(period, len(price_changes)):
        current_gain = max(0, price_changes[i])
        current_loss = max(0, -price_changes[i])
        
        # Wilder's smoothing: new_avg = (prev_avg * (n-1) + current) / n
        avg_gain = (avg_gain * (period - 1) + current_gain) / period
        avg_loss = (avg_loss * (period - 1) + current_loss) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        
        result.append({"rsi": round(rsi, 2)})
    
    return result
