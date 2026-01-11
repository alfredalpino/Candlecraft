"""
Configuration management module.

Handles loading configuration from environment variables and config files.
Supports different environments (development, production, testing).
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, use system environment variables


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    
    host: str = "localhost"
    port: int = 5432
    database: str = "market_data"
    user: str = "postgres"
    password: str = ""
    dialect: str = "postgresql"  # postgresql, sqlite, mysql
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load database config from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "market_data"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            dialect=os.getenv("DB_DIALECT", "postgresql"),
        )


@dataclass
class ProviderConfig:
    """Base configuration for data providers."""
    
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class MassiveConfig(ProviderConfig):
    """Massive.com (formerly Polygon.io) configuration."""
    
    api_key: Optional[str] = field(default=None, init=False)
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("MASSIVE_API_KEY")


@dataclass
class YahooFinanceConfig(ProviderConfig):
    """Yahoo Finance configuration (no API key required)."""
    pass


@dataclass
class BinanceConfig(ProviderConfig):
    """Binance API configuration."""
    
    api_key: Optional[str] = field(default=None, init=False)
    api_secret: Optional[str] = field(default=None, init=False)
    testnet: bool = False
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("BINANCE_API_KEY")
        if self.api_secret is None:
            self.api_secret = os.getenv("BINANCE_API_SECRET")
        self.testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"


@dataclass
class OANDAConfig(ProviderConfig):
    """OANDA API configuration."""
    
    api_key: Optional[str] = field(default=None, init=False)
    account_id: Optional[str] = field(default=None, init=False)
    environment: str = "practice"  # practice or live
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("OANDA_API_KEY")
        if self.account_id is None:
            self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice")


@dataclass
class Config:
    """
    Main configuration class.
    
    Loads all configuration from environment variables with sensible defaults.
    """
    
    database: DatabaseConfig = field(default_factory=DatabaseConfig.from_env)
    massive: MassiveConfig = field(default_factory=MassiveConfig)
    yahoo_finance: YahooFinanceConfig = field(default_factory=YahooFinanceConfig)
    binance: BinanceConfig = field(default_factory=BinanceConfig)
    oanda: OANDAConfig = field(default_factory=OANDAConfig)
    
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Optional[str] = field(default_factory=lambda: os.getenv("LOG_FILE"))
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment."""
        return cls()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
