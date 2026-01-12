# Data Puller Architecture Analysis & Refactoring Plan

## Executive Summary

This document provides a senior software architect's perspective on refactoring the Data-Puller-AiO codebase into a true plug-and-play system. The analysis evaluates current implementation, identifies gaps, and proposes a comprehensive architecture for flexible data routing, storage, and consumption.

---

## 1. Current Implementation Assessment

### 1.1 Architecture Overview

**Current State:**
- Three monolithic scripts (`pull_crypto.py`, `pull_fx.py`, `pull_us-eq.py`)
- Each script is self-contained with duplicated logic
- Direct coupling between data fetching, formatting, and output
- No separation of concerns between data acquisition, processing, and storage

**Strengths:**
- ✅ Functional and working for basic use cases
- ✅ Supports multiple asset classes (crypto, forex, equities)
- ✅ Handles both historical and real-time data
- ✅ Basic output formatting (table, CSV, JSON)
- ✅ Rate limiting awareness

**Weaknesses:**
- ❌ Code duplication across three scripts (~70% similar code)
- ❌ No unified data model/schema
- ❌ Limited data validation and cleaning
- ❌ No pluggable storage backends
- ❌ No flexible routing mechanism
- ❌ Hard to extend with new data sources
- ❌ No standardized error handling
- ❌ Limited metadata tracking

### 1.2 Data Normalization Assessment

#### Current Normalization (What Exists)

**Timestamp Normalization:**
- ✅ Converts timestamps to Python `datetime` objects
- ✅ Handles timezone configuration (for Twelve Data sources)
- ⚠️ Inconsistent: Crypto uses UTC, FX uses "Exchange", Equities uses "America/New_York"
- ❌ No standardized timezone conversion to UTC

**Price Normalization:**
- ✅ Converts all prices to `float`
- ✅ Basic symbol normalization (uppercase, format standardization)
- ❌ No validation of price ranges (negative prices, zero values)
- ❌ No handling of missing/null values

**Volume Normalization:**
- ⚠️ Inconsistent: Crypto always has volume, FX/Equities may have `None`
- ❌ No validation of volume data (negative volumes)
- ❌ No handling of missing volume data

**Data Structure:**
- ✅ Consistent dictionary format: `{timestamp, open, high, low, close, volume}`
- ❌ No schema validation
- ❌ No data type enforcement
- ❌ Missing metadata (source, asset_class, timeframe, etc.)

#### Missing Normalization Features

1. **Data Quality Checks:**
   - No validation that `high >= low`
   - No validation that `high >= open` and `high >= close`
   - No validation that `low <= open` and `low <= close`
   - No detection of outliers or anomalies
   - No handling of gaps in time series

2. **Data Cleaning:**
   - No removal of duplicate timestamps
   - No handling of missing candles
   - No interpolation of missing data
   - No smoothing of noisy data

3. **Standardization:**
   - No unified timezone (should all be UTC)
   - No standardized precision for prices
   - No standardized volume units
   - No metadata enrichment (source, fetch_time, etc.)

4. **Data Integrity:**
   - No checksum or data validation
   - No audit trail of data transformations
   - No versioning of data schema

---

## 2. Plug-and-Play Architecture Design

### 2.1 Core Principles

1. **Separation of Concerns:** Data acquisition, processing, storage, and routing are independent
2. **Interface-Based Design:** All components implement well-defined interfaces
3. **Dependency Injection:** Components are loosely coupled and configurable
4. **Extensibility:** Easy to add new data sources, storage backends, and processors
5. **Observability:** Built-in logging, metrics, and error tracking

### 2.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Puller Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Data       │    │  Normalizer   │    │   Parser/    │      │
│  │   Source     │───▶│   & Cleaner   │───▶│   Router     │      │
│  │  (Adapter)   │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │               │
│                                                  ▼               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Storage & Consumer Layer                      │  │
│  ├──────────────┬──────────────┬──────────────┬─────────────┤  │
│  │   CSV        │  Time-Series │  Real-time   │  Training   │  │
│  │   Exporter   │     DB       │   Pipeline   │   Dataset   │  │
│  └──────────────┴──────────────┴──────────────┴─────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Component Breakdown

#### 2.3.1 Data Source Adapters

**Purpose:** Abstract data fetching from different providers

