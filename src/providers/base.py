"""
Base data provider interface.

All asset class providers must inherit from this base class and implement
the required methods for authentication, data fetching, and normalization.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..models.ohlcv import OHLCVData, AssetClass
from ..utils.logger import get_logger
from ..utils.exceptions import (
    AuthenticationError,
    DataFetchError,
    NormalizationError,
)


class BaseDataProvider(ABC):
    """
    Abstract base class for all data providers.
    
    This class defines the contract that all asset class providers must follow.
    Each provider is responsible for:
    1. Authenticating with the data source
    2. Fetching raw OHLCV data
    3. Normalizing data to the standard OHLCVData schema
    """
    
    def __init__(self, asset_class: AssetClass, source_name: str):
        """
        Initialize the base data provider.
        
        Args:
            asset_class: The asset class this provider handles
            source_name: Name of the data source (e.g., 'massive', 'binance', 'oanda')
        """
        self.asset_class = asset_class
        self.source_name = source_name
        self.logger = get_logger(f"provider.{source_name}")
        self._authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the data provider.
        
        Returns:
            True if authentication successful, False otherwise
        
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data for a symbol within a time range.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'BTCUSDT', 'EUR_USD')
            timeframe: Timeframe string (e.g., '1min', '1hour', '1day')
            start: Start datetime
            end: End datetime
        
        Returns:
            List of normalized OHLCVData objects
        
        Raises:
            DataFetchError: If data fetching fails
            NormalizationError: If data normalization fails
        """
        pass
    
    def normalize_timeframe(self, timeframe: str) -> str:
        """
        Normalize timeframe string to standard format.
        
        Standard formats: '1min', '5min', '15min', '30min', '1hour', '4hour', '1day', '1week', '1month'
        
        Args:
            timeframe: Input timeframe string
        
        Returns:
            Normalized timeframe string
        """
        timeframe_lower = timeframe.lower().strip()
        
        # Map common variations to standard format
        timeframe_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1hour",
            "4h": "4hour",
            "1d": "1day",
            "1w": "1week",
            "1mo": "1month",
            "1month": "1month",
            "daily": "1day",
            "hourly": "1hour",
            "minute": "1min",
        }
        
        return timeframe_map.get(timeframe_lower, timeframe_lower)
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol format for the asset class.
        
        Args:
            symbol: Trading symbol to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not symbol or not isinstance(symbol, str):
            return False
        return len(symbol.strip()) > 0
    
    def ensure_authenticated(self):
        """
        Ensure provider is authenticated before operations.
        
        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._authenticated:
            if not self.authenticate():
                raise AuthenticationError(
                    f"Failed to authenticate with {self.source_name}"
                )
