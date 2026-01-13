"""
Bollinger Bands Indicator

This module provides a Bollinger Bands indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing Bollinger Bands indicator values aligned by timestamp.
"""

import sys
import statistics
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


def calculate(ohlcv_data: List[OHLCV], period: int = 20, std_mult: float = 2.0) -> List[Dict[str, Any]]:
    """
    Calculate Bollinger Bands indicator values for OHLCV data.
    
    Formula:
    - Middle = SMA(n)
    - Upper = SMA + k × std
    - Lower = SMA − k × std
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: SMA period (default: 20)
        std_mult: Standard deviation multiplier (default: 2.0)
    
    Returns:
        List of dictionaries with keys: 'bb_upper', 'bb_middle', 'bb_lower'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period:
        # Not enough data for Bollinger Bands calculation
        return [{"bb_upper": None, "bb_middle": None, "bb_lower": None} for _ in ohlcv_data]
    
    closes = [candle.close for candle in ohlcv_data]
    result = []
    
    # Calculate Bollinger Bands for each period
    for i in range(len(closes)):
        if i < period - 1:
            result.append({"bb_upper": None, "bb_middle": None, "bb_lower": None})
        else:
            # Get the window of closes for this period
            window = closes[i - period + 1:i + 1]
            
            # Calculate SMA (middle band)
            sma = sum(window) / period
            
            # Calculate standard deviation
            std = statistics.stdev(window)
            
            # Calculate upper and lower bands
            upper = sma + (std_mult * std)
            lower = sma - (std_mult * std)
            
            result.append({
                "bb_upper": round(upper, 8),
                "bb_middle": round(sma, 8),
                "bb_lower": round(lower, 8),
            })
    
    return result
