# CLI Guide (`pull_ohlcv.py`)

The CLI wraps the candlecraft library for terminal use: historical fetch, polling, streaming, and indicators.

## Basic usage

```bash
# Latest 10 hourly BTC candles
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10

# With RSI indicator
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 50 --indicator rsi

# Forex (requires TWELVEDATA_SECRET)
python pull_ohlcv.py --symbol EUR/USD --timeframe 1d --limit 30
```

## Output formats

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 5 --format table
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 5 --format json
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 5 --format csv
```

## Date ranges

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h \
  --start "2024-01-01" --end "2024-01-07"
```

## Streaming (crypto)

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1m --stream
```

## Polling mode

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 1 --poll
```

## List indicators from Python

```python
from candlecraft import list_indicators
print(list_indicators())
```

See [INDICATORS_README.md](../INDICATORS_README.md) for indicator parameters.
