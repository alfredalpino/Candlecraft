"""
Data models for candlecraft library.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class AssetClass(Enum):
    """Asset class types"""
    CRYPTO = "crypto"
    FOREX = "forex"
    EQUITY = "equity"


@dataclass
class OHLCV:
    """Internal data model for OHLCV data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]
    symbol: str
    timeframe: str
    asset_class: AssetClass
    source: str
