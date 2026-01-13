"""
EMA (Exponential Moving Average) Indicator

This module provides an EMA indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing EMA indicator values aligned by timestamp.
"""

import sys
from typing import List, Dict, Any

# Import OHLCV from the parent module
try:
    from pull_ohlcv import OHLCV
except ImportError:
    # Fallback: try importing from parent directory
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from pull_ohlcv import OHLCV


def calculate(ohlcv_data: List[OHLCV], period: int = 20) -> List[Dict[str, Any]]:
    """
    Calculate EMA (Exponential Moving Average) indicator values for OHLCV data.
    
    Formula:
    - EMA = price × k + EMA_prev × (1 − k)
    - k = 2 / (n + 1)
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: EMA period (default: 20)
    
    Returns:
        List of dictionaries with key: 'ema'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period:
        # Not enough data for EMA calculation
        return [{"ema": None} for _ in ohlcv_data]
    
    closes = [candle.close for candle in ohlcv_data]
    result = []
    
    multiplier = 2.0 / (period + 1)
    
    # Start with SMA for the first EMA value
    sma = sum(closes[:period]) / period
    result.extend([{"ema": None} for _ in range(period - 1)])
    result.append({"ema": round(sma, 8)})
    
    # Calculate EMA for remaining values
    ema_prev = sma
    for i in range(period, len(closes)):
        ema_value = (closes[i] - ema_prev) * multiplier + ema_prev
        result.append({"ema": round(ema_value, 8)})
        ema_prev = ema_value
    
    return result
