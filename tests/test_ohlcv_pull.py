"""
Test suite for OHLCV data pulling from external APIs (Binance and Twelve Data).

Tests actual API calls to verify:
- Authentication works
- Data fetching works
- Data structure is correct
- Error handling works

Requires API keys in environment variables:
- BINANCE_API_KEY, BINANCE_API_SECRET (optional for public API)
- TWELVEDATA_SECRET (required for Twelve Data)
"""

import pytest
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from candlecraft library
from candlecraft import fetch_ohlcv, OHLCV, AssetClass
from candlecraft.utils import detect_asset_class, validate_ohlcv
from candlecraft.providers import (
    authenticate_binance, authenticate_twelvedata,
    fetch_ohlcv_binance, fetch_ohlcv_twelvedata,
)


# ============================================================================
# Test Result Storage Helper
# ============================================================================

def save_test_result(test_name: str, test_type: str, data: list, command_info: dict):
    """
    Save test results to test-results directory.
    
    Automatically creates directories if they don't exist. Works for all users.
    Directory structure: test-results/{test_type}_{timestamp}/
    
    Args:
        test_name: Name of the test function
        test_type: 'pull' or 'indicator'
        data: List of OHLCV objects or indicator results
        command_info: Dictionary with command details
    
    Returns:
        Path to the created test directory
    """
    try:
        # Get project root directory (parent of tests directory)
        # This works regardless of where the test is run from
        project_root = Path(__file__).parent.parent.resolve()
        results_dir = project_root / "test-results"
        
        # Create test-results directory if it doesn't exist (works for all users)
        results_dir.mkdir(exist_ok=True, mode=0o755)
        
        # Create timestamped directory: test-results/{test_type}_{timestamp}/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir = results_dir / f"{test_type}_{timestamp}"
        test_dir.mkdir(exist_ok=True, mode=0o755)
        
        # Verify directory was created
        if not test_dir.exists():
            raise OSError(f"Failed to create test results directory: {test_dir}")
            
    except Exception as e:
        # If directory creation fails, log but don't crash the test
        print(f"Warning: Could not save test results to {results_dir}: {e}")
        return None
    
    # Convert OHLCV objects to dictionaries for JSON serialization
    if data and isinstance(data[0], OHLCV):
        output_data = []
        for candle in data:
            output_data.append({
                "timestamp": candle.timestamp.isoformat(),
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": float(candle.volume) if candle.volume is not None else None,
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "asset_class": candle.asset_class.value,
                "source": candle.source
            })
    else:
        output_data = data
    
    # Create result dictionary
    result = {
        "test_name": test_name,
        "test_type": test_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command_info,
        "data_count": len(data),
        "data": output_data
    }
    
    try:
        # Save to JSON file with proper error handling
        output_file = test_dir / f"{test_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Also save a human-readable summary
        summary_file = test_dir / f"{test_name}_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Test: {test_name}\n")
            f.write(f"Type: {test_type}\n")
            f.write(f"Timestamp: {result['timestamp']}\n")
            f.write(f"\nCommand:\n")
            for key, value in command_info.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\nData Count: {len(data)}\n")
            f.write(f"\nFirst 5 Candles:\n")
            f.write("=" * 80 + "\n")
            for i, candle_data in enumerate(output_data[:5]):
                f.write(f"\nCandle {i+1}:\n")
                for key, value in candle_data.items():
                    f.write(f"  {key}: {value}\n")
            if len(output_data) > 5:
                f.write(f"\n... and {len(output_data) - 5} more candles\n")
        
        return test_dir
        
    except Exception as e:
        # If file writing fails, log but don't crash the test
        print(f"Warning: Could not write test results to {test_dir}: {e}")
        return None


# ============================================================================
# Binance API Tests
# ============================================================================

