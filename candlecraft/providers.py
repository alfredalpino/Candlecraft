"""
Provider implementations for fetching OHLCV data.
"""

import logging
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from candlecraft.models import OHLCV, AssetClass, RateLimitException
from candlecraft.utils import get_default_timezone, normalize_symbol, to_utc, validate_ohlcv

logger = logging.getLogger(__name__)

# Import providers
if TYPE_CHECKING:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from twelvedata import TDClient

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    Client = Any  # type: ignore
    BinanceAPIException = Exception  # type: ignore

try:
    from twelvedata import TDClient
    TWELVEDATA_AVAILABLE = True
except ImportError:
    TWELVEDATA_AVAILABLE = False
    TDClient = Any  # type: ignore


# Rate limiting strategy types
RATE_LIMIT_RAISE = "raise"
RATE_LIMIT_SLEEP = "sleep"


def authenticate_binance():
    """Authenticate with Binance API."""
    if not BINANCE_AVAILABLE:
        raise ImportError(
            "python-binance library not installed. "
            "Install it with: pip install python-binance"
        )

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

    if api_key and api_secret:
        try:
            client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
            logger.info("Authenticated with Binance API (testnet=%s)", testnet)
            return client
        except Exception as e:
            raise RuntimeError(f"Binance authentication failed: {e}") from e

    try:
        client = Client(testnet=testnet)
        logger.info("Using Binance public API (no authentication required)")
        logger.debug(
            "For higher rate limits, set BINANCE_API_KEY and BINANCE_API_SECRET"
        )
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Binance client: {e}") from e


def authenticate_twelvedata():
    """Authenticate with Twelve Data API."""
    if not TWELVEDATA_AVAILABLE:
        raise ImportError(
            "twelvedata library not installed. "
            "Install it with: pip install twelvedata"
        )

    api_key = os.getenv("TWELVEDATA_SECRET")

    if not api_key:
        raise ValueError(
            "TWELVEDATA_SECRET environment variable not set. "
            "Set it in your .env file or export it as an environment variable."
        )

    try:
        client = TDClient(apikey=api_key)
        logger.info("Authenticated with Twelve Data API")
        return client
    except Exception as e:
        raise RuntimeError(f"Twelve Data authentication failed: {e}") from e


def fetch_ohlcv_binance(
    client: Client,
    symbol: str,
    timeframe: str,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[OHLCV]:
    """Fetch OHLCV data from Binance."""
    interval_map = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "1w": Client.KLINE_INTERVAL_1WEEK,
        "1M": Client.KLINE_INTERVAL_1MONTH,
    }

    if timeframe not in interval_map:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. "
            f"Supported: {', '.join(interval_map.keys())}"
        )

    interval = interval_map[timeframe]
    symbol_upper = symbol.upper()

    try:
        client.ping()
    except Exception as e:
        raise ConnectionError(f"Binance connection test failed: {e}") from e

    try:
        if limit:
            if limit > 1000:
                logger.warning(
                    "Binance limit is 1000 candles per request; using 1000 (requested %s)",
                    limit,
                )
                limit = 1000

            logger.info(
                "Fetching %s candles for %s (%s) from Binance",
                limit,
                symbol_upper,
                timeframe,
            )
            klines = client.get_klines(
                symbol=symbol_upper,
                interval=interval,
                limit=limit,
            )
        elif start and end:
            start_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000)

            logger.info(
                "Fetching %s (%s) from %s to %s from Binance",
                symbol_upper,
                timeframe,
                start,
                end,
            )

            all_klines = []
            current_start = start_ms

            while current_start < end_ms:
                klines = client.get_klines(
                    symbol=symbol_upper,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_ms,
                    limit=1000,
                )

                if not klines:
                    break

                all_klines.extend(klines)

                if len(klines) < 1000:
                    break

                current_start = klines[-1][0] + 1

            klines = all_klines
        else:
            raise ValueError("Either limit or both start and end must be provided")

        if not klines:
            raise ValueError(f"No data returned for {symbol_upper}")

        ohlcv_data = []
        for kline in klines:
            ohlcv = OHLCV(
                timestamp=to_utc(datetime.fromtimestamp(kline[0] / 1000)),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5]),
                symbol=symbol_upper,
                timeframe=timeframe,
                asset_class=AssetClass.CRYPTO,
                source="binance",
            )
            validate_ohlcv(ohlcv)
            ohlcv_data.append(ohlcv)

        logger.info("Fetched %s candles from Binance for %s", len(ohlcv_data), symbol_upper)
        return ohlcv_data

    except BinanceAPIException as e:
        raise RuntimeError(f"Binance API error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error fetching data: {e}") from e


