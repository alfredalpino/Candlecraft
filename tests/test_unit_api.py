"""Unit tests for candlecraft public API and utilities (no live API calls)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from candlecraft import (
    OHLCV,
    AssetClass,
    Provider,
    RateLimitException,
    fetch_ohlcv,
    list_indicators,
    load_indicator,
)
from candlecraft.api import is_provider_available
from candlecraft.providers import fetch_ohlcv_binance, fetch_ohlcv_twelvedata
from candlecraft.utils import detect_asset_class, validate_ohlcv


def _sample_candle(close: float = 100.0) -> OHLCV:
    return OHLCV(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=close - 0.5,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1000.0,
        symbol="BTCUSDT",
        timeframe="1h",
        asset_class=AssetClass.CRYPTO,
        source="test",
    )


class TestDetectAssetClass:
    def test_crypto_symbol(self):
        assert detect_asset_class("BTCUSDT") == AssetClass.CRYPTO
        assert detect_asset_class("ETHUSDT") == AssetClass.CRYPTO

    def test_forex_symbol(self):
        assert detect_asset_class("EUR/USD") == AssetClass.FOREX
        assert detect_asset_class("GBP_USD") == AssetClass.FOREX

    def test_equity_symbol(self):
        assert detect_asset_class("AAPL") == AssetClass.EQUITY
        assert detect_asset_class("MSFT") == AssetClass.EQUITY


class TestValidateOhlcv:
    def test_valid_candle(self):
        validate_ohlcv(_sample_candle())

    def test_high_less_than_low(self):
        candle = _sample_candle()
        candle.high = 90.0
        candle.low = 100.0
        with pytest.raises(ValueError, match="high < low"):
            validate_ohlcv(candle)

    def test_non_positive_price(self):
        candle = _sample_candle()
        candle.open = -1.0
        candle.high = 1.0
        candle.low = -2.0
        candle.close = -1.0
        with pytest.raises(ValueError, match="non-positive"):
            validate_ohlcv(candle)


class TestIndicatorsPackage:
    def test_list_indicators_returns_packaged_modules(self):
        names = list_indicators()
        assert "rsi" in names
        assert "macd" in names
        assert "bollinger" in names
        assert "__init__" not in names

    def test_load_indicator_rsi(self):
        calculate = load_indicator("rsi")
        data = [_sample_candle(100 + i) for i in range(30)]
        result = calculate(data)
        assert len(result) == len(data)
        assert any(row.get("rsi") is not None for row in result)

    def test_load_indicator_invalid_name(self):
        with pytest.raises(ValueError, match="Invalid indicator name"):
            load_indicator("../secrets")

    def test_load_indicator_missing_module(self):
        with pytest.raises(FileNotFoundError, match="Indicator module not found"):
            load_indicator("not_a_real_indicator")


class TestFetchOhlcvBinanceMocked:
    def test_fetch_limit(self):
        client = MagicMock()
        client.ping.return_value = {}
        client.KLINE_INTERVAL_1HOUR = "1h"
        client.get_klines.return_value = [
            [1704067200000, "100", "101", "99", "100.5", "1234"],
        ]

        result = fetch_ohlcv_binance(client, "btcusdt", "1h", limit=1)

        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"
        assert result[0].close == 100.5
        assert result[0].source == "binance"

    def test_unsupported_timeframe(self):
        client = MagicMock()
        client.KLINE_INTERVAL_1HOUR = "1h"
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            fetch_ohlcv_binance(client, "BTCUSDT", "2h", limit=1)


class TestFetchOhlcvTwelveDataMocked:
    def test_fetch_limit(self):
        client = MagicMock()
        index = pd.to_datetime(["2024-01-01"], utc=True)
        df = pd.DataFrame(
            {
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [1000.0],
            },
            index=index,
        )
        ts = MagicMock()
        ts.as_pandas.return_value = df
        client.time_series.return_value = ts

        result = fetch_ohlcv_twelvedata(
            client,
            "AAPL",
            "1d",
            AssetClass.EQUITY,
            limit=1,
        )

        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].close == 100.5

    def test_rate_limit_raise(self):
        client = MagicMock()
        client.time_series.side_effect = Exception("HTTP 429 Too Many Requests")

        with pytest.raises(RateLimitException) as exc_info:
            fetch_ohlcv_twelvedata(
                client,
                "AAPL",
                "1d",
                AssetClass.EQUITY,
                limit=1,
                rate_limit_strategy="raise",
            )

        assert exc_info.value.provider == "twelvedata"

    def test_rate_limit_sleep_retries(self):
        client = MagicMock()
        index = pd.to_datetime(["2024-01-01"], utc=True)
        df = pd.DataFrame(
            {
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [1000.0],
            },
            index=index,
        )
        ts = MagicMock()
        ts.as_pandas.return_value = df
        client.time_series.side_effect = [
            Exception("HTTP 429 Too Many Requests"),
            ts,
        ]

        with patch("candlecraft.providers.time.sleep") as sleep_mock:
            result = fetch_ohlcv_twelvedata(
                client,
                "AAPL",
                "1d",
                AssetClass.EQUITY,
                limit=1,
                rate_limit_strategy="sleep",
            )

        sleep_mock.assert_called_once()
        assert len(result) == 1


class TestFetchOhlcvProviderSelection:
    def test_binance_not_available_for_equity(self):
        with patch("candlecraft.api.is_provider_available", return_value=True):
            with patch("candlecraft.api.authenticate_binance") as auth_mock:
                with pytest.raises(ValueError, match="does not support"):
                    fetch_ohlcv(
                        "AAPL",
                        "1d",
                        asset_class=AssetClass.EQUITY,
                        provider=Provider.BINANCE,
                        limit=1,
                    )
                auth_mock.assert_not_called()

    def test_no_providers_available(self):
        with patch("candlecraft.api.get_available_providers", return_value=[]):
            with patch("candlecraft.api._get_default_provider", return_value=None):
                with pytest.raises(ValueError, match="No providers available"):
                    fetch_ohlcv("BTCUSDT", "1h", limit=1)

    def test_twelvedata_unavailable_when_not_configured(self):
        with patch("candlecraft.api.is_provider_available", return_value=False):
            with pytest.raises(ValueError, match="Twelve Data provider is not available"):
                fetch_ohlcv(
                    "AAPL",
                    "1d",
                    asset_class=AssetClass.EQUITY,
                    provider=Provider.TWELVEDATA,
                    limit=1,
                )


class TestProviderAvailability:
    def test_binance_available_without_keys_when_installed(self):
        with patch("candlecraft.api.BINANCE_AVAILABLE", True):
            assert is_provider_available(Provider.BINANCE) is True

    def test_twelvedata_requires_secret(self):
        with patch("candlecraft.api.TWELVEDATA_AVAILABLE", True):
            with patch.dict("os.environ", {}, clear=True):
                assert is_provider_available(Provider.TWELVEDATA) is False
            with patch.dict("os.environ", {"TWELVEDATA_SECRET": "test-key"}):
                assert is_provider_available(Provider.TWELVEDATA) is True
