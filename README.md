# Data Puller All-in-One

A production-ready system for pulling OHLCV data from Cryptocurrency, Forex, and U.S. Equities markets.

**Package page:** https://pypi.org/project/candlecraft/

**Repository:** https://github.com/alfredalpino/Data-Puller-AiO 

**License:** MIT License - See [LICENSE](LICENSE) for details

## Candlecraft Library

**`candlecraft`** is a Python library for fetching OHLCV data from multiple providers. Published on PyPI.

### Installation

```bash
pip install candlecraft
```

### Quick Start

```python
from candlecraft import fetch_ohlcv, OHLCV, AssetClass

# Fetch OHLCV data (auto-detects asset class)
data = fetch_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    limit=100
)

# Access OHLCV data
for candle in data:
    print(f"{candle.timestamp}: {candle.close}")

# Explicit asset class
data = fetch_ohlcv(
    symbol="EUR/USD",
    timeframe="1h",
    asset_class=AssetClass.FOREX,
    limit=50
)
```

### API Reference

- `fetch_ohlcv()` - Fetch OHLCV data from appropriate provider
- `list_indicators()` - List available technical indicators
- `OHLCV` - Data model for OHLCV candles
- `AssetClass` - Enum for asset class types (CRYPTO, FOREX, EQUITY)

### Configuration

Set environment variables for API authentication:

```bash
# Binance API (Optional - for higher rate limits)
export BINANCE_API_KEY=your_key_here
export BINANCE_API_SECRET=your_secret_here

# Twelve Data API (Required for Forex and US Equities)
export TWELVEDATA_SECRET=your_key_here
```

**API Keys:**
- **Binance**: [API Management](https://www.binance.com/en/my/settings/api-management) (optional, works without keys for public data)
- **Twelve Data**: [Sign up](https://twelvedata.com/) (required for Forex/Equities)

### Supported Asset Classes

| Asset Class | Provider | Example Symbols |
|-------------|----------|-----------------|
| Cryptocurrency | Binance | BTCUSDT, ETHUSDT, BNBUSDT |
| Forex | Twelve Data | EUR/USD, GBP/USD, USD/JPY |
| U.S. Equities | Twelve Data | AAPL, MSFT, TSLA, GOOGL |

### Supported Timeframes

`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1M`

---

## CLI Interface (Optional)

**`pull_ohlcv.py`** is a command-line interface for the same functionality. Use this repository for CLI access or development.

### Installation (CLI)

```bash
git clone https://github.com/alfredalpino/Data-Puller-AiO.git
cd Data-Puller-AiO
python -m venv dpa
source dpa/bin/activate  # On Windows: dpa\Scripts\activate
pip install -r requirements.txt
```

### Quick Start (CLI)

```bash
# Cryptocurrency
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100

# Forex
python pull_ohlcv.py --symbol EUR/USD --timeframe 1h --limit 100

# U.S. Equities
python pull_ohlcv.py --symbol AAPL --timeframe 1h --limit 100

# Real-time streaming
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --stream

# Polling mode (Forex/Equities)
python pull_ohlcv.py --symbol EUR/USD --timeframe 1m --limit 1 --poll
```

### Historical Data

```bash
# Fetch last N candles
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100

# Fetch by date range
python pull_ohlcv.py --symbol AAPL --timeframe 1d --start 2024-01-01 --end 2024-01-31

# Output formats
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --format csv
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --format json
```

### Real-time Streaming

```bash
# Stream only
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --stream

# Fetch historical, then stream
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --stream
```

### Polling Mode (Forex/Equities)

```bash
# Poll for latest candle every 60 seconds
python pull_ohlcv.py --symbol EUR/USD --timeframe 1m --limit 1 --poll
```

### Command Reference

**Required Arguments:**
- `--symbol`: Trading pair or stock symbol
- `--timeframe`: Time interval (required for historical data)

**Optional Arguments:**
- `--limit N`: Fetch last N candles
- `--start YYYY-MM-DD`: Start date (requires `--end`)
- `--end YYYY-MM-DD`: End date (requires `--start`)
- `--format {table,csv,json}`: Output format (default: table)
- `--stream`: Enable WebSocket streaming
- `--poll`: Enable polling mode (60s intervals, Forex/Equities only)
- `--timezone TZ`: Timezone (e.g., `UTC`, `America/New_York`)
- `--indicator NAME`: Calculate technical indicator (e.g., `macd`)

### Output Formats

- **Table** (default): Formatted table output
- **CSV**: Comma-separated values
- **JSON**: JSON array of OHLCV objects

### Rate Limiting

- **Binance**: Public access unlimited; with API keys: 1200 requests/minute
- **Twelve Data (Free Tier)**: 1 REST API request per minute (automatically handled)
- **Polling Mode**: Automatically respects rate limits with 60-second intervals

### Troubleshooting

**1. "TWELVEDATA_SECRET environment variable not set"**
```bash
export TWELVEDATA_SECRET=your_key_here
# Or add to .env file
```

**2. "ModuleNotFoundError"**
```bash
source dpa/bin/activate
pip install -r requirements.txt
```

**3. "Subscription failed" (WebSocket)**
- Free tier may not support WebSocket for all symbols
- Use polling mode instead: `--poll`
- Check your Twelve Data plan tier

## Legacy Scripts

The following scripts are legacy/development-only and should not be used in production:
- `pull_fx.py` - Use `pull_ohlcv.py` instead
- `pull_us-eq.py` - Use `pull_ohlcv.py` instead
- `my_ohlcv.py` - Use `pull_ohlcv.py` instead

All functionality is available in `pull_ohlcv.py`.

## License

MIT License - See [LICENSE](LICENSE) for details.
