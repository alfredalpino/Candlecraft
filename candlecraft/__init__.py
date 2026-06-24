"""
candlecraft - A clean, reusable Python library for fetching OHLCV data.

This library provides a minimal, stable API for fetching OHLCV data from
multiple providers (Binance, Twelve Data) and computing technical indicators.
"""

from candlecraft.api import (
    fetch_ohlcv,
    get_available_providers,
    is_provider_available,
    list_indicators,
    load_indicator,
)
from candlecraft.models import OHLCV, AssetClass, Provider, RateLimitException

__version__ = "0.2.0"
__all__ = [
    "fetch_ohlcv",
    "list_indicators",
    "load_indicator",
    "OHLCV",
    "AssetClass",
    "Provider",
    "RateLimitException",
    "get_available_providers",
    "is_provider_available",
]
