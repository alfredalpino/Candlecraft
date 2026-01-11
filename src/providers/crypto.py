"""
Crypto data provider using Binance API.

This module handles authentication, data fetching, and normalization
for cryptocurrency trading pairs.
"""

from typing import List, Optional
from datetime import datetime, timedelta
import time

from ..models.ohlcv import OHLCVData, AssetClass
from ..providers.base import BaseDataProvider
from ..utils.config import get_config, BinanceConfig
from ..utils.logger import get_logger
from ..utils.exceptions import (
    AuthenticationError,
    DataFetchError,
    NormalizationError,
)

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    Client = None
    BinanceAPIException = Exception


class CryptoProvider(BaseDataProvider):
    """
    Provider for cryptocurrency data using Binance API.
    
    Supports both spot and futures markets. No API key required for public data,
    but API key can be provided for higher rate limits.
    """
    
    def __init__(self, binance_config: Optional[BinanceConfig] = None):
        """
        Initialize crypto provider.
        
        Args:
            binance_config: Optional Binance configuration
        """
        super().__init__(AssetClass.CRYPTO, "binance")
        self.logger = get_logger("provider.crypto")
        
        config = get_config()
        self.binance_config = binance_config or config.binance
        self.client: Optional[Client] = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Binance API.
        
        Returns:
            True if authentication successful
        
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if not BINANCE_AVAILABLE:
                raise AuthenticationError(
                    "Binance library not installed. Install with: pip install python-binance"
                )
            
            # Binance allows public data access without API key
            # API key is optional but recommended for higher rate limits
            if self.binance_config.api_key and self.binance_config.api_secret:
                self.client = Client(
                    api_key=self.binance_config.api_key,
                    api_secret=self.binance_config.api_secret,
                    testnet=self.binance_config.testnet,
                )
                self.logger.info("Authenticated with Binance API (with API key)")
            else:
                self.client = Client(testnet=self.binance_config.testnet)
                self.logger.info("Using Binance API (public access, no API key)")
            
            # Test connection
            self.client.ping()
            self._authenticated = True
            return True
        
        except Exception as e:
            self.logger.error(f"Binance authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate with Binance: {e}") from e
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data for a cryptocurrency pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT', 'ETHUSDT')
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
            return self._fetch_from_binance(symbol, normalized_timeframe, start, end)
        
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise DataFetchError(f"Failed to fetch data: {e}") from e
    
    def _fetch_from_binance(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """Fetch data from Binance."""
        if not self.client:
            raise DataFetchError("Binance client not initialized")
        
        try:
            # Map timeframe to Binance kline interval
            interval_map = {
                "1min": Client.KLINE_INTERVAL_1MINUTE,
                "5min": Client.KLINE_INTERVAL_5MINUTE,
                "15min": Client.KLINE_INTERVAL_15MINUTE,
                "30min": Client.KLINE_INTERVAL_30MINUTE,
                "1hour": Client.KLINE_INTERVAL_1HOUR,
                "4hour": Client.KLINE_INTERVAL_4HOUR,
                "1day": Client.KLINE_INTERVAL_1DAY,
                "1week": Client.KLINE_INTERVAL_1WEEK,
                "1month": Client.KLINE_INTERVAL_1MONTH,
            }
            
            if timeframe not in interval_map:
                raise DataFetchError(f"Unsupported timeframe for Binance: {timeframe}")
            
            interval = interval_map[timeframe]
            
            # Binance requires timestamps in milliseconds
            start_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000)
            
            # Fetch klines
            # Binance limits to 1000 klines per request, so we need to paginate
            ohlcv_list = []
            current_start = start_ms
            
            while current_start < end_ms:
                try:
                    klines = self.client.get_klines(
                        symbol=symbol.upper(),
                        interval=interval,
                        startTime=current_start,
                        endTime=end_ms,
                        limit=1000,
                    )
                    
                    if not klines:
                        break
                    
                    # Process klines
                    for kline in klines:
                        try:
                            ohlcv = OHLCVData(
                                symbol=symbol.upper(),
                                asset_class=AssetClass.CRYPTO,
                                timestamp=datetime.fromtimestamp(kline[0] / 1000),
                                open=float(kline[1]),
                                high=float(kline[2]),
                                low=float(kline[3]),
                                close=float(kline[4]),
                                volume=float(kline[5]),
                                timeframe=timeframe,
                                source="binance",
                                metadata={
                                    "quote_volume": float(kline[7]),
                                    "trades": int(kline[8]),
                                    "taker_buy_base": float(kline[9]),
                                    "taker_buy_quote": float(kline[10]),
                                },
                            )
                            ohlcv_list.append(ohlcv)
                        except Exception as e:
                            self.logger.warning(f"Failed to normalize kline: {e}")
                            continue
                    
                    # Update start time for next batch
                    if len(klines) < 1000:
                        break
                    
                    # Move to next batch (use last kline's close time)
                    current_start = klines[-1][0] + 1
                    
                    # Rate limiting: Binance allows 1200 requests per minute
                    time.sleep(0.05)  # Small delay to avoid hitting rate limits
                
                except BinanceAPIException as e:
                    if e.code == -1003:  # Too many requests
                        self.logger.warning("Rate limit hit, waiting...")
                        time.sleep(1)
                        continue
                    else:
                        raise
            
            self.logger.info(f"Fetched {len(ohlcv_list)} bars for {symbol} from Binance")
            return ohlcv_list
        
        except Exception as e:
            raise DataFetchError(f"Binance fetch failed: {e}") from e