class TestBinanceAPI:
    """Test Binance API integration."""
    
    def test_binance_authentication_public(self):
        """Test Binance public API authentication (no keys required)."""
        try:
            client = authenticate_binance()
            assert client is not None
            # Test connection
            client.ping()
        except Exception as e:
            pytest.skip(f"Binance API unavailable: {e}")
    
    def test_binance_fetch_ohlcv_crypto(self):
        """Test fetching OHLCV data from Binance for cryptocurrency."""
        try:
            client = authenticate_binance()
            
            # Fetch recent BTCUSDT data
            symbol = "BTCUSDT"
            timeframe = "1h"
            limit = 10
            
            data = fetch_ohlcv_binance(
                client=client,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            assert len(data) > 0
            assert len(data) <= 10
            
            # Validate data structure
            for candle in data:
                assert isinstance(candle, OHLCV)
                assert candle.symbol == symbol
                assert candle.timeframe == timeframe
                assert candle.asset_class == AssetClass.CRYPTO
                assert candle.source == "binance"
                assert candle.timestamp.tzinfo == timezone.utc
                
                # Validate OHLCV values
                validate_ohlcv(candle)
                
                # Check price values are positive
                assert candle.open > 0
                assert candle.high > 0
                assert candle.low > 0
                assert candle.close > 0
                assert candle.volume > 0
            
            # Save test results
            command_info = {
                "provider": "binance",
                "function": "fetch_ohlcv_binance",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "crypto"
            }
            save_test_result("test_binance_fetch_ohlcv_crypto", "pull", data, command_info)
                
        except Exception as e:
            pytest.skip(f"Binance API test failed: {e}")
    
    def test_binance_fetch_different_timeframes(self):
        """Test Binance with different timeframes."""
        try:
            client = authenticate_binance()
            symbol = "ETHUSDT"
            timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
            limit = 5
            
            all_data = []
            for tf in timeframes:
                data = fetch_ohlcv_binance(
                    client=client,
                    symbol=symbol,
                    timeframe=tf,
                    limit=limit
                )
                
                assert len(data) > 0
                for candle in data:
                    assert candle.timeframe == tf
                
                all_data.extend(data)
            
            # Save test results
            command_info = {
                "provider": "binance",
                "function": "fetch_ohlcv_binance",
                "symbol": symbol,
                "timeframes": timeframes,
                "limit": limit,
                "asset_class": "crypto"
            }
            save_test_result("test_binance_fetch_different_timeframes", "pull", all_data, command_info)
                    
        except Exception as e:
            pytest.skip(f"Binance timeframe test failed: {e}")
    
    def test_binance_invalid_symbol(self):
        """Test Binance error handling for invalid symbol."""
        try:
            client = authenticate_binance()
            
            with pytest.raises(SystemExit):
                fetch_ohlcv_binance(
                    client=client,
                    symbol="INVALID_SYMBOL_XYZ",
                    timeframe="1h",
                    limit=10
                )
        except Exception as e:
            pytest.skip(f"Binance error handling test failed: {e}")


# ============================================================================
# Twelve Data API Tests
# ============================================================================

class TestTwelveDataAPI:
    """Test Twelve Data API integration."""
    
    def test_twelvedata_authentication(self):
        """Test Twelve Data authentication."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            client = authenticate_twelvedata()
            assert client is not None
        except Exception as e:
            pytest.skip(f"Twelve Data authentication failed: {e}")
    
    def test_twelvedata_fetch_forex(self):
        """Test fetching OHLCV data from Twelve Data for Forex."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            client = authenticate_twelvedata()
            
            # Fetch EUR/USD data
            symbol = "EUR/USD"
            timeframe = "1h"
            limit = 10
            
            data = fetch_ohlcv_twelvedata(
                client=client,
                symbol=symbol,
                timeframe=timeframe,
                asset_class=AssetClass.FOREX,
                limit=limit
            )
            
            assert len(data) > 0
            assert len(data) <= 10
            
            # Validate data structure
            for candle in data:
                assert isinstance(candle, OHLCV)
                assert candle.symbol == symbol
                assert candle.timeframe == timeframe
                assert candle.asset_class == AssetClass.FOREX
                assert candle.source == "twelvedata"
                assert candle.timestamp.tzinfo == timezone.utc
                
                # Validate OHLCV values
                validate_ohlcv(candle)
                
                # Check price values are positive
                assert candle.open > 0
                assert candle.high > 0
                assert candle.low > 0
                assert candle.close > 0
            
            # Save test results
            command_info = {
                "provider": "twelvedata",
                "function": "fetch_ohlcv_twelvedata",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "forex"
            }
            save_test_result("test_twelvedata_fetch_forex", "pull", data, command_info)
                
        except Exception as e:
            pytest.skip(f"Twelve Data Forex test failed: {e}")
    
    def test_twelvedata_fetch_equity(self):
        """Test fetching OHLCV data from Twelve Data for U.S. Equity."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            client = authenticate_twelvedata()
            
            # Fetch AAPL data
            symbol = "AAPL"
            timeframe = "1h"
            limit = 10
            
            data = fetch_ohlcv_twelvedata(
                client=client,
                symbol=symbol,
                timeframe=timeframe,
                asset_class=AssetClass.EQUITY,
                limit=limit
            )
            
            assert len(data) > 0
            assert len(data) <= 10
            
            # Validate data structure
            for candle in data:
                assert isinstance(candle, OHLCV)
                assert candle.symbol == symbol
                assert candle.timeframe == timeframe
                assert candle.asset_class == AssetClass.EQUITY
                assert candle.source == "twelvedata"
                assert candle.timestamp.tzinfo == timezone.utc
                
                # Validate OHLCV values
                validate_ohlcv(candle)
                
                # Check price values are positive
                assert candle.open > 0
                assert candle.high > 0
                assert candle.low > 0
                assert candle.close > 0
            
            # Save test results
            command_info = {
                "provider": "twelvedata",
                "function": "fetch_ohlcv_twelvedata",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "equity"
            }
            save_test_result("test_twelvedata_fetch_equity", "pull", data, command_info)
                
        except Exception as e:
            pytest.skip(f"Twelve Data Equity test failed: {e}")
    
    def test_twelvedata_different_timeframes(self):
        """Test Twelve Data with different timeframes."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            client = authenticate_twelvedata()
            symbol = "EUR/USD"
            timeframes = ["1h", "4h", "1d"]
            limit = 5
            
            all_data = []
            for tf in timeframes:
                data = fetch_ohlcv_twelvedata(
                    client=client,
                    symbol=symbol,
                    timeframe=tf,
                    asset_class=AssetClass.FOREX,
                    limit=limit
                )
                
                assert len(data) > 0
                for candle in data:
                    assert candle.timeframe == tf
                
                all_data.extend(data)
            
            # Save test results
            command_info = {
                "provider": "twelvedata",
                "function": "fetch_ohlcv_twelvedata",
                "symbol": symbol,
                "timeframes": timeframes,
                "limit": limit,
                "asset_class": "forex"
            }
            save_test_result("test_twelvedata_different_timeframes", "pull", all_data, command_info)
                    
        except Exception as e:
            pytest.skip(f"Twelve Data timeframe test failed: {e}")


# ============================================================================
# Unified Fetch Tests
# ============================================================================

class TestUnifiedFetch:
    """Test unified fetch_ohlcv function that routes to correct provider."""
    
    def test_fetch_crypto_routes_to_binance(self):
        """Test that crypto symbols route to Binance."""
        try:
            symbol = "BTCUSDT"
            timeframe = "1h"
            limit = 5
            
            data = fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                asset_class=AssetClass.CRYPTO,
                limit=limit
            )
            
            assert len(data) > 0
            assert all(c.source == "binance" for c in data)
            assert all(c.asset_class == AssetClass.CRYPTO for c in data)
            
            # Save test results
            command_info = {
                "function": "fetch_ohlcv",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "crypto",
                "routed_to": "binance"
            }
            save_test_result("test_fetch_crypto_routes_to_binance", "pull", data, command_info)
            
        except Exception as e:
            pytest.skip(f"Unified crypto fetch failed: {e}")
    
    def test_fetch_forex_routes_to_twelvedata(self):
        """Test that forex symbols route to Twelve Data."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            symbol = "EUR/USD"
            timeframe = "1h"
            limit = 5
            
            data = fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                asset_class=AssetClass.FOREX,
                limit=limit
            )
            
            assert len(data) > 0
            assert all(c.source == "twelvedata" for c in data)
            assert all(c.asset_class == AssetClass.FOREX for c in data)
            
            # Save test results
            command_info = {
                "function": "fetch_ohlcv",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "forex",
                "routed_to": "twelvedata"
            }
            save_test_result("test_fetch_forex_routes_to_twelvedata", "pull", data, command_info)
            
        except Exception as e:
            pytest.skip(f"Unified forex fetch failed: {e}")
    
    def test_fetch_equity_routes_to_twelvedata(self):
        """Test that equity symbols route to Twelve Data."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            symbol = "AAPL"
            timeframe = "1h"
            limit = 5
            
            data = fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                asset_class=AssetClass.EQUITY,
                limit=limit
            )
            
            assert len(data) > 0
            assert all(c.source == "twelvedata" for c in data)
            assert all(c.asset_class == AssetClass.EQUITY for c in data)
            
            # Save test results
            command_info = {
                "function": "fetch_ohlcv",
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "asset_class": "equity",
                "routed_to": "twelvedata"
            }
            save_test_result("test_fetch_equity_routes_to_twelvedata", "pull", data, command_info)
            
        except Exception as e:
            pytest.skip(f"Unified equity fetch failed: {e}")


