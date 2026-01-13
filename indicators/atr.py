"""
ATR (Average True Range) Indicator

This module provides an ATR indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing ATR indicator values aligned by timestamp.
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


def calculate(ohlcv_data: List[OHLCV], period: int = 14) -> List[Dict[str, Any]]:
    """
    Calculate ATR (Average True Range) indicator values for OHLCV data.
    
    Formula:
    - TR = max(high−low, |high−prev_close|, |low−prev_close|)
    - ATR = EMA(TR, n)
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: ATR period (default: 14)
    
    Returns:
        List of dictionaries with key: 'atr'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period + 1:
        # Not enough data for ATR calculation
        return [{"atr": None} for _ in ohlcv_data]
    
    # Calculate True Range for each period
    true_ranges = []
    
    for i in range(len(ohlcv_data)):
        if i == 0:
            # First period: TR = high - low
            tr = ohlcv_data[i].high - ohlcv_data[i].low
        else:
            # TR = max(high-low, |high-prev_close|, |low-prev_close|)
            high_low = ohlcv_data[i].high - ohlcv_data[i].low
            high_prev_close = abs(ohlcv_data[i].high - ohlcv_data[i - 1].close)
            low_prev_close = abs(ohlcv_data[i].low - ohlcv_data[i - 1].close)
            tr = max(high_low, high_prev_close, low_prev_close)
        
        true_ranges.append(tr)
    
    # Calculate ATR using EMA
    result = []
    multiplier = 2.0 / (period + 1)
    
    # Start with SMA for the first ATR value
    sma = sum(true_ranges[:period]) / period
    result.extend([{"atr": None} for _ in range(period - 1)])
    result.append({"atr": round(sma, 8)})
    
    # Calculate EMA for remaining values
    atr_prev = sma
    for i in range(period, len(true_ranges)):
        atr_value = (true_ranges[i] - atr_prev) * multiplier + atr_prev
        result.append({"atr": round(atr_value, 8)})
        atr_prev = atr_value
    
    return result
