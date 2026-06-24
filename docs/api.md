# API Reference

## `fetch_ohlcv`

```python
fetch_ohlcv(
    symbol: str,
    timeframe: str,
    asset_class: AssetClass | None = None,
    provider: Provider | None = None,
    limit: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    timezone: str | None = None,
    rate_limit_strategy: str = "raise",
) -> list[OHLCV]
```

Fetch normalized OHLCV candles from Binance or Twelve Data.

**Raises:** `ValueError`, `RuntimeError`, `RateLimitException`, `ConnectionError`

**Example:**

```python
from candlecraft import fetch_ohlcv

candles = fetch_ohlcv("BTCUSDT", "1h", limit=24)
print(candles[-1].close)
```

## `list_indicators`

```python
list_indicators() -> list[str]
```

Returns sorted indicator module names packaged with candlecraft.

## `load_indicator`

```python
load_indicator(indicator_name: str) -> Callable
```

Loads an indicator's `calculate` function by name (e.g. `"rsi"`, `"macd"`).

## `get_available_providers` / `is_provider_available`

Check which providers are installed and configured (Twelve Data requires `TWELVEDATA_SECRET`).

## Models

### `OHLCV`

Dataclass fields: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `symbol`, `timeframe`, `asset_class`, `source`.

### `AssetClass`

`CRYPTO`, `FOREX`, `EQUITY`

### `Provider`

`BINANCE`, `TWELVEDATA`

### `RateLimitException`

Attributes: `provider`, `message`, `retry_after` (seconds, optional).

## Environment variables

| Variable | Provider | Required |
|----------|----------|----------|
| `BINANCE_API_KEY` | Binance | No (public API works) |
| `BINANCE_API_SECRET` | Binance | No |
| `BINANCE_TESTNET` | Binance | No (`true`/`false`) |
| `TWELVEDATA_SECRET` | Twelve Data | Yes for forex/equity |

## Logging

Library code uses the `candlecraft` logger namespace. Enable verbose output:

```python
import logging
logging.basicConfig(level=logging.INFO)
```