def fetch_ohlcv_twelvedata(
    client: TDClient,
    symbol: str,
    timeframe: str,
    asset_class: AssetClass,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
    rate_limit_strategy: str = RATE_LIMIT_RAISE,
) -> List[OHLCV]:
    """Fetch OHLCV data from Twelve Data."""
    interval_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1day",
        "1w": "1week",
        "1M": "1month",
    }

    if timeframe not in interval_map:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. "
            f"Supported: {', '.join(interval_map.keys())}"
        )

    interval = interval_map[timeframe]
    symbol_normalized = normalize_symbol(symbol, asset_class)
    default_timezone = timezone if timezone else get_default_timezone(asset_class)

    def _is_rate_limit_error(error: Exception) -> bool:
        """Check if an exception is a rate limit error."""
        error_msg = str(error)
        error_str_lower = error_msg.lower()
        error_type = type(error).__name__.lower()

        rate_limit_indicators = [
            "429",
            "rate limit",
            "rate_limit",
            "too many requests",
            "quota exceeded",
            "quota_exceeded",
        ]

        if any(indicator in error_str_lower for indicator in rate_limit_indicators):
            return True

        if any(indicator in error_type for indicator in rate_limit_indicators):
            return True

        if hasattr(error, "status_code") and error.status_code == 429:
            return True

        if hasattr(error, "code") and error.code == 429:
            return True

        return False

    def _extract_retry_after(error: Exception) -> Optional[float]:
        """Extract retry-after duration from error if available."""
        if hasattr(error, "retry_after"):
            try:
                return float(error.retry_after)
            except (ValueError, TypeError):
                pass

        if hasattr(error, "headers"):
            headers = error.headers
            if isinstance(headers, dict):
                retry_after = headers.get("Retry-After") or headers.get("retry-after")
                if retry_after:
                    try:
                        return float(retry_after)
                    except (ValueError, TypeError):
                        pass

        error_msg = str(error)
        match = re.search(r"retry[_\s-]?after[:\s]+(\d+)", error_msg, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                pass

        return 60.0

    def _handle_rate_limit_error(error: Exception) -> None:
        """Handle rate limit errors based on strategy."""
        if not _is_rate_limit_error(error):
            raise error

        error_msg = str(error)
        retry_after = _extract_retry_after(error)

        if rate_limit_strategy == RATE_LIMIT_SLEEP and retry_after is not None:
            logger.warning(
                "Twelve Data rate limit encountered; waiting %.1f seconds before retry",
                retry_after,
            )
            time.sleep(retry_after)
        else:
            raise RateLimitException(
                provider="twelvedata",
                message=error_msg,
                retry_after=retry_after,
            )

    try:
        if limit:
            logger.info(
                "Fetching %s candles for %s (%s) from Twelve Data",
                limit,
                symbol_normalized,
                timeframe,
            )

            try:
                ts = client.time_series(
                    symbol=symbol_normalized,
                    interval=interval,
                    outputsize=limit,
                    timezone=default_timezone,
                )
                df = ts.as_pandas()
            except Exception as e:
                _handle_rate_limit_error(e)
                ts = client.time_series(
                    symbol=symbol_normalized,
                    interval=interval,
                    outputsize=limit,
                    timezone=default_timezone,
                )
                df = ts.as_pandas()

        elif start and end:
            logger.info(
                "Fetching %s (%s) from %s to %s from Twelve Data",
                symbol_normalized,
                timeframe,
                start,
                end,
            )

            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            try:
                ts = client.time_series(
                    symbol=symbol_normalized,
                    interval=interval,
                    start_date=start_str,
                    end_date=end_str,
                    timezone=default_timezone,
                )
                df = ts.as_pandas()
            except Exception as e:
                _handle_rate_limit_error(e)
                ts = client.time_series(
                    symbol=symbol_normalized,
                    interval=interval,
                    start_date=start_str,
                    end_date=end_str,
                    timezone=default_timezone,
                )
                df = ts.as_pandas()

        else:
            raise ValueError("Either limit or both start and end must be provided")

        if df.empty:
            raise ValueError(f"No data returned for {symbol_normalized}")

        ohlcv_data = []
        for timestamp, row in df.iterrows():
            try:
                ts = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
                ohlcv = OHLCV(
                    timestamp=to_utc(ts),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]) if "volume" in row else None,
                    symbol=symbol_normalized,
                    timeframe=timeframe,
                    asset_class=asset_class,
                    source="twelvedata",
                )
                validate_ohlcv(ohlcv)
                ohlcv_data.append(ohlcv)
            except ValueError:
                raise
            except Exception as e:
                logger.warning("Failed to process Twelve Data row: %s", e)
                continue

        logger.info(
            "Fetched %s candles from Twelve Data for %s",
            len(ohlcv_data),
            symbol_normalized,
        )
        return ohlcv_data

    except RateLimitException:
        raise
    except Exception as e:
        raise RuntimeError(f"Error fetching data: {e}") from e