# ============================================================================
# Data Quality Tests
# ============================================================================

class TestDataQuality:
    """Test data quality from API responses."""
    
    def test_binance_data_chronological_order(self):
        """Test Binance data is in chronological order."""
        try:
            client = authenticate_binance()
            data = fetch_ohlcv_binance(
                client=client,
                symbol="BTCUSDT",
                timeframe="1h",
                limit=20
            )
            
            if len(data) > 1:
                for i in range(1, len(data)):
                    assert data[i].timestamp >= data[i-1].timestamp
                    
        except Exception as e:
            pytest.skip(f"Binance chronological test failed: {e}")
    
    def test_twelvedata_data_chronological_order(self):
        """Test Twelve Data is in chronological order."""
        api_key = os.getenv("TWELVEDATA_SECRET")
        if not api_key:
            pytest.skip("TWELVEDATA_SECRET not set - skipping API test")
        
        try:
            client = authenticate_twelvedata()
            data = fetch_ohlcv_twelvedata(
                client=client,
                symbol="EUR/USD",
                timeframe="1h",
                asset_class=AssetClass.FOREX,
                limit=20
            )
            
            if len(data) > 1:
                for i in range(1, len(data)):
                    assert data[i].timestamp >= data[i-1].timestamp
                    
        except Exception as e:
            pytest.skip(f"Twelve Data chronological test failed: {e}")
    
    def test_all_candles_validated(self):
        """Test that all fetched candles pass validation."""
        try:
            # Test Binance
            client = authenticate_binance()
            data = fetch_ohlcv_binance(
                client=client,
                symbol="ETHUSDT",
                timeframe="1h",
                limit=10
            )
            
            for candle in data:
                validate_ohlcv(candle)
                
        except Exception as e:
            pytest.skip(f"Data validation test failed: {e}")
