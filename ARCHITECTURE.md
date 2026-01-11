# System Architecture

## Overview

The Data Puller All-in-One system is designed with a modular, plug-and-play architecture that separates concerns and ensures each component is independently testable and maintainable.

## Directory Structure

```
Data-Puller-AiO/
├── src/
│   ├── models/              # Data models and schemas
│   │   ├── __init__.py
│   │   └── ohlcv.py         # OHLCVData model and AssetClass enum
│   │
│   ├── providers/           # Asset class specific data providers
│   │   ├── __init__.py
│   │   ├── base.py          # BaseDataProvider abstract class
│   │   ├── equities.py      # EquitiesProvider (Massive.com/Yahoo Finance)
│   │   ├── crypto.py        # CryptoProvider (Binance)
│   │   └── forex.py         # ForexProvider (OANDA)
│   │
│   ├── database/            # Unified database management
│   │   ├── __init__.py
│   │   └── manager.py        # DatabaseManager class
│   │
│   └── utils/               # Shared utilities
│       ├── __init__.py
│       ├── config.py        # Configuration management
│       ├── logger.py        # Logging utilities
│       └── exceptions.py    # Custom exceptions
│
├── examples/                # Example scripts
│   ├── pull_equities.py
│   ├── pull_crypto.py
│   ├── pull_forex.py
│   └── pull_all.py
│
├── requirements.txt         # Python dependencies
├── README.md                # User documentation
└── ARCHITECTURE.md          # This file
```

## Component Design

### 1. Models Layer (`src/models/`)

**Purpose**: Define the normalized data schema that all providers must conform to.

**Key Components**:
- `OHLCVData`: Dataclass representing a single OHLCV bar
- `AssetClass`: Enum for asset class types (equities, crypto, forex)

**Design Principles**:
- Single source of truth for data structure
- All providers must transform their raw data to this format
- Enables uniform database storage regardless of source

### 2. Providers Layer (`src/providers/`)

**Purpose**: Handle authentication, data fetching, and normalization for each asset class.

**Key Components**:
- `BaseDataProvider`: Abstract base class defining the provider contract
- `EquitiesProvider`: Handles U.S. equities (supports Massive.com and Yahoo Finance)
- `CryptoProvider`: Handles cryptocurrency data (Binance)
- `ForexProvider`: Handles forex data (OANDA v20)

**Design Principles**:
- Each provider is independent and testable
- Implements common interface from `BaseDataProvider`
- Handles provider-specific authentication and API calls
- Normalizes all data to `OHLCVData` format before returning

**Provider Responsibilities**:
1. Authenticate with data source
2. Fetch raw OHLCV data
3. Normalize data to `OHLCVData` schema
4. Handle provider-specific errors and rate limiting

### 3. Database Layer (`src/database/`)

**Purpose**: Unified interface for storing and querying OHLCV data from all sources.

**Key Components**:
- `DatabaseManager`: Main class for all database operations
- `OHLCVRecord`: SQLAlchemy model for database table

**Design Principles**:
- Single interface for all asset classes
- Handles schema creation and migrations
- Supports batch operations for efficiency
- Implements conflict resolution (insert vs update)
- Database-agnostic (supports PostgreSQL, MySQL, SQLite)

**Database Manager Responsibilities**:
1. Create and manage database schema
2. Insert single or batch OHLCV records
3. Handle duplicate records (update on conflict)
4. Query data with flexible filters
5. Support incremental updates (get latest timestamp)

### 4. Utilities Layer (`src/utils/`)

**Purpose**: Shared functionality for configuration, logging, and error handling.

**Key Components**:
- `config.py`: Configuration management from environment variables
- `logger.py`: Centralized logging setup
- `exceptions.py`: Custom exception classes

**Design Principles**:
- Centralized configuration management
- Consistent logging across all components
- Clear error types for better error handling

## Data Flow

```
┌─────────────────┐
│  Data Provider  │
│  (Equities/     │
│   Crypto/Forex) │
└────────┬────────┘
         │
         │ 1. Authenticate
         │ 2. Fetch raw data
         │ 3. Normalize to OHLCVData
         │
         ▼
┌─────────────────┐
│   OHLCVData     │
│  (Normalized)   │
└────────┬────────┘
         │
         │
         ▼
┌─────────────────┐
│ DatabaseManager │
│                 │
│  - Insert       │
│  - Update       │
│  - Query        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Database      │
│  (PostgreSQL/   │
│   MySQL/SQLite) │
└─────────────────┘
```

## Key Design Patterns

### 1. Strategy Pattern
Each asset class provider implements the same interface (`BaseDataProvider`), allowing them to be used interchangeably.

### 2. Factory Pattern
Providers can be instantiated with different configurations (e.g., EquitiesProvider with "massive" or "yahoo" source).

### 3. Adapter Pattern
Each provider adapts its specific API format to the unified `OHLCVData` schema.

### 4. Repository Pattern
`DatabaseManager` acts as a repository, abstracting database operations from business logic.

## Error Handling Strategy

1. **Provider Level**: Handles authentication and API-specific errors
2. **Normalization Level**: Catches data transformation errors
3. **Database Level**: Handles database connection and constraint errors
4. **Application Level**: Logs all errors with context for debugging

## Extension Points

The system is designed to be easily extended:

1. **New Asset Classes**: Create a new provider inheriting from `BaseDataProvider`
2. **New Data Sources**: Add support within existing providers (e.g., add Alpha Vantage to EquitiesProvider)
3. **New Databases**: Add support in `DatabaseManager` by configuring SQLAlchemy
4. **New Features**: Add methods to providers or database manager as needed

## Testing Strategy

Each component can be tested independently:

- **Unit Tests**: Test individual methods in isolation
- **Integration Tests**: Test provider → database flow
- **Mock Tests**: Mock external APIs for reliable testing

## Configuration Management

Configuration is loaded from:
1. Environment variables (highest priority)
2. `.env` file (if present)
3. Default values (lowest priority)

This allows for:
- Development: `.env` file
- Production: Environment variables
- Testing: Programmatic configuration

## Logging Strategy

- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Outputs**: Console (always) + File (optional)
- **Format**: Timestamp, logger name, level, file:line, message
- **Context**: Each component has its own logger for easy filtering

## Database Schema

The unified schema stores all asset classes in a single table:

```sql
CREATE TABLE ohlcv_data (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT,
    timeframe VARCHAR(20) NOT NULL,
    source VARCHAR(50) NOT NULL,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(symbol, asset_class, timestamp, timeframe)
);
```

This design:
- Stores all asset classes uniformly
- Enforces data integrity with unique constraints
- Supports efficient querying with indexes
- Allows metadata storage for provider-specific data
