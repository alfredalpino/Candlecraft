# Data Puller All-in-One

A production-ready, modular system for pulling OHLCV (Open, High, Low, Close, Volume) data from multiple asset classes: **Cryptocurrency**, **Forex**, and **U.S. Equities**.

## Table of Contents

- [Overview](#overview)
- [Polling vs Streaming: Architectural Overview](#polling-vs-streaming-architectural-overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage by Asset Class](#usage-by-asset-class)
  - [Cryptocurrency](#cryptocurrency-pull_cryptopy)
  - [Forex](#forex-pull_fxpy)
  - [U.S. Equities](#us-equities-pull_us-eqpy)
- [Supported Timeframes](#supported-timeframes)
- [Output Formats](#output-formats)
- [Rate Limiting](#rate-limiting)
- [Troubleshooting](#troubleshooting)

---

## Overview

This system provides three standalone data pullers, each optimized for its asset class:

- **`pull_crypto.py`** - Cryptocurrency data from Binance (BTC, ETH, etc.)
- **`pull_fx.py`** - Forex pairs from Twelve Data (EUR/USD, GBP/USD, etc.)
- **`pull_us-eq.py`** - U.S. Equities from Twelve Data (AAPL, MSFT, TSLA, etc.)

Each script supports:
- ✅ Historical OHLCV data fetching (REST API)
- ✅ Real-time data streaming (WebSocket)
- ✅ Polling mode (REST API at fixed intervals)
- ✅ Multiple output formats (table, CSV, JSON)
- ✅ Flexible timeframes (1 minute to 1 month)
- ✅ Date range queries
- ✅ Timezone configuration

---

## Polling vs Streaming: Architectural Overview

### Polling (REST API)

**What it is:**
Polling repeatedly requests data from a REST API at fixed intervals (e.g., every 60 seconds). The client initiates each request, waits for a response, processes it, then waits before the next request.

**Architecture:**
```
Client → [Request] → API Server → [Response] → Client
         (wait 60s)
Client → [Request] → API Server → [Response] → Client
         (wait 60s)
... (repeats)
```

**Trade-offs:**

**Advantages:**
- ✅ **Simple Implementation**: Standard HTTP requests, easy to debug
- ✅ **Reliable**: Each request is independent; failures don't cascade
- ✅ **Rate Limit Friendly**: Predictable API usage, easy to control
- ✅ **Works on Free Tiers**: No special WebSocket access required
- ✅ **OHLCV Candles**: Gets complete, closed candles directly
- ✅ **Stateless**: No connection management needed
- ✅ **Firewall Friendly**: Uses standard HTTP/HTTPS ports

**Disadvantages:**
- ❌ **Higher Latency**: Data arrives only at polling intervals (e.g., 60s delay)
- ❌ **Inefficient**: Makes requests even when no new data exists
- ❌ **Rate Limit Constraints**: Limited by API call frequency (1/min on free tier)
- ❌ **Resource Usage**: Each request has HTTP overhead
- ❌ **Not Real-time**: Data is delayed by polling interval

**When to Use Polling:**
- Free tier API access with strict rate limits
- Non-critical applications where 60-second delay is acceptable
- Simple scripts that need OHLCV candles (not tick data)
- Batch data collection for analysis
- When WebSocket access is unavailable or unreliable

**Example Use Cases:**
- Daily portfolio value updates
- End-of-day data collection
- Historical data backfilling
- Low-frequency trading signals

---

### Streaming (WebSocket)

**What it is:**
Streaming maintains a persistent, bidirectional connection (WebSocket) with the data provider. The server pushes new data to the client immediately when it becomes available, without waiting for requests.

**Architecture:**
```
Client ←→ [WebSocket Connection] ←→ Server
         (persistent connection)
         ↓ (server pushes data)
Client receives updates in real-time
```

**Trade-offs:**

**Advantages:**
- ✅ **Low Latency**: Data arrives immediately (milliseconds, not seconds)
- ✅ **Efficient**: No unnecessary requests; server pushes only new data
- ✅ **Real-time**: True real-time updates for live trading
- ✅ **Lower API Usage**: Doesn't count against REST API rate limits (separate quota)
- ✅ **Continuous Updates**: Receives every price tick or candle update

**Disadvantages:**
- ❌ **Complex Implementation**: Requires connection management, reconnection logic
- ❌ **Connection Overhead**: Must maintain persistent connection (heartbeats, ping/pong)
- ❌ **Stateful**: Connection state must be managed
- ❌ **May Require Paid Plans**: Free tiers often have limited WebSocket access
- ❌ **Firewall Issues**: Some networks block WebSocket connections
- ❌ **Price Data Only**: Often provides prices, not complete OHLCV candles
- ❌ **Unstable on Free Tiers**: Subscriptions may fail for some symbols

**When to Use Streaming:**
- Real-time trading bots requiring immediate price updates
- Live monitoring dashboards
- High-frequency data collection
- When latency is critical (< 1 second)
- Paid API plans with WebSocket access

**Example Use Cases:**
- Live trading signal generation
- Real-time portfolio monitoring
- High-frequency algorithmic trading
- Live price alerts

---

### Hybrid Approach (Recommended)

**Best Practice:**
1. **Fetch Historical Data First** (REST API polling)
   - Get last N candles for context
   - Backfill missing data
   - Initialize your system state

2. **Switch to Streaming** (WebSocket)
   - Receive new updates in real-time
   - Maintain continuity with historical data

**Command Pattern:**
```bash
# Fetch 100 historical candles, then stream new ones
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100 --stream
```

This gives you:
- Complete historical context
- Real-time updates going forward
- Best of both worlds

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- API keys (see [Configuration](#configuration))

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd Data-Puller-AiO
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv dpa

# Activate virtual environment
# On macOS/Linux:
source dpa/bin/activate

# On Windows:
dpa\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `python-binance` - Binance API client
- `twelvedata` - Twelve Data API client
- `websocket-client` - WebSocket support
- `python-dotenv` - Environment variable management
- `pandas` - Data processing

---

## Configuration

### Environment Variables

#### Quick Setup

1. **Copy the template file:**
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` with your actual API keys:**
   ```bash
   # Open .env in your editor
   nano .env
   # or
   code .env
   ```

#### Environment Variables Template

The project includes a `.env.template` file with the following structure:

```bash
# .env file structure

# Binance API (Optional - for higher rate limits)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=false

#-------------
# Twelve Data API (Required for Forex and US Equities)
TWELVEDATA_SECRET=your_twelvedata_api_key_here
```

**Example `.env` file:**
```bash
# Binance API (Optional - for higher rate limits)
BINANCE_API_KEY=D0OM70wj0DWnTlAhtCckicg8oDnWOmSdVrWCrhL6hi4654sX2wtPkroGCXadAKzk
BINANCE_API_SECRET=jbdkjbnd1234567890abcdefghijklmnopqrstuvwxyz
BINANCE_TESTNET=false

#-------------
# Twelve Data API (Required for Forex and US Equities)
TWELVEDATA_SECRET=4948hd84h1234567890abcdefghijklmnopqrstuvwxyz
```

**Important Security Notes:**
- ✅ The `.env` file is automatically ignored by git (in `.gitignore`)
- ✅ Never commit your `.env` file to version control
- ✅ Keep your API keys secure and private
- ✅ You can create a `.env.backup` file for local backup (also gitignored)

### Getting API Keys

#### Binance API Key (Optional)
1. Visit [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Create API key (read-only permissions sufficient)
3. Copy API key and secret to `.env` file

**Note:** Binance scripts work without API keys for public data, but rate limits are lower.

#### Twelve Data API Key (Required)
1. Visit [Twelve Data](https://twelvedata.com/)
2. Sign up for free account
3. Navigate to API Keys section
4. Copy API key to `.env` file as `TWELVEDATA_SECRET`

**Free Tier Limits:**
- 1 REST API request per minute
- Limited WebSocket access (may require paid plan for some symbols)

### Environment File Backup

For your convenience, you can create a backup of your `.env` file:

```bash
# Create a backup (already gitignored)
cp .env .env.backup
```

**Backup File Structure:**
```bash
# .env.backup example

# Binance API (Optional - for higher rate limits)
BINANCE_API_KEY=D0OM70wj0DWnTlAhtCckicg8oDnWOmSdVrWCrhL6hi4654sX2wtPkroGCXadAKzk
BINANCE_API_SECRET=jbdkjbnd1234567890abcdefghijklmnopqrstuvwxyz
BINANCE_TESTNET=false

#-------------
# Twelve Data API (Required for Forex and US Equities)
TWELVEDATA_SECRET=4948hd84h1234567890abcdefghijklmnopqrstuvwxyz
```

**Note:** Both `.env` and `.env.backup` are automatically excluded from git commits for security.

---

## Usage by Asset Class

### Cryptocurrency (pull_crypto.py)

#### Historical Data (REST API)

**Fetch last N candles:**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100
```

**Fetch by date range:**
```bash
python pull_crypto.py --symbol ETHUSDT --timeframe 1d --start 2024-01-01 --end 2024-01-31
```

**Output as CSV:**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 10 --format csv
```

**Output as JSON:**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 10 --format json
```

#### Real-time Streaming (WebSocket)

**Stream only (no historical):**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --stream
```

**Fetch historical, then stream:**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100 --stream
```

**Supported Symbols:**
- `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `ADAUSDT`, `SOLUSDT`, and all Binance trading pairs

---

### Forex (pull_fx.py)

#### Historical Data (REST API)

**Fetch last N candles:**
```bash
python pull_fx.py --symbol EUR/USD --timeframe 1h --limit 100
```

**Fetch by date range:**
```bash
python pull_fx.py --symbol GBP/USD --timeframe 1d --start 2024-01-01 --end 2024-01-31
```

**With timezone (UTC):**
```bash
python pull_fx.py --symbol EUR/USD --timeframe 1h --limit 10 --timezone UTC
```

#### Real-time Streaming (WebSocket)

**Stream only:**
```bash
python pull_fx.py --symbol EUR/USD --stream
```

**Historical + streaming:**
```bash
python pull_fx.py --symbol EUR/USD --timeframe 1h --limit 10 --stream
```

#### Polling Mode (1 call per minute)

**Poll for latest candle every 60 seconds:**
```bash
python pull_fx.py --symbol EUR/USD --timeframe 1m --limit 1 --poll
```

**Note:** Forex symbols accept both `/` and `_` separators:
- `EUR/USD` or `EUR_USD` (both work)

**Supported Symbols:**
- `EUR/USD`, `GBP/USD`, `USD/JPY`, `AUD/USD`, `USD/CAD`, and all major forex pairs

---

### U.S. Equities (pull_us-eq.py)

#### Historical Data (REST API)

**Minute-level data (1-minute candles):**
```bash
# Last 10 one-minute candles
python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 10

# Last 100 one-minute candles
python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 100
```

**5-minute candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 5m --limit 50
```

**15-minute candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 15m --limit 30
```

**30-minute candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 30m --limit 20
```

**Hourly candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 100
```

**4-hour candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 4h --limit 50
```

**Daily candles:**
```bash
# Last 30 days
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 30

# Specific date range
python pull_us-eq.py --symbol AAPL --timeframe 1d --start 2024-01-01 --end 2024-01-31
```

**Weekly candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1w --limit 52
```

**Monthly candles:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1M --limit 12
```

**With timezone:**
```bash
# UTC timezone
python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 10 --timezone UTC

# Pacific timezone
python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 10 --timezone America/Los_Angeles

# Default is America/New_York (US market time)
```

**Output formats:**
```bash
# CSV format
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 10 --format csv

# JSON format
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 10 --format json
```

#### Real-time Streaming (WebSocket)

**Stream only:**
```bash
python pull_us-eq.py --symbol AAPL --stream
```

**Historical + streaming:**
```bash
# Fetch last 100 hourly candles, then stream new ones
python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 100 --stream
```

#### Polling Mode (1 call per minute)

**Poll for latest 1-minute candle every 60 seconds:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 1 --poll
```

**Poll for latest 5-minute candle every 60 seconds:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 5m --limit 1 --poll
```

**Poll for latest hourly candle every 60 seconds:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 1 --poll
```

**Poll for latest daily candle every 60 seconds:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 1 --poll
```

**Supported Symbols:**
- `AAPL` (Apple), `MSFT` (Microsoft), `TSLA` (Tesla), `GOOGL` (Alphabet), `AMZN` (Amazon), `META` (Meta), and all US-listed stocks

---

## Supported Timeframes

All scripts support the following timeframes:

| Timeframe | Description | Example Use Case |
|-----------|-------------|-----------------|
| `1m` | 1 minute | Intraday trading, scalping |
| `5m` | 5 minutes | Short-term trading, minute-level analysis |
| `15m` | 15 minutes | Intraday swing trading |
| `30m` | 30 minutes | Medium-term intraday analysis |
| `1h` | 1 hour | Hourly trend analysis |
| `4h` | 4 hours | Multi-hour patterns |
| `1d` | 1 day | Daily trading, end-of-day analysis |
| `1w` | 1 week | Weekly trend analysis |
| `1M` | 1 month | Monthly analysis, long-term trends |

**Note:** Not all timeframes are available for all asset classes. Check provider documentation for specific limitations.

---

## Output Formats

### Table Format (Default)

```
====================================================================================================
Timestamp                    Open         High          Low        Close               Volume
====================================================================================================
2026-01-12 10:00:00  $    259.08 $    260.21 $    256.22 $    259.37           39,952,300
2026-01-12 11:00:00  $    257.02 $    259.29 $    255.70 $    259.04           50,419,300
====================================================================================================
```

### CSV Format

```bash
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 5 --format csv
```

Output:
```csv
timestamp,open,high,low,close,volume
2026-01-09 00:00:00,259.08,260.21,256.22,259.37,39952300
2026-01-08 00:00:00,257.02,259.29,255.70,259.04,50419300
```

### JSON Format

```bash
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 5 --format json
```

Output:
```json
[
  {
    "timestamp": "2026-01-09T00:00:00",
    "open": 259.08,
    "high": 260.21,
    "low": 256.22,
    "close": 259.37,
    "volume": 39952300
  },
  {
    "timestamp": "2026-01-08T00:00:00",
    "open": 257.02,
    "high": 259.29,
    "low": 255.70,
    "close": 259.04,
    "volume": 50419300
  }
]
```

---

## Rate Limiting

### Cryptocurrency (Binance)

- **Public Access**: No rate limiting required
- **With API Keys**: Higher rate limits (1200 requests/minute)
- **WebSocket**: Separate from REST API limits

### Forex & U.S. Equities (Twelve Data)

**Free Tier:**
- **REST API**: 1 request per minute
- **WebSocket**: Limited access (may require paid plan)
- **Automatic Rate Limiting**: Scripts automatically wait 60 seconds between REST API calls

**Rate Limit Behavior:**
- Scripts detect when rate limit is approaching
- Automatically wait required time before next request
- Display message: `⏳ Rate limit: Waiting X seconds before next request...`

**Polling Mode:**
- Respects rate limits automatically
- Waits exactly 60 seconds between requests
- Perfect for free tier usage

---

## Troubleshooting

### Common Issues

#### 1. "TWELVEDATA_SECRET environment variable not set"

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# If missing, create it:
echo "TWELVEDATA_SECRET=your_key_here" > .env

# Or export directly:
export TWELVEDATA_SECRET=your_key_here
```

#### 2. "ModuleNotFoundError: No module named 'twelvedata'"

**Solution:**
```bash
# Activate virtual environment
source dpa/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. "Subscription failed" (WebSocket)

**Causes:**
- Free tier may not support WebSocket for all symbols
- WebSocket credits exhausted
- Symbol not available for streaming

**Solution:**
- Use polling mode instead: `--poll`
- Try different symbols (major pairs/stocks work better)
- Check your Twelve Data plan tier

#### 4. "Rate limit exceeded"

**Solution:**
- Scripts automatically handle rate limiting
- For manual requests, wait 60 seconds between calls
- Use polling mode for automatic rate limit compliance

#### 5. "No data returned for SYMBOL"

**Causes:**
- Invalid symbol
- Market closed (for stocks)
- Date range outside available data

**Solution:**
- Verify symbol is correct (e.g., `AAPL` not `APPL`)
- Check market hours for US equities
- Try a different date range

#### 6. "Invalid timeframe"

**Solution:**
- Use supported timeframes: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1M`
- Check provider documentation for symbol-specific limitations

### Getting Help

1. Check error messages - they provide specific guidance
2. Verify API keys are set correctly
3. Test with simple commands first (e.g., `--limit 1`)
4. Check provider status pages for API outages

---

## Quick Reference

### Command Structure

```bash
python <script> --symbol <SYMBOL> --timeframe <TF> [OPTIONS]
```

### Required Arguments

- `--symbol`: Trading pair or stock symbol
- `--timeframe`: Time interval (required for historical data)

### Optional Arguments

- `--limit N`: Fetch last N candles
- `--start YYYY-MM-DD`: Start date (requires `--end`)
- `--end YYYY-MM-DD`: End date (requires `--start`)
- `--format {table,csv,json}`: Output format
- `--stream`: Enable WebSocket streaming
- `--poll`: Enable polling mode (60s intervals)
- `--timezone TZ`: Timezone (e.g., `UTC`, `America/New_York`)

### Examples by Use Case

**Backtesting (Historical Data):**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1d --start 2024-01-01 --end 2024-12-31 --format csv > aapl_2024.csv
```

**Live Trading Bot (Historical + Streaming):**
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100 --stream
```

**Daily Data Collection (Polling):**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1d --limit 1 --poll
```

**Minute-level Analysis:**
```bash
python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 1000
```

---

## License

[Add your license here]

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
