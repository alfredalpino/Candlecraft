"""
Equities data provider.

Supports multiple data sources:
- Massive.com (formerly Polygon.io) - Recommended for production
- Yahoo Finance - Free alternative for development/testing

This module handles authentication, data fetching, and normalization
for U.S. equities and indices.
"""

from typing import List, Optional
from datetime import datetime, timedelta
import time

from ..models.ohlcv import OHLCVData, AssetClass
from ..providers.base import BaseDataProvider
from ..utils.config import get_config, MassiveConfig, YahooFinanceConfig
from ..utils.logger import get_logger
from ..utils.exceptions import (
    AuthenticationError,
    DataFetchError,
    NormalizationError,
)

try:
    from massive import RESTClient
    MASSIVE_AVAILABLE = True
except ImportError:
    MASSIVE_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class EquitiesProvider(BaseDataProvider):
    """
    Provider for U.S. equities and indices data.
    
    Supports both Massive.com (production) and Yahoo Finance (development).
    Automatically falls back to Yahoo Finance if Massive.com is not configured.
    """
    
    def __init__(
        self,
        source: str = "auto",  # "massive", "yahoo", or "auto"
        massive_config: Optional[MassiveConfig] = None,
        yahoo_config: Optional[YahooFinanceConfig] = None,
    ):
        """
        Initialize equities provider.
        
        Args:
            source: Data source to use ('massive', 'yahoo', or 'auto' for auto-detection)
            massive_config: Optional Massive.com configuration
            yahoo_config: Optional Yahoo Finance configuration
        """
        super().__init__(AssetClass.EQUITIES, "equities")
        self.logger = get_logger("provider.equities")
        
        config = get_config()
        self.massive_config = massive_config or config.massive
        self.yahoo_config = yahoo_config or config.yahoo_finance
        
        # Determine which source to use
        if source == "auto":
            if MASSIVE_AVAILABLE and self.massive_config.api_key:
                self.source = "massive"
                self.source_name = "massive"
            elif YFINANCE_AVAILABLE:
                self.source = "yahoo"
                self.source_name = "yahoo_finance"
            else:
                raise DataFetchError(
                    "No equities data source available. Install 'massive' or 'yfinance'."
                )
        else:
            self.source = source
            self.source_name = source
        
        self.client: Optional[RESTClient] = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with the selected data provider.
        
        Returns:
            True if authentication successful
        
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if self.source == "massive":
                if not MASSIVE_AVAILABLE:
                    raise AuthenticationError(
                        "Massive.com library not installed. Install with: pip install massive"
                    )
                
                if not self.massive_config.api_key:
                    raise AuthenticationError(
                        "Massive.com API key not configured. Set MASSIVE_API_KEY environment variable."
                    )
                
                self.client = RESTClient(self.massive_config.api_key)
                # Test authentication with a simple request
                # Note: Massive.com doesn't have explicit auth endpoint, so we'll test on first fetch
                self._authenticated = True
                self.logger.info("Authenticated with Massive.com")
                return True
            
            elif self.source == "yahoo":
                if not YFINANCE_AVAILABLE:
                    raise AuthenticationError(
                        "Yahoo Finance library not installed. Install with: pip install yfinance"
                    )
                
                # Yahoo Finance doesn't require authentication
                self._authenticated = True
                self.logger.info("Using Yahoo Finance (no authentication required)")
                return True
            
            else:
                raise AuthenticationError(f"Unknown source: {self.source}")
        
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {e}") from e
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data for an equity symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'SPY', 'QQQ')
            timeframe: Timeframe (e.g., '1min', '1hour', '1day')
            start: Start datetime
            end: End datetime
        
        Returns:
            List of normalized OHLCVData objects
        
        Raises:
            DataFetchError: If data fetching fails
            NormalizationError: If data normalization fails
        """
        self.ensure_authenticated()
        
        if not self.validate_symbol(symbol):
            raise DataFetchError(f"Invalid symbol: {symbol}")
        
        normalized_timeframe = self.normalize_timeframe(timeframe)
        
        try:
            if self.source == "massive":
                return self._fetch_from_massive(symbol, normalized_timeframe, start, end)
            elif self.source == "yahoo":
                return self._fetch_from_yahoo(symbol, normalized_timeframe, start, end)
            else:
                raise DataFetchError(f"Unknown source: {self.source}")
        
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise DataFetchError(f"Failed to fetch data: {e}") from e
    
    def _fetch_from_massive(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """Fetch data from Massive.com."""
        if not self.client:
            raise DataFetchError("Massive.com client not initialized")
        
        try:
            # Map timeframe to Massive.com format
            timeframe_map = {
                "1min": (1, "minute"),
                "5min": (5, "minute"),
                "15min": (15, "minute"),
                "30min": (30, "minute"),
                "1hour": (1, "hour"),
                "4hour": (4, "hour"),
                "1day": (1, "day"),
            }
            
            if timeframe not in timeframe_map:
                raise DataFetchError(f"Unsupported timeframe for Massive.com: {timeframe}")
            
            multiplier, timespan = timeframe_map[timeframe]
            
            # Format dates for Massive.com API
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            
            # Fetch aggregates
            aggs = self.client.list_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start_str,
                to=end_str,
                limit=50000,  # Maximum limit
            )
            
            if not aggs or not hasattr(aggs, "results"):
                self.logger.warning(f"No data returned for {symbol}")
                return []
            
            # Normalize data
            ohlcv_list = []
            for agg in aggs.results:
                try:
                    ohlcv = OHLCVData(
                        symbol=symbol,
                        asset_class=AssetClass.EQUITIES,
                        timestamp=datetime.fromtimestamp(agg.timestamp / 1000),
                        open=float(agg.open),
                        high=float(agg.high),
                        low=float(agg.low),
                        close=float(agg.close),
                        volume=float(agg.volume) if hasattr(agg, "volume") else None,
                        timeframe=timeframe,
                        source="massive",
                        metadata={"vwap": getattr(agg, "vwap", None)},
                    )
                    ohlcv_list.append(ohlcv)
                except Exception as e:
                    self.logger.warning(f"Failed to normalize data point: {e}")
                    continue
            
            self.logger.info(f"Fetched {len(ohlcv_list)} bars for {symbol} from Massive.com")
            return ohlcv_list
        
        except Exception as e:
            raise DataFetchError(f"Massive.com fetch failed: {e}") from e
    
    def _fetch_from_yahoo(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """Fetch data from Yahoo Finance."""
        try:
            # Map timeframe to yfinance interval
            interval_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "1hour": "1h",
                "1day": "1d",
                "1week": "1wk",
                "1month": "1mo",
            }
            
            if timeframe not in interval_map:
                raise DataFetchError(f"Unsupported timeframe for Yahoo Finance: {timeframe}")
            
            interval = interval_map[timeframe]
            
            # Fetch data
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=True,
                prepost=False,
            )
            
            if df.empty:
                self.logger.warning(f"No data returned for {symbol}")
                return []
            
            # Normalize data
            ohlcv_list = []
            for timestamp, row in df.iterrows():
                try:
                    ohlcv = OHLCVData(
                        symbol=symbol,
                        asset_class=AssetClass.EQUITIES,
                        timestamp=timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row["Volume"]) if "Volume" in row else None,
                        timeframe=timeframe,
                        source="yahoo_finance",
                        metadata={},
                    )
                    ohlcv_list.append(ohlcv)
                except Exception as e:
                    self.logger.warning(f"Failed to normalize data point: {e}")
                    continue
            
            self.logger.info(f"Fetched {len(ohlcv_list)} bars for {symbol} from Yahoo Finance")
            return ohlcv_list
        
        except Exception as e:
            raise DataFetchError(f"Yahoo Finance fetch failed: {e}") from e
