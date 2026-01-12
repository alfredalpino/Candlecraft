# Parser/Router Component - Detailed Design

## Overview

The Parser/Router component is the central nervous system of the plug-and-play data pipeline. It receives normalized OHLCV data and intelligently routes it to multiple destinations based on configurable rules.

## Architecture

```
                    ┌─────────────────┐
                    │  Normalized     │
                    │  Data Points    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Data Router   │
                    │   (Parser)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Storage     │   │  Real-time     │   │  Analytics    │
│   Destinations│   │  Destinations  │   │  Destinations │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Core Components

### 1. Route Definition

```python
from dataclasses import dataclass
from typing import Callable, Optional, List, Dict, Any
from enum import Enum

class RoutePriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class Route:
    """Defines a routing rule for data points"""
    
    route_id: str
    name: str
    description: Optional[str] = None
    
    # Condition: Function that returns True if data point matches this route
    condition: Callable[['NormalizedDataPoint'], bool]
    
    # Destination: Where to send matching data
    destination: 'DataDestination'
    
    # Optional transformation before sending to destination
    transform: Optional[Callable[['NormalizedDataPoint'], Any]] = None
    
    # Batch processing configuration
    batch_size: Optional[int] = None  # Batch N items before sending
    batch_timeout: Optional[float] = None  # Send batch after N seconds
    
    # Route metadata
    priority: RoutePriority = RoutePriority.NORMAL
    enabled: bool = True
    
    # Error handling
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting per route
    rate_limit: Optional[float] = None  # Items per second
    
    def matches(self, data_point: 'NormalizedDataPoint') -> bool:
        """Check if data point matches this route's condition"""
        if not self.enabled:
            return False
        try:
            return self.condition(data_point)
        except Exception as e:
            logger.error(f"Error evaluating route {self.route_id}: {e}")
            return False
```

### 2. Data Router Implementation

```python
import asyncio
from collections import defaultdict
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

