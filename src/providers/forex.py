"""
Forex data provider using OANDA v20 API.

This module handles authentication, data fetching, and normalization
for foreign exchange currency pairs.
"""

from typing import List, Optional
from datetime import datetime, timedelta
import time

from ..models.ohlcv import OHLCVData, AssetClass
from ..providers.base import BaseDataProvider
from ..utils.config import get_config, OANDAConfig
from ..utils.logger import get_logger
from ..utils.exceptions import (
    AuthenticationError,
    DataFetchError,
    NormalizationError,
)

try:
    import oandapyV20
    from oandapyV20 import API
    from oandapyV20.endpoints import instruments
    from oandapyV20.exceptions import V20Error
    OANDA_AVAILABLE = True
except ImportError:
    OANDA_AVAILABLE = False
    API = None
    V20Error = Exception


class ForexProvider(BaseDataProvider):
    """
    Provider for forex data using OANDA v20 API.
    
    Supports all major and minor currency pairs, as well as metals and CFDs.
    """
    
    def __init__(self, oanda_config: Optional[OANDAConfig] = None):
        """
        Initialize forex provider.
        
        Args:
            oanda_config: Optional OANDA configuration
        """
        super().__init__(AssetClass.FOREX, "oanda")
        self.logger = get_logger("provider.forex")
        
        config = get_config()
        self.oanda_config = oanda_config or config.oanda
        self.client: Optional[API] = None
        self.account_id: Optional[str] = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with OANDA API.
        
        Returns:
            True if authentication successful
        
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            if not OANDA_AVAILABLE:
                raise AuthenticationError(
                    "OANDA library not installed. Install with: pip install oandapyV20"
                )
            
            if not self.oanda_config.api_key:
                raise AuthenticationError(
                    "OANDA API key not configured. Set OANDA_API_KEY environment variable."
                )
            
            # Initialize OANDA API client
            self.client = API(
                access_token=self.oanda_config.api_key,
                environment=self.oanda_config.environment,
            )
            
            # Get account ID if not provided
            if not self.oanda_config.account_id:
                # For practice accounts, we can use a default account ID
                # For live accounts, account ID is required
                if self.oanda_config.environment == "practice":
                    # Try to get accounts list
                    from oandapyV20.endpoints import accounts
                    r = accounts.AccountList()
                    self.client.request(r)
                    if r.response and "accounts" in r.response:
                        accounts_list = r.response["accounts"]
                        if accounts_list:
                            self.account_id = accounts_list[0]["id"]
                        else:
                            raise AuthenticationError("No accounts found")
                    else:
                        # Use a default practice account ID format
                        # In practice, you should get this from the accounts endpoint
                        raise AuthenticationError(
                            "Account ID required. Set OANDA_ACCOUNT_ID environment variable."
                        )
                else:
                    raise AuthenticationError(
                        "Account ID required for live environment. Set OANDA_ACCOUNT_ID environment variable."
                    )
            else:
                self.account_id = self.oanda_config.account_id
            
            # Test authentication with a simple request
            r = instruments.InstrumentsCandles(
                instrument="EUR_USD",
                params={"count": 1},
            )
            try:
                self.client.request(r)
            except V20Error as e:
                # If it's just a data error (not auth), we're good
                if "UNAUTHORIZED" in str(e) or "AUTHORIZATION" in str(e):
                    raise AuthenticationError(f"OANDA authentication failed: {e}")
            
            self._authenticated = True
            self.logger.info(f"Authenticated with OANDA ({self.oanda_config.environment} environment)")
            return True
        
        except Exception as e:
            self.logger.error(f"OANDA authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate with OANDA: {e}") from e
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data for a forex pair.
        
        Args:
            symbol: Currency pair (e.g., 'EUR_USD', 'GBP_USD', 'USD_JPY')
            timeframe: Timeframe (e.g., '5min', '15min', '1hour', '1day')
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
            return self._fetch_from_oanda(symbol, normalized_timeframe, start, end)
        
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise DataFetchError(f"Failed to fetch data: {e}") from e
    
    def _fetch_from_oanda(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCVData]:
        """Fetch data from OANDA."""
        if not self.client:
            raise DataFetchError("OANDA client not initialized")
        
        try:
            # Map timeframe to OANDA granularity
            granularity_map = {
                "1min": "M1",
                "5min": "M5",
                "15min": "M15",
                "30min": "M30",
                "1hour": "H1",
                "4hour": "H4",
                "1day": "D",
                "1week": "W",
                "1month": "M",
            }
            
            if timeframe not in granularity_map:
                raise DataFetchError(f"Unsupported timeframe for OANDA: {timeframe}")
            
            granularity = granularity_map[timeframe]
            
            # OANDA uses RFC3339 format for dates
            from_datetime = start.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
            to_datetime = end.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
            
            # Convert symbol format (EUR_USD -> EUR_USD for OANDA)
            oanda_symbol = symbol.replace("_", "_")
            
            # OANDA limits to 5000 candles per request, so we may need to paginate
            ohlcv_list = []
            current_start = start
            
            # Calculate max candles per request based on timeframe
            max_candles = 5000
            
            while current_start < end:
                try:
                    # Calculate end for this batch
                    batch_end = min(
                        current_start + timedelta(days=365),  # Max 1 year per request
                        end,
                    )
                    
                    params = {
                        "from": current_start.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                        "to": batch_end.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                        "granularity": granularity,
                    }
                    
                    r = instruments.InstrumentsCandles(
                        instrument=oanda_symbol,
                        params=params,
                    )
                    
                    self.client.request(r)
                    
                    if not r.response or "candles" not in r.response:
                        break
                    
                    candles = r.response["candles"]
                    
                    # Process candles
                    for candle in candles:
                        if candle["complete"]:  # Only process complete candles
                            try:
                                mid = candle["mid"]
                                ohlcv = OHLCVData(
                                    symbol=symbol,
                                    asset_class=AssetClass.FOREX,
                                    timestamp=datetime.fromisoformat(
                                        candle["time"].replace("Z", "+00:00")
                                    ),
                                    open=float(mid["o"]),
                                    high=float(mid["h"]),
                                    low=float(mid["l"]),
                                    close=float(mid["c"]),
                                    volume=int(candle["volume"]) if "volume" in candle else None,
                                    timeframe=timeframe,
                                    source="oanda",
                                    metadata={
                                        "bid_open": float(candle["bid"]["o"]) if "bid" in candle else None,
                                        "bid_high": float(candle["bid"]["h"]) if "bid" in candle else None,
                                        "bid_low": float(candle["bid"]["l"]) if "bid" in candle else None,
                                        "bid_close": float(candle["bid"]["c"]) if "bid" in candle else None,
                                        "ask_open": float(candle["ask"]["o"]) if "ask" in candle else None,
                                        "ask_high": float(candle["ask"]["h"]) if "ask" in candle else None,
                                        "ask_low": float(candle["ask"]["l"]) if "ask" in candle else None,
                                        "ask_close": float(candle["ask"]["c"]) if "ask" in candle else None,
                                    },
                                )
                                ohlcv_list.append(ohlcv)
                            except Exception as e:
                                self.logger.warning(f"Failed to normalize candle: {e}")
                                continue
                    
                    # Move to next batch
                    current_start = batch_end
                    
                    # Rate limiting: OANDA allows 2000 requests per 5 minutes
                    time.sleep(0.15)  # Small delay to avoid hitting rate limits
                
                except V20Error as e:
                    if "RATE_LIMIT" in str(e) or "429" in str(e):
                        self.logger.warning("Rate limit hit, waiting...")
                        time.sleep(1)
                        continue
                    else:
                        raise
            
            self.logger.info(f"Fetched {len(ohlcv_list)} bars for {symbol} from OANDA")
            return ohlcv_list
        
        except Exception as e:
            raise DataFetchError(f"OANDA fetch failed: {e}") from e
