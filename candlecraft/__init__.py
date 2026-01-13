"""
candlecraft - A clean, reusable Python library for fetching OHLCV data.

This library provides a minimal, stable API for fetching OHLCV data from
multiple providers (Binance, Twelve Data) and computing technical indicators.
"""

from candlecraft.models import OHLCV, AssetClass
from candlecraft.api import fetch_ohlcv, list_indicators

__version__ = "0.1.1"
__all__ = ["fetch_ohlcv", "list_indicators", "OHLCV", "AssetClass"]
