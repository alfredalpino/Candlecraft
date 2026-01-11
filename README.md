# Data Puller All-in-One

A simple, standalone script for pulling OHLCV (Open, High, Low, Close, Volume) data from cryptocurrency exchanges.

## Current Status

This project is in its initial phase, focusing on a **standalone crypto OHLCV data puller** using Binance API. The goal is to validate the core pipeline: authentication, data retrieval, parameter handling, and accurate OHLCV output.

Future phases will extend this pattern to Forex and U.S. Equities.

## Features

- ✅ **Binance API Integration**: Connect to Binance exchange
- ✅ **Flexible Authentication**: Works with or without API keys (public data access)
- ✅ **Configurable Parameters**: Symbol, timeframe, limit, or date range
- ✅ **Clean Output**: Formatted table, CSV, or JSON output
- ✅ **Reliable Data Retrieval**: Handles pagination and rate limits

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Data-Puller-AiO
```

2. **Create and activate virtual environment**:
```bash
python -m venv dpa
source dpa/bin/activate  # On Windows: dpa\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables** (optional, for higher rate limits):
```bash
# Create .env file or export variables
export BINANCE_API_KEY=your_api_key_here
export BINANCE_API_SECRET=your_api_secret_here
export BINANCE_TESTNET=false  # Set to true for testnet
```

**Note**: API keys are optional. The script works without them for public data, but rate limits are lower.

## Usage

### Basic Examples

**Fetch last 100 hourly candles**:
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100
```

**Fetch daily candles for a date range**:
```bash
python pull_crypto.py --symbol ETHUSDT --timeframe 1d --start 2024-01-01 --end 2024-01-31
```

**Output as CSV**:
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 10 --format csv
```

**Output as JSON**:
```bash
python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 10 --format json
```

### Command Line Arguments

- `--symbol` (required): Trading pair symbol (e.g., BTCUSDT, ETHUSDT)
- `--timeframe` (required): Timeframe interval
  - Options: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1M`
- `--limit` (optional): Number of candles to fetch (max 1000)
  - Required if `--start`/`--end` not provided
- `--start` (optional): Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
  - Required with `--end` if `--limit` not provided
- `--end` (optional): End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
  - Required with `--start` if `--limit` not provided
- `--format` (optional): Output format
  - Options: `table` (default), `csv`, `json`

## Output Format

The script outputs clean OHLCV data with the following fields:

- **Timestamp**: Date and time of the candle
- **Open**: Opening price
- **High**: Highest price during the period
- **Low**: Lowest price during the period
- **Close**: Closing price
- **Volume**: Trading volume

### Example Output (Table Format)

```
====================================================================================================
Timestamp             Open         High          Low         Close        Volume
====================================================================================================
2024-01-15 10:00:00  42000.500000  42100.250000  41950.750000  42050.000000       1250.50000000
2024-01-15 11:00:00  42050.000000  42150.500000  42000.000000  42100.250000       1380.75000000
...
====================================================================================================
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BINANCE_API_KEY` | Binance API key | No (optional for higher rate limits) |
| `BINANCE_API_SECRET` | Binance API secret | No (optional for higher rate limits) |
| `BINANCE_TESTNET` | Use Binance testnet | No (default: false) |

## Supported Symbols

Any valid Binance trading pair, for example:
- `BTCUSDT` - Bitcoin to USDT
- `ETHUSDT` - Ethereum to USDT
- `BNBUSDT` - Binance Coin to USDT
- `ADAUSDT` - Cardano to USDT
- And many more...

## Error Handling

The script includes error handling for:
- Authentication failures
- Invalid symbols or timeframes
- API rate limits
- Network errors
- Invalid date formats

All errors are displayed with clear messages to help diagnose issues.

## Roadmap

- [x] Standalone crypto OHLCV puller (Binance)
- [ ] Forex OHLCV puller (OANDA)
- [ ] U.S. Equities OHLCV puller (Massive.com/Yahoo Finance)
- [ ] Unified interface for all asset classes
- [ ] Database persistence
- [ ] Multi-asset orchestration

## License

[Add your license here]

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
