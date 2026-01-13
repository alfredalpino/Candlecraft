"""
OBV (On-Balance Volume) Indicator

This module provides an OBV indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing OBV indicator values aligned by timestamp.
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
    Calculate OBV (On-Balance Volume) indicator values for OHLCV data.
    
    Formula:
    - If close ↑ → OBV += volume
    - If close ↓ → OBV −= volume
    - If close = → OBV unchanged
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
    
    Returns:
        List of dictionaries with key: 'obv'
        Values are None if volume data is missing.
    """
    result = []
    obv = 0.0
    
    for i, candle in enumerate(ohlcv_data):
        if candle.volume is None:
            result.append({"obv": None})
            continue
        
        if i == 0:
            # First period: OBV starts at volume (or 0)
            obv = candle.volume
        else:
            prev_close = ohlcv_data[i - 1].close
            current_close = candle.close
            
            if current_close > prev_close:
                # Price increased: add volume
                obv += candle.volume
            elif current_close < prev_close:
                # Price decreased: subtract volume
                obv -= candle.volume
            # If price unchanged, OBV remains the same
        
        result.append({"obv": round(obv, 2)})
    
    return result
