"""
VWAP (Volume Weighted Average Price) Indicator

This module provides a VWAP indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing VWAP indicator values aligned by timestamp.
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


def calculate(ohlcv_data: List[OHLCV]) -> List[Dict[str, Any]]:
    """
    Calculate VWAP (Volume Weighted Average Price) indicator values for OHLCV data.
    
    Formula: VWAP = cumulative(price × volume) / cumulative(volume)
    
    Uses typical price: (high + low + close) / 3
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
    
    Returns:
        List of dictionaries with key: 'vwap'
        Values are None if volume data is missing.
    """
    result = []
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0
    
    for candle in ohlcv_data:
        if candle.volume is None or candle.volume == 0:
            result.append({"vwap": None})
            continue
        
        # Calculate typical price
        typical_price = (candle.high + candle.low + candle.close) / 3.0
        
        # Update cumulative values
        cumulative_price_volume += typical_price * candle.volume
        cumulative_volume += candle.volume
        
        # Calculate VWAP
        vwap = cumulative_price_volume / cumulative_volume
        result.append({"vwap": round(vwap, 8)})
    
    return result