**Interface:**
```python
class DataSourceAdapter(ABC):
    @abstractmethod
    def fetch_historical(
        self, 
        symbol: str, 
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[RawDataPoint]:
        """Fetch historical OHLCV data"""
    
    @abstractmethod
    def stream_realtime(
        self,
        symbol: str,
        timeframe: str,
        callback: Callable[[RawDataPoint], None]
    ) -> None:
        """Stream real-time data"""
    
    @abstractmethod
    def get_asset_class(self) -> AssetClass:
        """Return asset class (CRYPTO, FOREX, EQUITY)"""
```

**Implementations:**
- `BinanceAdapter` (crypto)
- `TwelveDataForexAdapter` (forex)
- `TwelveDataEquityAdapter` (equities)

#### 2.3.2 Normalizer & Cleaner

**Purpose:** Standardize and validate all incoming data

**Responsibilities:**
1. Convert timestamps to UTC
2. Validate OHLCV relationships
3. Detect and handle anomalies
4. Enrich with metadata
5. Standardize data types and precision

**Interface:**
```python
class DataNormalizer:
    def normalize(
        self, 
        raw_data: List[RawDataPoint],
        source: str,
        asset_class: AssetClass
    ) -> List[NormalizedDataPoint]:
        """Normalize raw data to standard format"""
    
    def validate(self, data_point: NormalizedDataPoint) -> ValidationResult:
        """Validate data point integrity"""
    
    def clean(self, data_points: List[NormalizedDataPoint]) -> List[NormalizedDataPoint]:
        """Clean data (remove duplicates, handle gaps, etc.)"""
```

**Normalization Rules:**
- All timestamps → UTC
- All prices → Decimal (for precision) or float with fixed precision
- Volume → int or Decimal
- Metadata enrichment:
  - `source`: Data provider name
  - `asset_class`: CRYPTO, FOREX, EQUITY
  - `symbol`: Normalized symbol
  - `timeframe`: Standardized timeframe
  - `fetch_timestamp`: When data was fetched
  - `data_quality_score`: Quality metric (0-1)

**Validation Rules:**
- `high >= low`
- `high >= open` and `high >= close`
- `low <= open` and `low <= close`
- All prices > 0
- Volume >= 0 (if present)
- Timestamp is valid datetime
- No duplicate timestamps

#### 2.3.3 Parser/Router Component

**Purpose:** Flexibly route normalized data to different destinations

**Interface:**
```python
class DataRouter:
    def __init__(self, routes: List[Route]):
        """Initialize with routing configuration"""
    
    def route(
        self, 
        data: List[NormalizedDataPoint],
        context: RoutingContext
    ) -> Dict[str, Any]:
        """Route data to configured destinations"""
    
    def add_route(self, route: Route) -> None:
        """Dynamically add routing rule"""
    
    def remove_route(self, route_id: str) -> None:
        """Remove routing rule"""
```

**Route Types:**

1. **Storage Routes:**
   - CSV export
   - Time-series database (InfluxDB, TimescaleDB, etc.)
   - Relational database (PostgreSQL, MySQL)
   - Object storage (S3, GCS)

2. **Real-time Routes:**
   - WebSocket server
   - Message queue (Kafka, RabbitMQ, Redis Streams)
   - gRPC stream
   - HTTP webhook

3. **Analytics Routes:**
   - Real-time analytics engine
   - Stream processing (Apache Flink, Kafka Streams)
   - Event-driven automation triggers

4. **Training Dataset Routes:**
   - CSV/Parquet export for ML
   - Feature store (Feast, Tecton)
   - Vector database for embeddings
   - LLM training format (JSONL, etc.)

**Route Configuration:**
```python
@dataclass
class Route:
    route_id: str
    condition: Callable[[NormalizedDataPoint], bool]  # Filter condition
    destination: DataDestination
    transform: Optional[Callable] = None  # Optional transformation
    batch_size: Optional[int] = None  # For batching
    enabled: bool = True
```

**Example Routes:**
```python
# Route 1: Store all crypto data to InfluxDB
Route(
    route_id="crypto_to_influxdb",
    condition=lambda dp: dp.asset_class == AssetClass.CRYPTO,
    destination=InfluxDBDestination(bucket="crypto_ohlcv"),
    batch_size=100
)

# Route 2: Export equities to CSV for backtesting
Route(
    route_id="equities_to_csv",
    condition=lambda dp: dp.asset_class == AssetClass.EQUITY and dp.timeframe == "1d",
    destination=CSVDestination(path="/data/backtesting"),
    transform=lambda dp: dp.to_backtest_format()
)

# Route 3: Stream real-time data to Kafka
Route(
    route_id="realtime_to_kafka",
    condition=lambda dp: dp.is_realtime == True,
    destination=KafkaDestination(topic="ohlcv_stream"),
    batch_size=10
)

# Route 4: Create LLM training dataset
Route(
    route_id="llm_training_dataset",
    condition=lambda dp: dp.asset_class == AssetClass.CRYPTO and dp.timeframe == "1h",
    destination=LLMTrainingDatasetDestination(
        format="jsonl",
        include_features=["ohlcv", "technical_indicators"]
    ),
    transform=lambda dp: dp.to_llm_format()
)
```

