"""
Public API for candlecraft library.
"""

from datetime import datetime
from typing import List, Optional
from pathlib import Path
import importlib.util

from candlecraft.models import OHLCV, AssetClass
from candlecraft.utils import detect_asset_class
from candlecraft.providers import (
    authenticate_binance,
    authenticate_twelvedata,
    fetch_ohlcv_binance,
    fetch_ohlcv_twelvedata,
)


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    asset_class: Optional[AssetClass] = None,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
) -> List[OHLCV]:
    """
    Unified function to fetch OHLCV data from appropriate provider.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT', 'EUR/USD', 'AAPL')
        timeframe: Time interval (e.g., '1h', '1d', '1m')
        asset_class: Asset class (auto-detected if None)
        limit: Number of candles to fetch
        start: Start datetime (requires end)
        end: End datetime (requires start)
        timezone: Timezone for timestamps (Forex/Equities only)
    
    Returns:
        List of OHLCV objects
    
    Raises:
        ValueError: For invalid arguments or unsupported timeframes
        RuntimeError: For API errors or connection failures
    """
    if asset_class is None:
        asset_class = detect_asset_class(symbol)
    
    if asset_class == AssetClass.CRYPTO:
        client = authenticate_binance()
        return fetch_ohlcv_binance(client, symbol, timeframe, limit, start, end)
    else:
        client = authenticate_twelvedata()
        return fetch_ohlcv_twelvedata(
            client, symbol, timeframe, asset_class, limit, start, end, timezone
        )


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
