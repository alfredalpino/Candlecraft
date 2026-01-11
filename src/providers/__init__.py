"""
Data provider modules for different asset classes.

Each provider handles authentication, data fetching, and normalization
for a specific asset class and data source.
"""

from .base import BaseDataProvider
from .equities import EquitiesProvider
from .crypto import CryptoProvider
from .forex import ForexProvider

__all__ = [
    "BaseDataProvider",
    "EquitiesProvider",
    "CryptoProvider",
    "ForexProvider",
]
