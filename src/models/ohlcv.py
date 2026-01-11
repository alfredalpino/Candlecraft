"""
Normalized OHLCV data model.

This module defines the standard schema for OHLCV (Open, High, Low, Close, Volume)
data that all asset class providers must conform to. This ensures consistent
data representation across equities, crypto, and forex.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    """Enumeration of supported asset classes."""
    
    EQUITIES = "equities"
    CRYPTO = "crypto"
    FOREX = "forex"


@dataclass
class OHLCVData:
    """
    Normalized OHLCV data structure.
    
    All data providers must transform their raw data into this format before
    passing it to the database management module.
    
    Attributes:
        symbol: Trading symbol (e.g., 'AAPL', 'BTCUSDT', 'EUR_USD')
        asset_class: Asset class (equities, crypto, or forex)
        timestamp: Timestamp of the OHLCV bar
        open: Opening price
        high: Highest price during the period
        low: Lowest price during the period
        close: Closing price
        volume: Trading volume (None for forex if not available)
        timeframe: Timeframe string (e.g., '1min', '1hour', '1day')
        source: Data provider name (e.g., 'massive', 'binance', 'oanda')
        metadata: Optional additional metadata as dictionary
    """
    
    symbol: str
    asset_class: AssetClass
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timeframe: str = "1day"
    source: str = "unknown"
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert OHLCVData to dictionary for database insertion."""
        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class.value,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe,
            "source": self.source,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OHLCVData":
        """Create OHLCVData from dictionary."""
        return cls(
            symbol=data["symbol"],
            asset_class=AssetClass(data["asset_class"]),
            timestamp=data["timestamp"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data.get("volume"),
            timeframe=data.get("timeframe", "1day"),
            source=data.get("source", "unknown"),
            metadata=data.get("metadata"),
        )
