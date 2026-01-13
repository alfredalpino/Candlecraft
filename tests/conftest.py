"""
Pytest configuration and shared fixtures for testing
"""

import pytest
from datetime import datetime, timezone
from typing import List
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pull_ohlcv import OHLCV, AssetClass


@pytest.fixture
def sample_ohlcv_data() -> List[OHLCV]:
    """Generate sample OHLCV data for testing indicators."""
    data = []
    base_price = 100.0
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    for i in range(100):
        # Create a simple price pattern
        price_change = (i % 10) * 0.5
        close = base_price + price_change
        high = close + 1.0
        low = close - 1.0
        open_price = close - 0.5
        volume = 1000.0 + (i * 10)
        
        candle = OHLCV(
            timestamp=base_time.replace(hour=i % 24),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            symbol="TEST",
            timeframe="1h",
            asset_class=AssetClass.CRYPTO,
            source="test"
        )
        data.append(candle)
    
    return data


@pytest.fixture
def sample_ohlcv_data_no_volume() -> List[OHLCV]:
    """Generate sample OHLCV data without volume for testing."""
    data = []
    base_price = 100.0
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    for i in range(50):
        price_change = (i % 10) * 0.5
        close = base_price + price_change
        high = close + 1.0
        low = close - 1.0
        open_price = close - 0.5
        
        candle = OHLCV(
            timestamp=base_time.replace(hour=i % 24),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=None,  # No volume
            symbol="TEST",
            timeframe="1h",
            asset_class=AssetClass.CRYPTO,
            source="test"
        )
        data.append(candle)
    
    return data


@pytest.fixture
def minimal_ohlcv_data() -> List[OHLCV]:
    """Generate minimal OHLCV data (5 candles) for edge case testing."""
    data = []
    base_price = 100.0
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    for i in range(5):
        close = base_price + i
        candle = OHLCV(
            timestamp=base_time.replace(hour=i),
            open=close - 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1000.0,
            symbol="TEST",
            timeframe="1h",
            asset_class=AssetClass.CRYPTO,
            source="test"
        )
        data.append(candle)
    
    return data