#### 2.3.4 Storage & Consumer Implementations

**CSV Exporter:**
```python
class CSVDestination(DataDestination):
    def write(self, data: List[NormalizedDataPoint]) -> None:
        """Write to CSV file"""
        # Handles: file naming, chunking, compression
```

**Time-Series Database:**
```python
class InfluxDBDestination(DataDestination):
    def write(self, data: List[NormalizedDataPoint]) -> None:
        """Write to InfluxDB"""
        # Handles: batching, retries, connection pooling
```

**Real-time Pipeline:**
```python
class KafkaDestination(DataDestination):
    def write(self, data: List[NormalizedDataPoint]) -> None:
        """Publish to Kafka topic"""
        # Handles: serialization, partitioning, error handling
```

**Training Dataset:**
```python
class LLMTrainingDatasetDestination(DataDestination):
    def write(self, data: List[NormalizedDataPoint]) -> None:
        """Format for LLM training"""
        # Converts to: JSONL, includes context, features, labels
```

---

## 3. Use Case Scenarios

### 3.1 Historical Data Export to CSV

**Use Case:** Export 1 year of daily OHLCV data for backtesting

**Configuration:**
```python
pipeline = DataPipeline(
    source=BinanceAdapter(),
    normalizer=DataNormalizer(),
    router=DataRouter([
        Route(
            route_id="csv_export",
            condition=lambda dp: True,  # All data
            destination=CSVDestination(
                path="/exports",
                filename_pattern="{symbol}_{timeframe}_{date_range}.csv"
            )
        )
    ])
)

pipeline.fetch_and_process(
    symbol="BTCUSDT",
    timeframe="1d",
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31)
)
```

### 3.2 Live Pipeline to Time-Series Database

**Use Case:** Continuously stream real-time data to InfluxDB for monitoring

**Configuration:**
```python
pipeline = DataPipeline(
    source=BinanceAdapter(),
    normalizer=DataNormalizer(),
    router=DataRouter([
        Route(
            route_id="influxdb_realtime",
            condition=lambda dp: dp.is_realtime == True,
            destination=InfluxDBDestination(
                url="http://influxdb:8086",
                bucket="crypto_realtime",
                batch_size=50
            )
        )
    ])
)

pipeline.stream(
    symbol="BTCUSDT",
    timeframe="1m"
)
```

### 3.3 Multi-Destination Routing

**Use Case:** Route data to multiple destinations simultaneously

**Configuration:**
```python
router = DataRouter([
    # Store to database
    Route(
        route_id="timeseries_db",
        condition=lambda dp: True,
        destination=InfluxDBDestination(bucket="ohlcv")
    ),
    
    # Stream to real-time consumers
    Route(
        route_id="kafka_stream",
        condition=lambda dp: dp.is_realtime == True,
        destination=KafkaDestination(topic="ohlcv_live")
    ),
    
    # Export daily candles to CSV
    Route(
        route_id="daily_csv",
        condition=lambda dp: dp.timeframe == "1d",
        destination=CSVDestination(path="/exports/daily")
    ),
    
    # Send to webhook for alerts
    Route(
        route_id="webhook_alerts",
        condition=lambda dp: dp.asset_class == AssetClass.EQUITY and dp.close > threshold,
        destination=WebhookDestination(url="https://alerts.example.com/webhook")
    )
])
```

### 3.4 LLM Training Dataset Generation

**Use Case:** Create structured dataset for LLM-based trading analysis

**Configuration:**
```python
router = DataRouter([
    Route(
        route_id="llm_training",
        condition=lambda dp: dp.timeframe in ["1h", "4h", "1d"],
        destination=LLMTrainingDatasetDestination(
            format="jsonl",
            output_path="/datasets/llm_training",
            include_features=[
                "ohlcv",
                "technical_indicators",  # RSI, MACD, etc.
                "volume_profile",
                "price_action_patterns"
            ],
            context_window=100,  # Include 100 previous candles as context
            target_column="next_close"  # Predict next close price
        ),
        transform=lambda dp: dp.enrich_with_indicators().to_llm_format()
    )
])
```