class DataRouter:
    """
    Routes normalized data points to multiple destinations based on rules.
    
    Supports:
    - Conditional routing (filter data points)
    - Multiple destinations per data point
    - Batch processing
    - Async/async operations
    - Error handling and retries
    - Rate limiting
    """
    
    def __init__(
        self,
        routes: Optional[List[Route]] = None,
        default_destination: Optional['DataDestination'] = None,
        enable_parallel: bool = True
    ):
        self.routes: List[Route] = routes or []
        self.default_destination = default_destination
        self.enable_parallel = enable_parallel
        
        # Batch accumulators per route
        self._batches: Dict[str, List['NormalizedDataPoint']] = defaultdict(list)
        self._batch_timers: Dict[str, asyncio.Task] = {}
        
        # Rate limiting per route
        self._rate_limiters: Dict[str, RateLimiter] = {}
        
        # Statistics
        self.stats = RouterStats()
    
    def add_route(self, route: Route) -> None:
        """Add a new routing rule"""
        if route.route_id in [r.route_id for r in self.routes]:
            raise ValueError(f"Route ID {route.route_id} already exists")
        
        self.routes.append(route)
        
        # Initialize rate limiter if needed
        if route.rate_limit:
            self._rate_limiters[route.route_id] = RateLimiter(
                rate=route.rate_limit
            )
        
        logger.info(f"Added route: {route.route_id} -> {route.destination}")
    
    def remove_route(self, route_id: str) -> None:
        """Remove a routing rule"""
        self.routes = [r for r in self.routes if r.route_id != route_id]
        
        # Clean up batch accumulator
        if route_id in self._batches:
            del self._batches[route_id]
        
        # Clean up rate limiter
        if route_id in self._rate_limiters:
            del self._rate_limiters[route_id]
        
        logger.info(f"Removed route: {route_id}")
    
    def route(
        self,
        data_points: List['NormalizedDataPoint'],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route data points to matching destinations.
        
        Args:
            data_points: List of normalized data points to route
            context: Optional context information (source, fetch_time, etc.)
        
        Returns:
            Dictionary with routing results:
            {
                "routed": int,  # Number of data points routed
                "routes_matched": Dict[str, int],  # Count per route
                "errors": List[Dict],  # Any errors encountered
                "skipped": int  # Data points that matched no routes
            }
        """
        context = context or {}
        results = {
            "routed": 0,
            "routes_matched": defaultdict(int),
            "errors": [],
            "skipped": 0
        }
        
        # Sort routes by priority
        sorted_routes = sorted(
            self.routes,
            key=lambda r: r.priority.value
        )
        
        for data_point in data_points:
            matched = False
            
            for route in sorted_routes:
                if route.matches(data_point):
                    matched = True
                    results["routes_matched"][route.route_id] += 1
                    
                    # Apply rate limiting
                    if route.route_id in self._rate_limiters:
                        if not self._rate_limiters[route.route_id].acquire():
                            logger.warning(
                                f"Rate limit exceeded for route {route.route_id}, "
                                f"skipping data point"
                            )
                            continue
                    
                    # Transform if needed
                    transformed_data = data_point
                    if route.transform:
                        try:
                            transformed_data = route.transform(data_point)
                        except Exception as e:
                            logger.error(
                                f"Transform error for route {route.route_id}: {e}"
                            )
                            results["errors"].append({
                                "route_id": route.route_id,
                                "error": str(e),
                                "type": "transform_error"
                            })
                            continue
                    
                    # Route to destination
                    if route.batch_size:
                        # Batch mode
                        self._add_to_batch(route, transformed_data)
                    else:
                        # Immediate mode
                        self._send_to_destination(route, transformed_data, results)
            
            if matched:
                results["routed"] += 1
            else:
                results["skipped"] += 1
                
                # Send to default destination if configured
                if self.default_destination:
                    self._send_to_destination(
                        Route(
                            route_id="default",
                            name="Default",
                            condition=lambda _: True,
                            destination=self.default_destination
                        ),
                        data_point,
                        results
                    )
        
        # Update statistics
        self.stats.update(results)
        
        return results
    
    def _add_to_batch(
        self,
        route: Route,
        data_point: 'NormalizedDataPoint'
    ) -> None:
        """Add data point to batch accumulator"""
        route_id = route.route_id
        self._batches[route_id].append(data_point)
        
        # Check if batch is full
        if len(self._batches[route_id]) >= route.batch_size:
            self._flush_batch(route)
        elif route.batch_timeout and route_id not in self._batch_timers:
            # Start timeout timer
            self._batch_timers[route_id] = asyncio.create_task(
                self._batch_timeout_handler(route)
            )
    
    async def _batch_timeout_handler(self, route: Route) -> None:
        """Handle batch timeout"""
        await asyncio.sleep(route.batch_timeout)
        self._flush_batch(route)
        if route.route_id in self._batch_timers:
            del self._batch_timers[route.route_id]
    
    def _flush_batch(self, route: Route) -> None:
        """Flush accumulated batch to destination"""
        route_id = route.route_id
        if route_id not in self._batches or not self._batches[route_id]:
            return
        
        batch = self._batches[route_id]
        self._batches[route_id] = []
        
        # Cancel timeout timer if exists
        if route_id in self._batch_timers:
            self._batch_timers[route_id].cancel()
            del self._batch_timers[route_id]
        
        # Send batch to destination
        results = {"routed": 0, "routes_matched": {}, "errors": [], "skipped": 0}
        self._send_to_destination(route, batch, results)
    
    def _send_to_destination(
        self,
        route: Route,
        data: Union['NormalizedDataPoint', List['NormalizedDataPoint']],
        results: Dict[str, Any]
    ) -> None:
        """Send data to destination with error handling"""
        try:
            if isinstance(data, list):
                route.destination.write_batch(data)
            else:
                route.destination.write(data)
            
            logger.debug(
                f"Routed {len(data) if isinstance(data, list) else 1} "
                f"data point(s) to {route.destination} via route {route.route_id}"
            )
        
        except Exception as e:
            logger.error(
                f"Error routing to {route.destination} via route {route.route_id}: {e}"
            )
            
            results["errors"].append({
                "route_id": route.route_id,
                "destination": str(route.destination),
                "error": str(e),
                "type": "destination_error"
            })
            
            # Retry if configured
            if route.retry_on_failure:
                self._retry_destination(route, data, route.max_retries)
    
    def _retry_destination(
        self,
        route: Route,
        data: Union['NormalizedDataPoint', List['NormalizedDataPoint']],
        remaining_retries: int
    ) -> None:
        """Retry sending to destination"""
        if remaining_retries <= 0:
            logger.error(
                f"Max retries exceeded for route {route.route_id}, "
                f"dropping data point"
            )
            return
        
        time.sleep(route.retry_delay)
        
        try:
            if isinstance(data, list):
                route.destination.write_batch(data)
            else:
                route.destination.write(data)
            
            logger.info(
                f"Successfully retried route {route.route_id} "
                f"({remaining_retries} retries remaining)"
            )
        
        except Exception as e:
            logger.warning(
                f"Retry failed for route {route.route_id}: {e}, "
                f"{remaining_retries - 1} retries remaining"
            )
            self._retry_destination(route, data, remaining_retries - 1)
    
    def flush_all_batches(self) -> None:
        """Flush all pending batches (useful for shutdown)"""
        for route in self.routes:
            if route.route_id in self._batches:
                self._flush_batch(route)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return self.stats.to_dict()
```

### 3. Destination Interface

```python
from abc import ABC, abstractmethod
from typing import List, Union

class DataDestination(ABC):
    """Base class for all data destinations"""
    
    @abstractmethod
    def write(self, data_point: 'NormalizedDataPoint') -> None:
        """Write a single data point"""
        pass
    
    @abstractmethod
    def write_batch(self, data_points: List['NormalizedDataPoint']) -> None:
        """Write a batch of data points (more efficient)"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connection/cleanup resources"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}"
