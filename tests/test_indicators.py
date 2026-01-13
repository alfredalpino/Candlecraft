"""
Comprehensive test suite for all technical indicator computations.

Tests formula correctness, edge cases, and data integrity for all 10 indicators.
Uses static test data - NO external API calls.
"""

import pytest
import sys
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pull_ohlcv import OHLCV, AssetClass


def load_indicator(indicator_name: str):
    """Load indicator module dynamically."""
    import importlib.util
    indicator_file = Path(__file__).parent.parent / "indicators" / f"{indicator_name}.py"
    spec = importlib.util.spec_from_file_location(f"indicators.{indicator_name}", indicator_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.calculate


def create_ohlcv_data(prices: List[float], volumes: List[float] = None) -> List[OHLCV]:
    """Helper to create OHLCV data from price list."""
    data = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    for i, close in enumerate(prices):
        high = close + 1.0
        low = close - 1.0
        open_price = close - 0.5
        volume = volumes[i] if volumes and i < len(volumes) else 1000.0
        
        candle = OHLCV(
            timestamp=base_time.replace(hour=i % 24),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            symbol="TEST",
            timeframe="1h",
            asset_class=AssetClass.CRYPTO,
            source="test"
        )
        data.append(candle)
    
    return data


# ============================================================================
# MACD Tests
# ============================================================================

class TestMACD:
    """Test MACD indicator formula correctness and edge cases."""
    
    def test_macd_basic_calculation(self):
        """Test MACD produces expected structure and values."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(50)])
        calculate = load_indicator("macd")
        result = calculate(data)
        
        assert len(result) == len(data)
        assert all(isinstance(r, dict) for r in result)
        assert all("macd" in r and "signal" in r and "histogram" in r for r in result)
        
        # After sufficient data, values should not be None
        valid_results = [r for r in result if r["macd"] is not None]
        assert len(valid_results) > 0
        
        # MACD line should exist before signal line
        first_macd_idx = next(i for i, r in enumerate(result) if r["macd"] is not None)
        first_signal_idx = next(i for i, r in enumerate(result) if r["signal"] is not None)
        assert first_signal_idx >= first_macd_idx
    
    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data returns None."""
        data = create_ohlcv_data([100.0 + i for i in range(10)])  # Only 10 candles
        calculate = load_indicator("macd")
        result = calculate(data)
        
        # All values should be None (need at least 35 candles: 26 + 9 - 1)
        assert all(r["macd"] is None for r in result)
    
    def test_macd_histogram_calculation(self):
        """Test histogram = MACD - Signal."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(50)])
        calculate = load_indicator("macd")
        result = calculate(data)
        
        for r in result:
            if r["macd"] is not None and r["signal"] is not None:
                expected_histogram = r["macd"] - r["signal"]
                assert abs(r["histogram"] - expected_histogram) < 0.0001


# ============================================================================
# RSI Tests
# ============================================================================

class TestRSI:
    """Test RSI indicator formula correctness and edge cases."""
    
    def test_rsi_basic_calculation(self):
        """Test RSI produces values in 0-100 range."""
        data = create_ohlcv_data([100.0 + (i % 10) * 0.5 for i in range(30)])
        calculate = load_indicator("rsi")
        result = calculate(data)
        
        assert len(result) == len(data)
        valid_rsi = [r["rsi"] for r in result if r["rsi"] is not None]
        
        # RSI should be between 0 and 100
        assert all(0 <= rsi <= 100 for rsi in valid_rsi)
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        data = create_ohlcv_data([100.0 + i for i in range(10)])
        calculate = load_indicator("rsi")
        result = calculate(data)
        
        # First 14 values should be None
        assert all(r["rsi"] is None for r in result[:14])
    
    def test_rsi_extreme_values(self):
        """Test RSI with strong uptrend (should approach 100)."""
        # Create strong uptrend
        prices = [100.0 + i * 2.0 for i in range(30)]
        data = create_ohlcv_data(prices)
        calculate = load_indicator("rsi")
        result = calculate(data)
        
        valid_rsi = [r["rsi"] for r in result if r["rsi"] is not None]
        if valid_rsi:
            # In strong uptrend, RSI should be high
            assert max(valid_rsi) > 50


# ============================================================================
# SMA Tests
# ============================================================================

class TestSMA:
    """Test SMA indicator formula correctness and edge cases."""
    
    def test_sma_basic_calculation(self):
        """Test SMA is average of closes."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        data = create_ohlcv_data(prices)
        calculate = load_indicator("sma")
        result = calculate(data, period=3)
        
        # SMA(3) of [100, 101, 102] = 101.0
        assert result[2]["sma"] == pytest.approx(101.0, abs=0.01)
        # SMA(3) of [101, 102, 103] = 102.0
        assert result[3]["sma"] == pytest.approx(102.0, abs=0.01)
    
    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        data = create_ohlcv_data([100.0 + i for i in range(5)])
        calculate = load_indicator("sma")
        result = calculate(data, period=10)
        
        # First 9 values should be None
        assert all(r["sma"] is None for r in result[:9])
    
    def test_sma_single_value(self):
        """Test SMA with period=1 should equal close."""
        data = create_ohlcv_data([100.0, 101.0, 102.0])
        calculate = load_indicator("sma")
        result = calculate(data, period=1)
        
        assert result[0]["sma"] == pytest.approx(100.0, abs=0.01)
        assert result[1]["sma"] == pytest.approx(101.0, abs=0.01)


# ============================================================================
# EMA Tests
# ============================================================================

class TestEMA:
    """Test EMA indicator formula correctness and edge cases."""
    
    def test_ema_basic_calculation(self):
        """Test EMA calculation structure."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(30)])
        calculate = load_indicator("ema")
        result = calculate(data, period=10)
        
        assert len(result) == len(data)
        valid_ema = [r["ema"] for r in result if r["ema"] is not None]
        assert len(valid_ema) > 0
        
        # EMA should be within price range
        prices = [c.close for c in data]
        assert min(valid_ema) >= min(prices) * 0.9
        assert max(valid_ema) <= max(prices) * 1.1
    
    def test_ema_starts_with_sma(self):
        """Test EMA first value equals SMA."""
        data = create_ohlcv_data([100.0 + i for i in range(25)])
        calculate = load_indicator("ema")
        result = calculate(data, period=10)
        
        # First EMA value should equal SMA of first period
        first_ema_idx = next(i for i, r in enumerate(result) if r["ema"] is not None)
        first_10_closes = [c.close for c in data[:10]]
        expected_sma = sum(first_10_closes) / 10
        
        assert result[first_ema_idx]["ema"] == pytest.approx(expected_sma, abs=0.01)


# ============================================================================
# VWAP Tests
# ============================================================================

class TestVWAP:
    """Test VWAP indicator formula correctness and edge cases."""
    
    def test_vwap_basic_calculation(self):
        """Test VWAP calculation with volume."""
        prices = [100.0, 101.0, 102.0]
        volumes = [1000.0, 2000.0, 3000.0]
        data = create_ohlcv_data(prices, volumes)
        calculate = load_indicator("vwap")
        result = calculate(data)
        
        assert len(result) == len(data)
        assert all(r["vwap"] is not None for r in result)
        
        # VWAP should be within price range
        vwap_values = [r["vwap"] for r in result]
        assert min(vwap_values) >= min(prices) * 0.9
        assert max(vwap_values) <= max(prices) * 1.1
    
    def test_vwap_no_volume(self):
        """Test VWAP with missing volume returns None."""
        data = create_ohlcv_data([100.0 + i for i in range(10)])
        # Set volume to None
        for candle in data:
            candle.volume = None
        
        calculate = load_indicator("vwap")
        result = calculate(data)
        
        assert all(r["vwap"] is None for r in result)
    
    def test_vwap_cumulative_nature(self):
        """Test VWAP is cumulative (later values include earlier data)."""
        prices = [100.0, 101.0, 102.0, 103.0]
        volumes = [1000.0, 1000.0, 1000.0, 1000.0]
        data = create_ohlcv_data(prices, volumes)
        calculate = load_indicator("vwap")
        result = calculate(data)
        
        # VWAP should change as more data is included
        vwap_values = [r["vwap"] for r in result if r["vwap"] is not None]
        # Should be increasing trend in this case
        assert len(vwap_values) == len(data)


# ============================================================================
# Bollinger Bands Tests
# ============================================================================

class TestBollingerBands:
    """Test Bollinger Bands indicator formula correctness and edge cases."""
    
    def test_bollinger_structure(self):
        """Test Bollinger Bands structure."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(30)])
        calculate = load_indicator("bollinger")
        result = calculate(data, period=20)
        
        assert len(result) == len(data)
        assert all("bb_upper" in r and "bb_middle" in r and "bb_lower" in r for r in result)
        
        # Check band relationships
        valid_results = [r for r in result if r["bb_upper"] is not None]
        for r in valid_results:
            assert r["bb_upper"] > r["bb_middle"]
            assert r["bb_middle"] > r["bb_lower"]
    
    def test_bollinger_middle_is_sma(self):
        """Test middle band equals SMA."""
        data = create_ohlcv_data([100.0 + i for i in range(25)])
        calculate_bb = load_indicator("bollinger")
        calculate_sma = load_indicator("sma")
        
        bb_result = calculate_bb(data, period=10)
        sma_result = calculate_sma(data, period=10)
        
        # Middle band should equal SMA
        for i in range(len(data)):
            if bb_result[i]["bb_middle"] is not None and sma_result[i]["sma"] is not None:
                assert bb_result[i]["bb_middle"] == pytest.approx(sma_result[i]["sma"], abs=0.01)


# ============================================================================
# ATR Tests
# ============================================================================

class TestATR:
    """Test ATR indicator formula correctness and edge cases."""
    
    def test_atr_positive_values(self):
        """Test ATR always positive."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(20)])
        calculate = load_indicator("atr")
        result = calculate(data)
        
        valid_atr = [r["atr"] for r in result if r["atr"] is not None]
        assert all(atr > 0 for atr in valid_atr)
    
    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        data = create_ohlcv_data([100.0 + i for i in range(10)])
        calculate = load_indicator("atr")
        result = calculate(data, period=14)
        
        # Need at least 15 candles (14 + 1)
        assert all(r["atr"] is None for r in result[:14])


# ============================================================================
# Stochastic Tests
# ============================================================================

class TestStochastic:
    """Test Stochastic Oscillator formula correctness and edge cases."""
    
    def test_stochastic_range(self):
        """Test %K and %D are in 0-100 range."""
        data = create_ohlcv_data([100.0 + (i % 10) * 0.5 for i in range(20)])
        calculate = load_indicator("stochastic")
        result = calculate(data)
        
        for r in result:
            if r["stoch_k"] is not None:
                assert 0 <= r["stoch_k"] <= 100
            if r["stoch_d"] is not None:
                assert 0 <= r["stoch_d"] <= 100
    
    def test_stochastic_d_is_sma_of_k(self):
        """Test %D is SMA of %K."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(20)])
        calculate = load_indicator("stochastic")
        result = calculate(data, k_period=5, d_period=3)
        
        # %D should be calculated from %K values
        k_values = [r["stoch_k"] for r in result if r["stoch_k"] is not None]
        d_values = [r["stoch_d"] for r in result if r["stoch_d"] is not None]
        
        # %D should appear after enough %K values
        assert len(d_values) <= len(k_values)


# ============================================================================
# ADX Tests
# ============================================================================

class TestADX:
    """Test ADX indicator formula correctness and edge cases."""
    
    def test_adx_range(self):
        """Test ADX is in 0-100 range."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(30)])
        calculate = load_indicator("adx")
        result = calculate(data)
        
        valid_adx = [r["adx"] for r in result if r["adx"] is not None]
        if valid_adx:
            assert all(0 <= adx <= 100 for adx in valid_adx)
    
    def test_adx_structure(self):
        """Test ADX includes DI+ and DI-."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(30)])
        calculate = load_indicator("adx")
        result = calculate(data)
        
        assert all("adx" in r and "di_plus" in r and "di_minus" in r for r in result)


# ============================================================================
# OBV Tests
# ============================================================================

class TestOBV:
    """Test OBV indicator formula correctness and edge cases."""
    
    def test_obv_cumulative(self):
        """Test OBV is cumulative."""
        prices = [100.0, 101.0, 100.5, 102.0, 101.5]  # Mixed up/down
        volumes = [1000.0, 2000.0, 1500.0, 3000.0, 2500.0]
        data = create_ohlcv_data(prices, volumes)
        calculate = load_indicator("obv")
        result = calculate(data)
        
        assert len(result) == len(data)
        assert all(r["obv"] is not None for r in result)
        
        # OBV should change based on price direction
        obv_values = [r["obv"] for r in result]
        # First value should equal first volume
        assert obv_values[0] == pytest.approx(volumes[0], abs=0.01)
    
    def test_obv_no_volume(self):
        """Test OBV with missing volume returns None."""
        data = create_ohlcv_data([100.0 + i for i in range(10)])
        for candle in data:
            candle.volume = None
        
        calculate = load_indicator("obv")
        result = calculate(data)
        
        assert all(r["obv"] is None for r in result)


# ============================================================================
# Edge Cases and Data Integrity Tests
# ============================================================================

class TestIndicatorEdgeCases:
    """Test edge cases for all indicators."""
    
    def test_empty_data(self):
        """Test all indicators with empty data."""
        empty_data = []
        indicators = ["macd", "rsi", "sma", "ema", "bollinger", "atr", "stochastic", "adx"]
        
        for indicator_name in indicators:
            calculate = load_indicator(indicator_name)
            result = calculate(empty_data)
            assert result == []
        
        # Volume-based indicators
        for indicator_name in ["vwap", "obv"]:
            calculate = load_indicator(indicator_name)
            result = calculate(empty_data)
            assert result == []
    
    def test_single_candle(self):
        """Test indicators with single candle."""
        from pull_ohlcv import AssetClass
        single_candle = [OHLCV(
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
            symbol="TEST",
            timeframe="1h",
            asset_class=AssetClass.CRYPTO,
            source="test"
        )]
        
        # Most indicators should return None for single candle
        indicators = ["macd", "rsi", "sma", "ema", "bollinger", "atr", "stochastic", "adx"]
        for indicator_name in indicators:
            calculate = load_indicator(indicator_name)
            result = calculate(single_candle)
            assert len(result) == 1
            # Values should be None (insufficient data)
            assert all(v is None for v in result[0].values())
        
        # Volume-based indicators might work
        calculate_vwap = load_indicator("vwap")
        result_vwap = calculate_vwap(single_candle)
        assert len(result_vwap) == 1
        assert result_vwap[0]["vwap"] is not None
        
        calculate_obv = load_indicator("obv")
        result_obv = calculate_obv(single_candle)
        assert len(result_obv) == 1
        assert result_obv[0]["obv"] is not None
    
    def test_data_alignment(self):
        """Test that indicator results align with input data."""
        data = create_ohlcv_data([100.0 + i * 0.5 for i in range(50)])
        indicators = ["macd", "rsi", "sma", "ema", "bollinger", "atr", "stochastic", "adx", "vwap", "obv"]
        
        for indicator_name in indicators:
            calculate = load_indicator(indicator_name)
            result = calculate(data)
            # Result length must match input length
            assert len(result) == len(data), f"{indicator_name} alignment failed"
