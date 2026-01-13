"""
MACD (Moving Average Convergence Divergence) Indicator

This module provides a MACD indicator function that can be dynamically loaded
by the pull_ohlcv.py script.

The calculate function accepts a list of OHLCV objects and returns a list of
dictionaries containing MACD indicator values aligned by timestamp.
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


def calculate(ohlcv_data: List[OHLCV], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> List[Dict[str, Any]]:
    """
    Calculate MACD indicator values for OHLCV data.
    
    Args:
        ohlcv_data: List of OHLCV objects ordered by timestamp
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
    
    Returns:
        List of dictionaries with keys: 'macd', 'signal', 'histogram'
        Values are None for periods before enough data is available.
    """
    if len(ohlcv_data) < slow_period + signal_period:
        # Not enough data for MACD calculation
        return [{"macd": None, "signal": None, "histogram": None} for _ in ohlcv_data]
    
    closes = [candle.close for candle in ohlcv_data]
    
    # Calculate EMAs
    def ema(values: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(values) < period:
            return [None] * len(values)
        
        result = []
        multiplier = 2.0 / (period + 1)
        
        # Start with SMA
        sma = sum(values[:period]) / period
        result.append(sma)
        
        # Calculate EMA for remaining values
        for i in range(period, len(values)):
            ema_value = (values[i] - result[-1]) * multiplier + result[-1]
            result.append(ema_value)
        
        return [None] * (period - 1) + result
    
    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)
    
    # Calculate MACD line (fast EMA - slow EMA)
    macd_line = []
    for i in range(len(closes)):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line.append(fast_ema[i] - slow_ema[i])
        else:
            macd_line.append(None)
    
    # Calculate signal line (EMA of MACD line)
    # Extract valid MACD values (skip None values)
    valid_macd = [v for v in macd_line if v is not None]
    
    if len(valid_macd) < signal_period:
        signal_line = [None] * len(macd_line)
    else:
        # Calculate EMA on valid MACD values
        signal_ema_values = ema(valid_macd, signal_period)
        
        # Map signal values back to original positions
        signal_line = []
        valid_idx = 0
        for macd_val in macd_line:
            if macd_val is not None:
                # This position has a valid MACD value
                # Find corresponding signal value (accounting for signal_period offset)
                signal_idx = valid_idx - (signal_period - 1)
                if signal_idx >= 0 and signal_idx < len(signal_ema_values):
                    signal_line.append(signal_ema_values[signal_idx])
                else:
                    signal_line.append(None)
                valid_idx += 1
            else:
                signal_line.append(None)
    
    # Calculate histogram (MACD - Signal)
    result = []
    for i in range(len(ohlcv_data)):
        macd_val = macd_line[i]
        signal_val = signal_line[i] if i < len(signal_line) else None
        
        if macd_val is not None and signal_val is not None:
            histogram = macd_val - signal_val
        else:
            histogram = None
        
        result.append({
            "macd": round(macd_val, 8) if macd_val is not None else None,
            "signal": round(signal_val, 8) if signal_val is not None else None,
            "histogram": round(histogram, 8) if histogram is not None else None,
        })
    
    return result
