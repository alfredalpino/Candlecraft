"""
Unified database management module.

Handles all database interactions for storing normalized OHLCV data
from all asset classes in a consistent schema.
"""

from .manager import DatabaseManager

__all__ = ["DatabaseManager"]
