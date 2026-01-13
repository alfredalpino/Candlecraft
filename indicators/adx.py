"""
ADX (Average Directional Index) Indicator

This module provides an ADX indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing ADX indicator values aligned by timestamp.
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
    Calculate ADX (Average Directional Index) indicator values for OHLCV data.
    
    Formula:
    - Uses +DM, −DM, TR, DI+, DI−
    - ADX = EMA(|DI+ − DI−| / (DI+ + DI−), n)
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        period: ADX period (default: 14)
    
    Returns:
        List of dictionaries with keys: 'adx', 'di_plus', 'di_minus'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < period + 1:
        # Not enough data for ADX calculation
        return [{"adx": None, "di_plus": None, "di_minus": None} for _ in ohlcv_data]
    
    # Calculate True Range and Directional Movement
    true_ranges = []
    plus_dm = []
    minus_dm = []
    
    for i in range(len(ohlcv_data)):
        if i == 0:
            # First period
            tr = ohlcv_data[i].high - ohlcv_data[i].low
            plus_dm.append(0.0)
            minus_dm.append(0.0)
        else:
            # True Range
            high_low = ohlcv_data[i].high - ohlcv_data[i].low
            high_prev_close = abs(ohlcv_data[i].high - ohlcv_data[i - 1].close)
            low_prev_close = abs(ohlcv_data[i].low - ohlcv_data[i - 1].close)
            tr = max(high_low, high_prev_close, low_prev_close)
            
            # Directional Movement
            up_move = ohlcv_data[i].high - ohlcv_data[i - 1].high
            down_move = ohlcv_data[i - 1].low - ohlcv_data[i].low
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0.0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0.0)
        
        true_ranges.append(tr)
    
    # Calculate smoothed TR, +DM, -DM using Wilder's smoothing
    result = []
    smoothed_tr = [None] * (period - 1)
    smoothed_plus_dm = [None] * (period - 1)
    smoothed_minus_dm = [None] * (period - 1)
    
    # Initial values (sum of first period)
    initial_tr = sum(true_ranges[:period])
    initial_plus_dm = sum(plus_dm[:period])
    initial_minus_dm = sum(minus_dm[:period])
    
    smoothed_tr.append(initial_tr)
    smoothed_plus_dm.append(initial_plus_dm)
    smoothed_minus_dm.append(initial_minus_dm)
    
    # Calculate smoothed values for remaining periods
    for i in range(period, len(true_ranges)):
        # Wilder's smoothing: new = (prev * (n-1) + current) / n
        smoothed_tr.append((smoothed_tr[-1] * (period - 1) + true_ranges[i]) / period)
        smoothed_plus_dm.append((smoothed_plus_dm[-1] * (period - 1) + plus_dm[i]) / period)
        smoothed_minus_dm.append((smoothed_minus_dm[-1] * (period - 1) + minus_dm[i]) / period)
    
    # Calculate DI+ and DI-
    di_plus_values = []
    di_minus_values = []
    
    for i in range(len(smoothed_tr)):
        if smoothed_tr[i] is None or smoothed_tr[i] == 0:
            di_plus = None if smoothed_tr[i] is None else 0.0
            di_minus = None if smoothed_tr[i] is None else 0.0
        else:
            di_plus = (smoothed_plus_dm[i] / smoothed_tr[i]) * 100.0
            di_minus = (smoothed_minus_dm[i] / smoothed_tr[i]) * 100.0
        
        di_plus_values.append(di_plus)
        di_minus_values.append(di_minus)
    
    # Calculate DX and ADX (only for valid DI values)
    dx_values = []
    for i in range(len(di_plus_values)):
        if di_plus_values[i] is None:
            dx_values.append(None)
        else:
            di_sum = di_plus_values[i] + di_minus_values[i]
            if di_sum == 0:
                dx = 0.0
            else:
                dx = abs(di_plus_values[i] - di_minus_values[i]) / di_sum * 100.0
            dx_values.append(dx)
    
    # Calculate ADX using EMA of DX
    multiplier = 2.0 / (period + 1)
    
    # Find first valid DX window for ADX calculation
    valid_dx_start = period - 1
    first_dx_window = [dx for dx in dx_values[valid_dx_start:valid_dx_start + period] if dx is not None]
    
    if len(first_dx_window) < period:
        # Not enough valid DX values
        return [{"adx": None, "di_plus": None, "di_minus": None} for _ in ohlcv_data]
    
    adx_sma = sum(first_dx_window) / period
    
    # Build result
    for i in range(period - 1):
        result.append({"adx": None, "di_plus": None, "di_minus": None})
    
    result.append({
        "adx": round(adx_sma, 2),
        "di_plus": round(di_plus_values[period - 1], 2),
        "di_minus": round(di_minus_values[period - 1], 2),
    })
    
    # Calculate ADX for remaining values using EMA
    adx_prev = adx_sma
    for i in range(period, len(dx_values)):
        if dx_values[i] is None:
            result.append({
                "adx": None,
                "di_plus": round(di_plus_values[i], 2) if di_plus_values[i] is not None else None,
                "di_minus": round(di_minus_values[i], 2) if di_minus_values[i] is not None else None,
            })
        else:
            adx_value = (dx_values[i] - adx_prev) * multiplier + adx_prev
            result.append({
                "adx": round(adx_value, 2),
                "di_plus": round(di_plus_values[i], 2),
                "di_minus": round(di_minus_values[i], 2),
            })
            adx_prev = adx_value
    
    return result
