"""
candlecraft - A clean, reusable Python library for fetching OHLCV data.

This library provides a minimal, stable API for fetching OHLCV data from
multiple providers (Binance, Twelve Data) and computing technical indicators.
"""

from candlecraft.models import OHLCV, AssetClass, Provider, RateLimitException
from candlecraft.api import fetch_ohlcv, list_indicators, get_available_providers, is_provider_available

__version__ = "0.1.4"
__all__ = [
    "fetch_ohlcv",
    "list_indicators",
    "OHLCV",
    "AssetClass",
    "Provider",
    "RateLimitException",
    "get_available_providers",
    "is_provider_available",
]
