# Candlecraft

[![PyPI](https://img.shields.io/pypi/v/candlecraft)](https://pypi.org/project/candlecraft/)
[![CI](https://github.com/alfredalpino/Candlecraft/actions/workflows/ci.yml/badge.svg)](https://github.com/alfredalpino/Candlecraft/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Unified OHLCV fetching for **crypto**, **forex**, and **equities** — one Python API, multiple data providers, packaged technical indicators.

> **Stable beta** — used in production market-making workflows at 3poch Labs. Powers data for [MarketMakingMegaMachine](https://github.com/alfredalpino/MarketMakingMegaMachine).

## Install

```bash
pip install candlecraft
```

## 30-second example

```python
from candlecraft import fetch_ohlcv, load_indicator

candles = fetch_ohlcv("BTCUSDT", "1h", limit=24)
rsi = load_indicator("rsi")(candles)

print(f"Latest close: {candles[-1].close}")
print(f"Latest RSI: {rsi[-1]['rsi']}")
```

## Features

- Single `fetch_ohlcv()` for crypto, forex, and equities
- Auto provider selection (Binance for crypto, Twelve Data for forex/equity)
- Typed `OHLCV` dataclass with validation
- Rate-limit handling (`raise` or `sleep` strategies)
- 10 technical indicators included in the package (`pip install` works)

## Providers

| Provider | Asset classes | API keys |
|----------|---------------|----------|
| Binance | Crypto | Optional (public API supported) |
| Twelve Data | Crypto, Forex, Equity | `TWELVEDATA_SECRET` required |

```python
from candlecraft import Provider, fetch_ohlcv

candles = fetch_ohlcv("EUR/USD", "1d", provider=Provider.TWELVEDATA, limit=30)
```

## Indicators

```python
from candlecraft import list_indicators, load_indicator

print(list_indicators())
# ['adx', 'atr', 'bollinger', 'ema', 'macd', 'obv', 'rsi', 'sma', 'stochastic', 'vwap']

macd = load_indicator("macd")
result = macd(candles)
```

## CLI

```bash
git clone https://github.com/alfredalpino/Candlecraft.git
cd Candlecraft
pip install -e ".[dev]"

python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --indicator rsi
```

## Development

```bash
pip install -e ".[dev]"
pytest -m "not integration"    # unit tests (no API keys)
pytest -m integration          # live API tests (keys required)
ruff check candlecraft tests
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [API reference](docs/api.md)
- [CLI guide](docs/cli.md)
- [Indicators](INDICATORS_README.md)
- [Changelog](CHANGELOG.md)

## Related projects

- [MarketMakingMegaMachine](https://github.com/alfredalpino/MarketMakingMegaMachine) — Hyperliquid market-making platform ($58.9K live volume at 3poch Labs)

## License

MIT — see [LICENSE](LICENSE).
