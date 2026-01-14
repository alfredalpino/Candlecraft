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


class Provider(Enum):
    """Data provider types"""
    BINANCE = "binance"
    TWELVEDATA = "twelvedata"


class RateLimitException(Exception):
    """
    Exception raised when a provider rate limit is encountered.
    
    Attributes:
        provider: Name of the provider (e.g., 'twelvedata')
        retry_after: Optional retry-after duration in seconds if provided by the API
        message: Original error message from the provider
    """
    def __init__(self, provider: str, message: str, retry_after: Optional[float] = None):
        self.provider = provider
        self.retry_after = retry_after
        self.message = message
        error_msg = f"Rate limit exceeded for {provider}: {message}"
        if retry_after is not None:
            error_msg += f" (retry after {retry_after} seconds)"
        super().__init__(error_msg)


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