```

## Destination Implementations

### 1. CSV Destination

```python
import csv
from pathlib import Path
from typing import List, Optional
from datetime import datetime

class CSVDestination(DataDestination):
    """Export data to CSV files"""
    
    def __init__(
        self,
        path: str,
        filename_pattern: str = "{symbol}_{timeframe}_{date}.csv",
        append: bool = True,
        include_headers: bool = True,
        compression: Optional[str] = None  # "gzip", "bz2", etc.
    ):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.filename_pattern = filename_pattern
        self.append = append
        self.include_headers = include_headers
        self.compression = compression
        
        # Track open file handles per symbol/timeframe
        self._file_handles: Dict[str, Any] = {}
        self._writers: Dict[str, csv.DictWriter] = {}
    
    def _get_filename(self, data_point: 'NormalizedDataPoint') -> str:
        """Generate filename from pattern"""
        date_str = data_point.timestamp.strftime("%Y%m%d")
        return self.filename_pattern.format(
            symbol=data_point.symbol,
            timeframe=data_point.timeframe,
            date=date_str,
            asset_class=data_point.asset_class.value
        )
    
    def _get_file_handle(self, data_point: 'NormalizedDataPoint'):
        """Get or create file handle for symbol/timeframe"""
        key = f"{data_point.symbol}_{data_point.timeframe}"
        
        if key not in self._file_handles:
            filename = self._get_filename(data_point)
            filepath = self.path / filename
            
            mode = "a" if self.append and filepath.exists() else "w"
            
            # Handle compression
            if self.compression == "gzip":
                import gzip
                f = gzip.open(f"{filepath}.gz", mode + "t", encoding="utf-8")
            elif self.compression == "bz2":
                import bz2
                f = bz2.open(f"{filepath}.bz2", mode + "t", encoding="utf-8")
            else:
                f = open(filepath, mode, newline="", encoding="utf-8")
            
            self._file_handles[key] = f
            
            # Create CSV writer
            fieldnames = [
                "timestamp", "open", "high", "low", "close", "volume",
                "symbol", "asset_class", "timeframe", "source",
                "data_quality_score"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if self.include_headers and mode == "w":
                writer.writeheader()
            
            self._writers[key] = writer
        
        return self._writers[key]
    
    def write(self, data_point: 'NormalizedDataPoint') -> None:
        """Write single data point to CSV"""
        writer = self._get_file_handle(data_point)
        
        writer.writerow({
            "timestamp": data_point.timestamp.isoformat(),
            "open": str(data_point.open),
            "high": str(data_point.high),
            "low": str(data_point.low),
            "close": str(data_point.close),
            "volume": str(data_point.volume) if data_point.volume else "",
            "symbol": data_point.symbol,
            "asset_class": data_point.asset_class.value,
            "timeframe": data_point.timeframe,
            "source": data_point.source,
            "data_quality_score": str(data_point.data_quality_score)
        })
    
    def write_batch(self, data_points: List['NormalizedDataPoint']) -> None:
        """Write batch of data points (more efficient)"""
        # Group by symbol/timeframe for efficient writing
        grouped = defaultdict(list)
        for dp in data_points:
            key = f"{dp.symbol}_{dp.timeframe}"
            grouped[key].append(dp)
        
        for key, points in grouped.items():
            writer = self._get_file_handle(points[0])
            for dp in points:
                self.write(dp)
    
    def close(self) -> None:
        """Close all file handles"""
        for f in self._file_handles.values():
            f.close()
        self._file_handles.clear()
        self._writers.clear()
```

### 2. Time-Series Database Destination (InfluxDB)

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxDBDestination(DataDestination):
    """Write data to InfluxDB time-series database"""
    
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        batch_size: int = 100,
        flush_interval: int = 10  # seconds
    ):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._buffer: List['NormalizedDataPoint'] = []
    
    def write(self, data_point: 'NormalizedDataPoint') -> None:
        """Write single data point (buffered)"""
        self._buffer.append(data_point)
        
        if len(self._buffer) >= self.batch_size:
            self._flush_buffer()
    
    def write_batch(self, data_points: List['NormalizedDataPoint']) -> None:
        """Write batch of data points"""
        self._buffer.extend(data_points)
        
        if len(self._buffer) >= self.batch_size:
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Flush buffer to InfluxDB"""
        if not self._buffer:
            return
        
        points = []
        for dp in self._buffer:
            point = Point("ohlcv") \
                .tag("symbol", dp.symbol) \
                .tag("asset_class", dp.asset_class.value) \
                .tag("timeframe", dp.timeframe) \
                .tag("source", dp.source) \
                .field("open", float(dp.open)) \
                .field("high", float(dp.high)) \
                .field("low", float(dp.low)) \
                .field("close", float(dp.close)) \
                .field("volume", float(dp.volume) if dp.volume else 0.0) \
                .field("data_quality_score", dp.data_quality_score) \
                .time(dp.timestamp)
            
            points.append(point)
        
        try:
            self.write_api.write(bucket=self.bucket, record=points)
            self._buffer.clear()
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            raise
    
    def close(self) -> None:
        """Flush buffer and close connection"""
        if self._buffer:
            self._flush_buffer()
        self.client.close()
```

### 3. Kafka Destination

```python
from kafka import KafkaProducer
import json

class KafkaDestination(DataDestination):
    """Publish data to Kafka topic"""
    
    def __init__(
        self,
        brokers: List[str],
        topic: str,
        key_field: str = "symbol",  # Partition by this field
        compression_type: str = "gzip"
    ):
        self.producer = KafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type=compression_type
        )
        self.topic = topic
        self.key_field = key_field
    
    def write(self, data_point: 'NormalizedDataPoint') -> None:
        """Publish single data point"""
        message = {
            "timestamp": data_point.timestamp.isoformat(),
            "symbol": data_point.symbol,
            "asset_class": data_point.asset_class.value,
            "timeframe": data_point.timeframe,
            "open": float(data_point.open),
            "high": float(data_point.high),
            "low": float(data_point.low),
            "close": float(data_point.close),
            "volume": float(data_point.volume) if data_point.volume else None,
            "source": data_point.source,
            "data_quality_score": data_point.data_quality_score,
            "is_realtime": data_point.is_realtime
        }
        
        key = getattr(data_point, self.key_field, data_point.symbol).encode('utf-8')
        
        self.producer.send(self.topic, key=key, value=message)
    
    def write_batch(self, data_points: List['NormalizedDataPoint']) -> None:
        """Publish batch of data points"""
        for dp in data_points:
            self.write(dp)
        
        # Flush to ensure delivery
        self.producer.flush()
    
    def close(self) -> None:
        """Close Kafka producer"""
        self.producer.close()
```

### 4. LLM Training Dataset Destination

```python
import json
from pathlib import Path
from typing import List, Optional, Dict

class LLMTrainingDatasetDestination(DataDestination):
    """Format data for LLM training (JSONL format)"""
    
    def __init__(
        self,
        output_path: str,
        format: str = "jsonl",  # "jsonl" or "parquet"
        context_window: int = 100,
        include_features: List[str] = None,
        target_column: str = "next_close"
    ):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.format = format
        self.context_window = context_window
        self.include_features = include_features or ["ohlcv"]
        self.target_column = target_column
        
        # Buffer for context window
        self._context_buffers: Dict[str, List['NormalizedDataPoint']] = defaultdict(list)
    
    def write(self, data_point: 'NormalizedDataPoint') -> None:
        """Write single data point (with context)"""
        key = f"{data_point.symbol}_{data_point.timeframe}"
        self._context_buffers[key].append(data_point)
        
        # Keep only last N points for context
        if len(self._context_buffers[key]) > self.context_window:
            self._context_buffers[key] = self._context_buffers[key][-self.context_window:]
        
        # Generate training example when we have enough context
        if len(self._context_buffers[key]) >= self.context_window:
            self._write_training_example(key)
    
    def write_batch(self, data_points: List['NormalizedDataPoint']) -> None:
        """Write batch of data points"""
        for dp in data_points:
            self.write(dp)
    
    def _write_training_example(self, key: str) -> None:
        """Write a training example with context"""
        buffer = self._context_buffers[key]
        if len(buffer) < 2:
            return
        
        # Last point is the "current" point, previous ones are context
        context_points = buffer[:-1]
        current_point = buffer[-1]
        
        # Build training example
        example = {
            "symbol": current_point.symbol,
            "timeframe": current_point.timeframe,
            "asset_class": current_point.asset_class.value,
            "context": [
                self._format_data_point(dp) for dp in context_points
            ],
            "current": self._format_data_point(current_point),
            "target": {
                self.target_column: float(current_point.close)  # Simplified
            },
            "metadata": {
                "source": current_point.source,
                "data_quality": current_point.data_quality_score,
                "timestamp": current_point.timestamp.isoformat()
            }
        }
        
        # Write to file
        filename = f"{key}_{current_point.timestamp.strftime('%Y%m%d')}.jsonl"
        filepath = self.output_path / filename
        
        with open(filepath, "a") as f:
            f.write(json.dumps(example) + "\n")
    
    def _format_data_point(self, dp: 'NormalizedDataPoint') -> Dict:
        """Format data point for LLM training"""
        formatted = {
            "timestamp": dp.timestamp.isoformat(),
            "open": float(dp.open),
            "high": float(dp.high),
            "low": float(dp.low),
            "close": float(dp.close),
        }
        
        if "volume" in self.include_features and dp.volume:
            formatted["volume"] = float(dp.volume)
        
        if "technical_indicators" in self.include_features and dp.technical_indicators:
            formatted["indicators"] = dp.technical_indicators
        
        return formatted
    
    def close(self) -> None:
        """Flush remaining context buffers"""
        for key in list(self._context_buffers.keys()):
            if len(self._context_buffers[key]) > 1:
                self._write_training_example(key)
        self._context_buffers.clear()
```

## Usage Examples

### Example 1: Multi-Destination Routing

```python
router = DataRouter([
    # Store all data to InfluxDB
    Route(
        route_id="influxdb_all",
        name="InfluxDB Storage",
        condition=lambda dp: True,
        destination=InfluxDBDestination(
            url="http://localhost:8086",
            token="...",
            org="trading",
            bucket="ohlcv"
        ),
        batch_size=100
    ),
    
    # Export daily candles to CSV
    Route(
        route_id="csv_daily",
        name="Daily CSV Export",
        condition=lambda dp: dp.timeframe == "1d",
        destination=CSVDestination(
            path="/exports/daily",
            filename_pattern="{symbol}_daily_{date}.csv"
        )
    ),
    
    # Stream real-time crypto to Kafka
    Route(
        route_id="kafka_crypto_realtime",
        name="Crypto Real-time Stream",
        condition=lambda dp: (
            dp.asset_class == AssetClass.CRYPTO and
            dp.is_realtime == True
        ),
        destination=KafkaDestination(
            brokers=["localhost:9092"],
            topic="crypto_ohlcv_realtime"
        ),
        batch_size=10,
        batch_timeout=1.0  # Flush every second
    ),
    
    # Generate LLM training dataset
    Route(
        route_id="llm_training",
        name="LLM Training Dataset",
        condition=lambda dp: dp.timeframe in ["1h", "4h", "1d"],
        destination=LLMTrainingDatasetDestination(
            output_path="/datasets/llm_training",
            context_window=100,
            include_features=["ohlcv", "technical_indicators"]
        )
    )
])

# Route data
results = router.route(normalized_data_points)
print(f"Routed {results['routed']} data points")
print(f"Routes matched: {results['routes_matched']}")
```

### Example 2: Conditional Routing with Transformations

```python
router = DataRouter([
    # Route high-quality data to analytics
    Route(
        route_id="analytics_high_quality",
        condition=lambda dp: dp.data_quality_score >= 0.95,
        destination=AnalyticsEngineDestination(...),
        transform=lambda dp: dp.enrich_with_indicators()
    ),
    
    # Route low-quality data to review queue
    Route(
        route_id="quality_review",
        condition=lambda dp: dp.data_quality_score < 0.8,
        destination=QualityReviewQueue(...)
    )
])
```

## Summary

The Parser/Router component provides:

1. **Flexible Routing:** Route data to multiple destinations based on conditions
2. **Batch Processing:** Efficient batching for high-throughput scenarios
3. **Error Handling:** Retry logic and error recovery
4. **Rate Limiting:** Per-route rate limiting
5. **Transformations:** Apply transformations before routing
6. **Statistics:** Track routing performance and errors
7. **Extensibility:** Easy to add new destination types

This architecture enables the system to serve multiple use cases simultaneously:
- Historical data export (CSV, database)
- Real-time streaming (Kafka, WebSocket)
- Analytics pipelines (Flink, Spark)
- LLM training datasets (JSONL, Parquet)
- Automation triggers (webhooks, message queues)
