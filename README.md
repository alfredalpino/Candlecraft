# Candlecraft

A production-ready Python library for fetching OHLCV data from Cryptocurrency, Forex, and U.S. Equities markets.

**📦 [Package on PyPI](https://pypi.org/project/candlecraft/)** | **📚 [Documentation](#candlecraft-library)** | **⚖️ [License: MIT](LICENSE)**

## Data Sources

Candlecraft supports multiple data providers, giving you flexibility to choose the best option for your needs:

- **Twelve Data Finance** - Comprehensive market data for Forex, U.S. Equities, and Cryptocurrency
- **Binance** - Leading cryptocurrency exchange with public API access
- **More providers coming soon!** - We're continuously adding support for additional data sources

You can choose which provider to use, or let Candlecraft automatically select the best available option based on your asset class and configured API keys.

## Candlecraft Library

**`candlecraft`** is a Python library for fetching OHLCV data from multiple providers. Published on [PyPI](https://pypi.org/project/candlecraft/).

**Current Version:** v0.1.4

### What's New in v0.1.4

- 🔄 **Branch Consolidation** - Merged master into main, unified codebase
- 🏷️ **Repository Updates** - Updated to new Candlecraft repository structure

### What's New in v0.1.3

- ✨ **Provider Selection** - Choose which data provider to use (Binance or Twelve Data)
- 🔍 **Provider Availability Checks** - Check which providers are available before fetching data
- 🛡️ **Better Error Messages** - Clear guidance when providers aren't configured
- 🔄 **Smart Fallbacks** - Automatic provider selection with intelligent fallbacks
- 📚 **Enhanced Documentation** - Comprehensive examples and troubleshooting guide

### Installation

```bash
pip install candlecraft
```

### Quick Start

```python
from candlecraft import fetch_ohlcv, OHLCV, AssetClass, Provider

# Fetch OHLCV data (auto-detects asset class and provider)
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

# Choose a specific provider
data = fetch_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    provider=Provider.TWELVEDATA,  # Use Twelve Data instead of default Binance
    limit=100
)

# Check available providers
from candlecraft import get_available_providers
available = get_available_providers()
print(f"Available providers: {[p.value for p in available]}")
```

### API Reference

- `fetch_ohlcv()` - Fetch OHLCV data from appropriate provider
- `list_indicators()` - List available technical indicators
- `get_available_providers()` - Get list of available providers
- `is_provider_available()` - Check if a specific provider is available
- `OHLCV` - Data model for OHLCV candles
- `AssetClass` - Enum for asset class types (CRYPTO, FOREX, EQUITY)
- `Provider` - Enum for provider types (BINANCE, TWELVEDATA)

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

### Rate Limits & Provider Behavior

Candlecraft does not enforce rate limits by default. Market data providers apply their own rate limits based on your subscription plan, and these limits vary significantly between free tiers and paid plans.

When rate limits are exceeded, providers may return HTTP status codes (such as 429) along with retry-after information indicating when you can make your next request. By default, Candlecraft will raise a `RateLimitException` when a rate limit is encountered, allowing you to implement your own retry logic, backoff strategies, or error handling as appropriate for your application.

Candlecraft provides an optional opt-in mechanism for automatic waiting. If you explicitly enable `rate_limit_strategy="sleep"`, the library will wait for the provider-specified retry duration before retrying the request. This is useful for simple scripts or applications where automatic waiting is acceptable.

**Example with default behavior (fail fast):**
```python
from candlecraft import fetch_ohlcv, RateLimitException

try:
    data = fetch_ohlcv(symbol="AAPL", timeframe="1h", limit=100)
except RateLimitException as e:
    print(f"Rate limit hit for {e.provider}")
    print(f"Retry after {e.retry_after} seconds")
    # Implement your own retry logic here
```

**Example with opt-in automatic waiting:**
```python
from candlecraft import fetch_ohlcv

# Automatically wait and retry on rate limits
data = fetch_ohlcv(
    symbol="AAPL",
    timeframe="1h",
    limit=100,
    rate_limit_strategy="sleep"
)
```

Users are responsible for implementing rate limiting, retries, or backoff logic in their own applications based on their specific needs and subscription plans.

### Provider Selection

Candlecraft allows you to choose which provider to use for fetching data. This is especially useful if you only have API keys for one provider. The library will automatically select the best available provider, but you can also specify one explicitly.

**Why Provider Selection Matters:**
- Use the provider you have API keys for
- Avoid errors when a default provider isn't configured
- Flexibility to switch between providers based on your needs

**Example: Using a specific provider**

```python
from candlecraft import fetch_ohlcv, Provider

# Use Twelve Data for crypto (if you don't have Binance API)
data = fetch_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    provider=Provider.TWELVEDATA,  # Explicitly choose Twelve Data
    limit=100
)

# Use Binance for crypto (default, but explicit)
data = fetch_ohlcv(
    symbol="ETHUSDT",
    timeframe="1h",
    provider=Provider.BINANCE,
    limit=100
)
```

**Example: Check available providers**

```python
from candlecraft import get_available_providers, is_provider_available, Provider

# Get all available providers
available = get_available_providers()
print(f"Available providers: {[p.value for p in available]}")

# Check specific provider
if is_provider_available(Provider.BINANCE):
    print("✓ Binance is available")
if is_provider_available(Provider.TWELVEDATA):
    print("✓ Twelve Data is available")
```

**Default Provider Selection:**
- **Cryptocurrency**: Binance (if available), automatically falls back to Twelve Data
- **Forex**: Twelve Data (required)
- **U.S. Equities**: Twelve Data (required)

If no provider is specified, the library automatically selects an available provider based on the asset class. If your preferred provider isn't available, you'll get a clear error message with instructions on how to set it up.

### Supported Asset Classes

| Asset Class | Default Provider | Alternative Provider | Example Symbols |
|-------------|------------------|----------------------|-----------------|
| Cryptocurrency | Binance | Twelve Data | BTCUSDT, ETHUSDT, BNBUSDT |
| Forex | Twelve Data | - | EUR/USD, GBP/USD, USD/JPY |
| U.S. Equities | Twelve Data | - | AAPL, MSFT, TSLA, GOOGL |

### Supported Timeframes

`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1M`

---

## CLI Interface (Optional)

**`pull_ohlcv.py`** is a command-line interface for the same functionality. Use this repository for CLI access or development.

### Installation (CLI)

```bash
git clone https://github.com/alfredalpino/Candlecraft.git
cd Candlecraft
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

### Rate Limiting (CLI)

The CLI interface (`pull_ohlcv.py`) includes built-in rate limiting for convenience. This behavior is separate from the library's default behavior.

- **Binance**: Public access unlimited; with API keys: 1200 requests/minute
- **Twelve Data (Free Tier)**: 1 REST API request per minute (automatically handled in CLI)
- **Polling Mode**: Automatically respects rate limits with 60-second intervals

### Troubleshooting

**1. "TWELVEDATA_SECRET environment variable not set"**
```bash
export TWELVEDATA_SECRET=your_key_here
# Or add to .env file
```

**2. "No provider available for crypto"**
If you only have Twelve Data API keys and want to fetch crypto data:
```python
from candlecraft import fetch_ohlcv, Provider

# Explicitly use Twelve Data for crypto
data = fetch_ohlcv(
    symbol="BTCUSDT",  # or use Twelve Data format like "BTC/USD"
    timeframe="1h",
    provider=Provider.TWELVEDATA,
    limit=100
)
```

**3. "ModuleNotFoundError"**
```bash
source dpa/bin/activate
pip install -r requirements.txt
```

**4. "Subscription failed" (WebSocket)**
- Free tier may not support WebSocket for all symbols
- Use polling mode instead: `--poll`
- Check your Twelve Data plan tier

**5. "Provider not available"**
Check which providers are available:
```python
from candlecraft import get_available_providers, is_provider_available, Provider

available = get_available_providers()
print(f"Available providers: {[p.value for p in available]}")

# Check specific provider
if is_provider_available(Provider.BINANCE):
    print("Binance is available")
```

## Legacy Scripts

The following scripts are legacy/development-only and should not be used in production:
- `pull_fx.py` - Use `pull_ohlcv.py` instead
- `pull_us-eq.py` - Use `pull_ohlcv.py` instead
- `my_ohlcv.py` - Use `pull_ohlcv.py` instead

All functionality is available in `pull_ohlcv.py`.

## License

MIT License - See [LICENSE](LICENSE) for details.
