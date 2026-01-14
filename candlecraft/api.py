"""
Public API for candlecraft library.
"""

from datetime import datetime
from typing import List, Optional
from pathlib import Path
import importlib.util
import os

from candlecraft.models import OHLCV, AssetClass, Provider
from candlecraft.utils import detect_asset_class
from candlecraft.providers import (
    authenticate_binance,
    authenticate_twelvedata,
    fetch_ohlcv_binance,
    fetch_ohlcv_twelvedata,
    BINANCE_AVAILABLE,
    TWELVEDATA_AVAILABLE,
)


def is_provider_available(provider: Provider) -> bool:
    """
    Check if a provider is available (library installed and configured).
    
    Args:
        provider: Provider to check
    
    Returns:
        True if provider is available, False otherwise
    """
    if provider == Provider.BINANCE:
        if not BINANCE_AVAILABLE:
            return False
        # Binance can work without API keys (public API)
        return True
    elif provider == Provider.TWELVEDATA:
        if not TWELVEDATA_AVAILABLE:
            return False
        # Check if API key is set
        return os.getenv("TWELVEDATA_SECRET") is not None
    return False


def get_available_providers() -> List[Provider]:
    """
    Get list of available providers (installed and configured).
    
    Returns:
        List of available Provider enums
    """
    available = []
    if is_provider_available(Provider.BINANCE):
        available.append(Provider.BINANCE)
    if is_provider_available(Provider.TWELVEDATA):
        available.append(Provider.TWELVEDATA)
    return available


def _get_default_provider(asset_class: AssetClass) -> Optional[Provider]:
    """
    Get default provider for an asset class based on availability.
    
    Args:
        asset_class: Asset class to get provider for
    
    Returns:
        Default provider if available, None otherwise
    """
    if asset_class == AssetClass.CRYPTO:
        # Prefer Binance for crypto, fallback to Twelve Data
        if is_provider_available(Provider.BINANCE):
            return Provider.BINANCE
        elif is_provider_available(Provider.TWELVEDATA):
            return Provider.TWELVEDATA
    elif asset_class in (AssetClass.FOREX, AssetClass.EQUITY):
        # Twelve Data is the only option for forex/equity
        if is_provider_available(Provider.TWELVEDATA):
            return Provider.TWELVEDATA
    return None


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    asset_class: Optional[AssetClass] = None,
    provider: Optional[Provider] = None,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
    rate_limit_strategy: str = "raise",
) -> List[OHLCV]:
    """
    Unified function to fetch OHLCV data from appropriate provider.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT', 'EUR/USD', 'AAPL')
        timeframe: Time interval (e.g., '1h', '1d', '1m')
        asset_class: Asset class (auto-detected if None)
        provider: Provider to use (auto-selected if None based on availability)
        limit: Number of candles to fetch
        start: Start datetime (requires end)
        end: End datetime (requires start)
        timezone: Timezone for timestamps (Forex/Equities only)
        rate_limit_strategy: How to handle rate limits. Options:
            - "raise" (default): Raise RateLimitException when rate limit is hit
            - "sleep": Automatically wait and retry when rate limit is hit
    
    Returns:
        List of OHLCV objects
    
    Raises:
        ValueError: For invalid arguments, unsupported timeframes, or provider not available
        RuntimeError: For API errors or connection failures
        RateLimitException: When rate limit is exceeded (if rate_limit_strategy="raise")
    """
    if asset_class is None:
        asset_class = detect_asset_class(symbol)
    
    # Determine which provider to use
    if provider is None:
        provider = _get_default_provider(asset_class)
        if provider is None:
            available = get_available_providers()
            if not available:
                raise ValueError(
                    "No providers available. Please install and configure at least one provider:\n"
                    "- Binance: pip install python-binance (optional API keys)\n"
                    "- Twelve Data: pip install twelvedata and set TWELVEDATA_SECRET"
                )
            raise ValueError(
                f"No provider available for {asset_class.value}. "
                f"Available providers: {[p.value for p in available]}. "
                f"Please install and configure a compatible provider."
            )
    else:
        # User specified a provider, check if it's available
        if not is_provider_available(provider):
            if provider == Provider.BINANCE:
                raise ValueError(
                    "Binance provider is not available. "
                    "Install it with: pip install python-binance"
                )
            elif provider == Provider.TWELVEDATA:
                raise ValueError(
                    "Twelve Data provider is not available. "
                    "Install it with: pip install twelvedata and set TWELVEDATA_SECRET environment variable"
                )
        
        # Validate provider compatibility with asset class
        if asset_class == AssetClass.CRYPTO and provider == Provider.TWELVEDATA:
            # Twelve Data can support crypto, but we need to handle it
            pass  # Will be handled below
        elif asset_class in (AssetClass.FOREX, AssetClass.EQUITY) and provider == Provider.BINANCE:
            raise ValueError(
                f"Binance provider does not support {asset_class.value}. "
                f"Use Provider.TWELVEDATA for {asset_class.value} data."
            )
    
    # Fetch data using the selected provider
    if provider == Provider.BINANCE:
        if asset_class != AssetClass.CRYPTO:
            raise ValueError(
                f"Binance provider only supports CRYPTO asset class, got {asset_class.value}"
            )
        client = authenticate_binance()
        return fetch_ohlcv_binance(client, symbol, timeframe, limit, start, end)
    elif provider == Provider.TWELVEDATA:
        # Twelve Data supports all asset classes (crypto, forex, equity)
        client = authenticate_twelvedata()
        return fetch_ohlcv_twelvedata(
            client, symbol, timeframe, asset_class, limit, start, end, timezone, rate_limit_strategy
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def list_indicators(indicators_dir: Optional[Path] = None) -> List[str]:
    """
    List available indicator modules.
    
    Args:
        indicators_dir: Path to indicators directory (defaults to project indicators/)
    
    Returns:
        List of indicator names (without .py extension)
    """
    if indicators_dir is None:
        # Default to project indicators directory
        # This assumes the library is used within the project structure
        # For standalone use, users should provide the path
        project_root = Path(__file__).parent.parent.parent
        indicators_dir = project_root / "indicators"
    
    if not indicators_dir.exists():
        return []
    
    indicators = []
    for file in indicators_dir.glob("*.py"):
        if file.name != "__init__.py" and not file.name.startswith("_"):
            indicators.append(file.stem)
    
    return sorted(indicators)


def load_indicator(indicator_name: str, indicators_dir: Optional[Path] = None):
    """
    Load an indicator module dynamically.
    
    Args:
        indicator_name: Name of the indicator (e.g., 'macd')
        indicators_dir: Path to indicators directory (defaults to project indicators/)
    
    Returns:
        The indicator's calculate function
    
    Raises:
        FileNotFoundError: If indicator module not found
        AttributeError: If module doesn't export calculate function
    """
    if indicators_dir is None:
        project_root = Path(__file__).parent.parent.parent
        indicators_dir = project_root / "indicators"
    
    indicator_file = indicators_dir / f"{indicator_name}.py"
    
    if not indicator_file.exists():
        raise FileNotFoundError(
            f"Indicator module not found: {indicator_file}. "
            f"Expected file: {indicators_dir}/{indicator_name}.py"
        )
    
    try:
        spec = importlib.util.spec_from_file_location(f"indicators.{indicator_name}", indicator_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load indicator module: {indicator_name}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, "calculate"):
            raise AttributeError(
                f"Indicator module '{indicator_name}' does not export a 'calculate' function"
            )
        
        return module.calculate
    
    except Exception as e:
        raise ImportError(f"Error loading indicator module '{indicator_name}': {e}")
