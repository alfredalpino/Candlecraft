# Data Puller All-in-One

A modular, production-ready system for pulling OHLCV (Open, High, Low, Close, Volume) data across three asset classes: **U.S. Equities**, **Cryptocurrency**, and **Forex**.

## 🏗️ Architecture

The system follows a clean, modular architecture with clear separation of concerns:

```
Data Puller System
├── Models (Normalized Schema)
│   └── OHLCVData - Unified data structure
├── Providers (Asset Class Specific)
│   ├── EquitiesProvider - Massive.com / Yahoo Finance
│   ├── CryptoProvider - Binance
│   └── ForexProvider - OANDA v20
├── Database Manager (Unified Storage)
│   └── DatabaseManager - Single interface for all data
└── Utilities
    ├── Configuration Management
    ├── Logging
    └── Error Handling
```

## ✨ Features

- **Modular Design**: Each asset class has its own dedicated provider
- **Unified Schema**: All data normalized to consistent `OHLCVData` format
- **Multiple Data Sources**: Supports production (Massive.com, Binance, OANDA) and free alternatives (Yahoo Finance)
- **Robust Error Handling**: Comprehensive error handling and logging at every step
- **Flexible Database**: Supports PostgreSQL, MySQL, and SQLite
- **Batch Operations**: Efficient batch inserts with conflict resolution
- **Incremental Updates**: Query latest timestamps for incremental data pulls

## 📦 Installation

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

4. **Set up environment variables** (create a `.env` file):
```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=your_password
DB_DIALECT=postgresql  # or sqlite, mysql

# Data Provider API Keys (optional - some providers work without keys)
MASSIVE_API_KEY=your_massive_api_key
BINANCE_API_KEY=your_binance_api_key  # Optional for public data
BINANCE_API_SECRET=your_binance_secret  # Optional for public data
OANDA_API_KEY=your_oanda_api_key
OANDA_ACCOUNT_ID=your_oanda_account_id
OANDA_ENVIRONMENT=practice  # or live

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/data_puller.log
```

## 🚀 Quick Start

### Basic Usage

```python
from datetime import datetime, timedelta
from src.providers import EquitiesProvider, CryptoProvider, ForexProvider
from src.database import DatabaseManager

# Initialize providers
equities = EquitiesProvider(source="auto")  # Auto-detects Massive.com or Yahoo Finance
crypto = CryptoProvider()
forex = ForexProvider()

# Authenticate
equities.authenticate()
crypto.authenticate()
forex.authenticate()

# Fetch data
end = datetime.now()
start = end - timedelta(days=30)

# Equities
equity_data = equities.fetch_ohlcv("AAPL", "1day", start, end)

# Crypto
crypto_data = crypto.fetch_ohlcv("BTCUSDT", "1hour", start, end)

# Forex
forex_data = forex.fetch_ohlcv("EUR_USD", "1day", start, end)

# Store in database
db = DatabaseManager()
db.create_tables()  # Run once to create tables

# Insert data
db.insert_batch(equity_data)
db.insert_batch(crypto_data)
db.insert_batch(forex_data)
```

### Example Scripts

See the `examples/` directory for complete working examples:
- `pull_equities.py` - Pull U.S. equities data
- `pull_crypto.py` - Pull cryptocurrency data
- `pull_forex.py` - Pull forex data
- `pull_all.py` - Pull all asset classes

## 📚 API Reference

### Providers

#### EquitiesProvider

```python
from src.providers import EquitiesProvider

provider = EquitiesProvider(source="auto")  # or "massive", "yahoo"
provider.authenticate()
data = provider.fetch_ohlcv(
    symbol="AAPL",
    timeframe="1day",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31),
)
```

**Supported timeframes**: `1min`, `5min`, `15min`, `30min`, `1hour`, `4hour`, `1day`, `1week`, `1month`

#### CryptoProvider

```python
from src.providers import CryptoProvider

provider = CryptoProvider()
provider.authenticate()
data = provider.fetch_ohlcv(
    symbol="BTCUSDT",
    timeframe="1hour",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31),
)
```

**Supported timeframes**: `1min`, `5min`, `15min`, `30min`, `1hour`, `4hour`, `1day`, `1week`, `1month`

#### ForexProvider

```python
from src.providers import ForexProvider

provider = ForexProvider()
provider.authenticate()
data = provider.fetch_ohlcv(
    symbol="EUR_USD",
    timeframe="1day",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31),
)
```

**Supported timeframes**: `1min`, `5min`, `15min`, `30min`, `1hour`, `4hour`, `1day`, `1week`, `1month`

### Database Manager

```python
from src.database import DatabaseManager
from src.models.ohlcv import AssetClass

db = DatabaseManager()

# Create tables (run once)
db.create_tables()

# Insert single record
db.insert_ohlcv(ohlcv_data, update_on_conflict=True)

# Insert batch
stats = db.insert_batch(ohlcv_list, update_on_conflict=True)
# Returns: {'inserted': 100, 'updated': 5, 'skipped': 2, 'errors': 0}

# Query data
data = db.query_ohlcv(
    symbol="AAPL",
    asset_class=AssetClass.EQUITIES,
    timeframe="1day",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31),
)

# Get latest timestamp (for incremental updates)
latest = db.get_latest_timestamp(
    symbol="AAPL",
    asset_class=AssetClass.EQUITIES,
    timeframe="1day",
)
```

## 🔧 Configuration

### Data Sources

The system supports multiple data sources with automatic fallback:

- **Equities**: 
  - Primary: Massive.com (production, requires API key)
  - Fallback: Yahoo Finance (free, no API key)
  
- **Crypto**: 
  - Binance (works without API key, but API key recommended for higher rate limits)
  
- **Forex**: 
  - OANDA v20 (requires API key and account ID)

### Database Options

The system supports multiple database backends:

- **PostgreSQL** (recommended for production)
- **MySQL**
- **SQLite** (good for development/testing)

Configure via environment variables (see Installation section).

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 📝 Logging

The system uses Python's standard logging module with configurable levels:

- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

Logs are written to both console and optional log file (configured via `LOG_FILE`).

## 🛠️ Error Handling

The system includes comprehensive error handling:

- `AuthenticationError`: Provider authentication failures
- `DataFetchError`: Data retrieval failures
- `NormalizationError`: Data normalization failures
- `DatabaseError`: Database operation failures
- `ConfigurationError`: Configuration issues

All errors are logged with context for debugging.

## 🔄 Incremental Updates

For efficient data updates, use the `get_latest_timestamp()` method:

```python
# Get latest data timestamp
latest = db.get_latest_timestamp("AAPL", AssetClass.EQUITIES, "1day")

# Fetch only new data
if latest:
    start = latest + timedelta(days=1)
else:
    start = datetime(2020, 1, 1)  # First time, fetch from beginning

end = datetime.now()
new_data = provider.fetch_ohlcv("AAPL", "1day", start, end)
db.insert_batch(new_data)
```

## 📊 Data Schema

All data is normalized to the `OHLCVData` structure:

```python
@dataclass
class OHLCVData:
    symbol: str
    asset_class: AssetClass
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]
    timeframe: str
    source: str
    metadata: Optional[dict]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- [Massive.com](https://massive.com) (formerly Polygon.io) for equities data
- [Binance](https://binance.com) for cryptocurrency data
- [OANDA](https://oanda.com) for forex data
- [Yahoo Finance](https://finance.yahoo.com) for free equities data

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.