**Output Format (JSONL):**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "context": [
    {"timestamp": "2024-01-01T00:00:00Z", "open": 42000, "high": 42500, "low": 41800, "close": 42200, "volume": 1000, "rsi": 55.2, "macd": 150},
    ...
  ],
  "current": {"timestamp": "2024-01-01T10:00:00Z", "open": 43000, "high": 43500, "low": 42800, "close": 43200, "volume": 1200, "rsi": 58.5, "macd": 180},
  "target": {"next_close": 43500},
  "metadata": {"asset_class": "CRYPTO", "source": "binance", "data_quality": 0.98}
}
```

### 3.5 Real-time Analytics & Automation

**Use Case:** Stream data to analytics engine and trigger automated actions

**Configuration:**
```python
router = DataRouter([
    # Stream to analytics
    Route(
        route_id="analytics_engine",
        condition=lambda dp: dp.is_realtime == True,
        destination=AnalyticsEngineDestination(
            engine="apache_flink",
            processing_rules=[
                "calculate_indicators",
                "detect_patterns",
                "generate_signals"
            ]
        )
    ),
    
    # Trigger automation
    Route(
        route_id="automation_triggers",
        condition=lambda dp: dp.has_trading_signal == True,
        destination=AutomationDestination(
            triggers=["send_alert", "place_order", "update_dashboard"]
        )
    )
])
```

---

## 4. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

1. **Create unified data model:**
   - `NormalizedDataPoint` dataclass
   - `AssetClass` enum
   - `Timeframe` enum
   - Schema validation

2. **Implement DataNormalizer:**
   - Timestamp normalization (UTC)
   - Price/volume validation
   - Data quality checks
   - Metadata enrichment

3. **Create base interfaces:**
   - `DataSourceAdapter` abstract class
   - `DataDestination` abstract class
   - `DataRouter` class

### Phase 2: Adapter Refactoring (Week 2-3)

1. **Refactor existing scripts:**
   - Extract adapter logic into `BinanceAdapter`
   - Extract adapter logic into `TwelveDataForexAdapter`
   - Extract adapter logic into `TwelveDataEquityAdapter`

2. **Standardize output:**
   - All adapters return `List[RawDataPoint]`
   - Consistent error handling

### Phase 3: Router Implementation (Week 3-4)

1. **Implement DataRouter:**
   - Route matching logic
   - Conditional routing
   - Batch processing
   - Error handling per route

2. **Implement storage destinations:**
   - `CSVDestination`
   - `InfluxDBDestination` (or TimescaleDB)
   - `PostgreSQLDestination`

### Phase 4: Real-time & Analytics (Week 4-5)

1. **Real-time destinations:**
   - `KafkaDestination`
   - `WebSocketServerDestination`
   - `WebhookDestination`

2. **Analytics destinations:**
   - `AnalyticsEngineDestination`
   - `AutomationDestination`

### Phase 5: LLM Training Dataset (Week 5-6)

1. **Feature enrichment:**
   - Technical indicators (RSI, MACD, etc.)
   - Price action patterns
   - Volume analysis

2. **LLM format exporters:**
   - `LLMTrainingDatasetDestination`
   - Context window generation
   - JSONL/Parquet export

### Phase 6: Testing & Documentation (Week 6-7)

1. **Unit tests:**
   - Normalizer tests
   - Router tests
   - Adapter tests

2. **Integration tests:**
   - End-to-end pipeline tests
   - Multi-destination routing tests

3. **Documentation:**
   - API documentation
   - Usage examples
   - Configuration guide

---

## 5. Data Model Specification

### 5.1 NormalizedDataPoint

```python
@dataclass
class NormalizedDataPoint:
    # Core OHLCV data
    timestamp: datetime  # UTC timezone
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal]
    
    # Metadata
    symbol: str
    asset_class: AssetClass
    timeframe: str
    source: str  # "binance", "twelvedata", etc.
    
    # Data quality
    fetch_timestamp: datetime
    data_quality_score: float  # 0.0 to 1.0
    is_realtime: bool
    
    # Optional enrichment
    technical_indicators: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> ValidationResult:
        """Validate data point integrity"""
        errors = []
        
        if self.high < self.low:
            errors.append("high < low")
        if self.high < self.open or self.high < self.close:
            errors.append("high < open or close")
        if self.low > self.open or self.low > self.close:
            errors.append("low > open or close")
        if self.open <= 0 or self.close <= 0:
            errors.append("non-positive prices")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

### 5.2 AssetClass Enum

```python
class AssetClass(Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    EQUITY = "equity"
    COMMODITY = "commodity"
    INDEX = "index"
```

---

