"""
Custom exception classes for the data pulling system.
"""


class DataPullerError(Exception):
    """Base exception for all data puller errors."""
    pass


class AuthenticationError(DataPullerError):
    """Raised when authentication with a data provider fails."""
    pass


class DataFetchError(DataPullerError):
    """Raised when data fetching fails."""
    pass


class NormalizationError(DataPullerError):
    """Raised when data normalization fails."""
    pass


class DatabaseError(DataPullerError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(DataPullerError):
    """Raised when configuration is invalid or missing."""
    pass
