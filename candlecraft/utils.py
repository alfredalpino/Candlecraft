"""
Utility functions for candlecraft library.
"""

from datetime import datetime, timezone
from typing import Optional
from candlecraft.models import OHLCV, AssetClass


def to_utc(ts: datetime) -> datetime:
    """Convert datetime to timezone-aware UTC datetime."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def validate_ohlcv(dp: OHLCV) -> None:
    """Validate OHLCV data invariants. Raises ValueError on invalid data."""
    if dp.high < dp.low:
        raise ValueError("Invalid OHLCV: high < low")
    if dp.high < max(dp.open, dp.close):
        raise ValueError("Invalid OHLCV: high < open/close")
    if dp.low > min(dp.open, dp.close):
        raise ValueError("Invalid OHLCV: low > open/close")
    if dp.open <= 0 or dp.close <= 0:
        raise ValueError("Invalid OHLCV: non-positive price")


def detect_asset_class(symbol: str) -> AssetClass:
    """
    Detect asset class from symbol format.
    
    Rules:
    - Crypto: Contains 'USDT', 'BTC', 'ETH' or similar patterns, no '/' or spaces
    - Forex: Contains '/' separator (e.g., EUR/USD)
    - Equity: Simple uppercase letters, no special separators (e.g., AAPL, MSFT)
    """
    symbol_upper = symbol.upper().strip()
    
    # Check for forex pattern (contains / or _)
    if '/' in symbol or '_' in symbol:
        return AssetClass.FOREX
    
    # Check for crypto patterns (ends with USDT, BTC, ETH, etc. or contains common crypto patterns)
    crypto_patterns = ['USDT', 'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOGE', 'XRP', 'DOT', 'LINK']
    if any(pattern in symbol_upper for pattern in crypto_patterns) and '/' not in symbol_upper:
        return AssetClass.CRYPTO
    
    # Default to equity (simple uppercase letters)
    return AssetClass.EQUITY


def normalize_symbol(symbol: str, asset_class: AssetClass) -> str:
    """Normalize symbol format based on asset class."""
    if asset_class == AssetClass.FOREX:
        return symbol.replace("_", "/").upper()
    elif asset_class == AssetClass.EQUITY:
        return symbol.upper().strip()
    else:  # CRYPTO
        return symbol.upper()


def get_default_timezone(asset_class: AssetClass) -> str:
    """Get default timezone for asset class."""
    if asset_class == AssetClass.EQUITY:
        return "America/New_York"
    elif asset_class == AssetClass.FOREX:
        return "Exchange"
    else:  # CRYPTO
        return "UTC"