## 6. Configuration Management

### 6.1 YAML Configuration

```yaml
data_puller:
  sources:
    - name: binance_crypto
      type: binance
      api_key: ${BINANCE_API_KEY}
      api_secret: ${BINANCE_API_SECRET}
    
    - name: twelvedata_fx
      type: twelvedata
      api_key: ${TWELVEDATA_SECRET}
      asset_class: forex
    
    - name: twelvedata_equity
      type: twelvedata
      api_key: ${TWELVEDATA_SECRET}
      asset_class: equity
  
  normalizer:
    timezone: UTC
    price_precision: 8
    volume_precision: 2
    validate_ohlcv: true
    data_quality_threshold: 0.8
  
  router:
    routes:
      - id: influxdb_realtime
        condition: "is_realtime == True"
        destination:
          type: influxdb
          url: "http://localhost:8086"
          bucket: "ohlcv_realtime"
          batch_size: 50
      
      - id: csv_daily_export
        condition: "timeframe == '1d'"
        destination:
          type: csv
          path: "/exports/daily"
          filename_pattern: "{symbol}_{date}.csv"
      
      - id: kafka_stream
        condition: "asset_class == 'CRYPTO' and is_realtime == True"
        destination:
          type: kafka
          brokers: ["localhost:9092"]
          topic: "crypto_ohlcv"
      
      - id: llm_training
        condition: "timeframe in ['1h', '4h', '1d']"
        destination:
          type: llm_training_dataset
          format: jsonl
          path: "/datasets/llm"
          include_features: ["ohlcv", "technical_indicators"]
          context_window: 100
```

---

## 7. Missing Components Summary

### 7.1 Critical Missing Features

1. **Unified Data Model:** No standardized schema across sources
2. **Data Validation:** No comprehensive OHLCV validation
3. **Data Cleaning:** No duplicate removal, gap handling, anomaly detection
4. **Pluggable Storage:** No abstraction for different storage backends
5. **Flexible Routing:** No way to route data to multiple destinations
6. **Metadata Tracking:** No source, quality, or transformation tracking
7. **Error Handling:** Limited retry logic and error recovery
8. **Configuration Management:** Hard-coded logic, no external config
9. **Observability:** No logging, metrics, or monitoring
10. **Testing:** No unit or integration tests

### 7.2 Nice-to-Have Features

1. **Data Enrichment:** Technical indicators, patterns, features
2. **Caching:** Cache frequently accessed data
3. **Rate Limiting:** Centralized rate limit management
4. **Backfilling:** Automatic gap detection and backfilling
5. **Data Versioning:** Track data schema versions
6. **API Server:** REST/GraphQL API for querying stored data
7. **Dashboard:** Web UI for monitoring and configuration
8. **Alerting:** Notifications for data quality issues

---

## 8. Conclusion

The current implementation is functional but lacks the architectural foundation for a true plug-and-play system. The proposed refactoring introduces:

1. **Separation of Concerns:** Clear boundaries between data acquisition, processing, and storage
2. **Extensibility:** Easy to add new sources, destinations, and processors
3. **Flexibility:** Configurable routing to multiple destinations
4. **Data Quality:** Comprehensive validation and cleaning
5. **Production Readiness:** Error handling, observability, and testing

The parser/router component is the key innovation that enables flexible data routing to storage layers, real-time analytics, automation systems, and LLM training datasets. This architecture transforms the codebase from a collection of scripts into a production-ready data pipeline platform.

---

## Appendix: Quick Start Example

```python
from data_puller import DataPipeline, BinanceAdapter, DataNormalizer, DataRouter
from data_puller.destinations import InfluxDBDestination, CSVDestination, KafkaDestination

# Configure pipeline
pipeline = DataPipeline(
    source=BinanceAdapter(),
    normalizer=DataNormalizer(),
    router=DataRouter([
        Route(
            route_id="influxdb",
            condition=lambda dp: True,
            destination=InfluxDBDestination(bucket="ohlcv")
        ),
        Route(
            route_id="csv_export",
            condition=lambda dp: dp.timeframe == "1d",
            destination=CSVDestination(path="/exports")
        ),
        Route(
            route_id="kafka",
            condition=lambda dp: dp.is_realtime == True,
            destination=KafkaDestination(topic="ohlcv_stream")
        )
    ])
)

# Fetch and process
pipeline.fetch_and_process(
    symbol="BTCUSDT",
    timeframe="1h",
    limit=1000
)

# Or stream real-time
pipeline.stream(
    symbol="BTCUSDT",
    timeframe="1m"
)
```
