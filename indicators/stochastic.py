"""
Stochastic Oscillator Indicator

This module provides a Stochastic Oscillator indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing Stochastic Oscillator indicator values aligned by timestamp.
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


def calculate(ohlcv_data: List[OHLCV], k_period: int = 14, d_period: int = 3) -> List[Dict[str, Any]]:
    """
    Calculate Stochastic Oscillator indicator values for OHLCV data.
    
    Formula:
    - %K = (close − lowest_low) / (highest_high − lowest_low) × 100
    - %D = SMA(%K)
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)
    
    Returns:
        List of dictionaries with keys: 'stoch_k', 'stoch_d'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < k_period + d_period - 1:
        # Not enough data for Stochastic calculation
        return [{"stoch_k": None, "stoch_d": None} for _ in ohlcv_data]
    
    result = []
    stoch_k_values = []
    
    # Calculate %K for each period
    for i in range(len(ohlcv_data)):
        if i < k_period - 1:
            result.append({"stoch_k": None, "stoch_d": None})
            stoch_k_values.append(None)
        else:
            # Get the window for this period
            window = ohlcv_data[i - k_period + 1:i + 1]
            
            # Find highest high and lowest low in the window
            highest_high = max(candle.high for candle in window)
            lowest_low = min(candle.low for candle in window)
            
            # Calculate %K
            if highest_high == lowest_low:
                stoch_k = 50.0  # Avoid division by zero
            else:
                stoch_k = ((ohlcv_data[i].close - lowest_low) / (highest_high - lowest_low)) * 100.0
            
            stoch_k_values.append(stoch_k)
            
            # Calculate %D (SMA of %K) if we have enough values
            if len([v for v in stoch_k_values if v is not None]) < d_period:
                result.append({"stoch_k": round(stoch_k, 2), "stoch_d": None})
            else:
                # Get the last d_period valid %K values
                valid_k_values = [v for v in stoch_k_values if v is not None][-d_period:]
                stoch_d = sum(valid_k_values) / d_period
                result.append({"stoch_k": round(stoch_k, 2), "stoch_d": round(stoch_d, 2)})
    
    return result
