"""
SMA (Simple Moving Average) Indicator

This module provides an SMA indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing SMA indicator values aligned by timestamp.
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


def calculate(ohlcv_data: List[OHLCV], period: int = 20) -> List[Dict[str, Any]]:
    """
    Calculate SMA (Simple Moving Average) indicator values for OHLCV data.
    
    Formula: SMA = sum(close) / n
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: SMA period (default: 20)
    
    Returns:
        List of dictionaries with key: 'sma'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period:
        # Not enough data for SMA calculation
        return [{"sma": None} for _ in ohlcv_data]
    
    closes = [candle.close for candle in ohlcv_data]
    result = []
    
    # Calculate SMA for each period
    for i in range(len(closes)):
        if i < period - 1:
            result.append({"sma": None})
        else:
            sma = sum(closes[i - period + 1:i + 1]) / period
            result.append({"sma": round(sma, 8)})
    
    return result
