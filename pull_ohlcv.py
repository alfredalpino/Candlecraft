#!/usr/bin/env python3
"""
Unified OHLCV Data Puller

Supports Cryptocurrency (Binance), Forex (Twelve Data), and US Equities (Twelve Data).
Automatically detects asset class from symbol format.

Usage:
    # Cryptocurrency
    python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100
    
    # Forex
    python pull_ohlcv.py --symbol EUR/USD --timeframe 1h --limit 100
    
    # US Equities
    python pull_ohlcv.py --symbol AAPL --timeframe 1h --limit 100
    
    # Real-time streaming
    python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --stream
    
    # Polling mode (Forex/Equities only)
    python pull_ohlcv.py --symbol EUR/USD --timeframe 1m --limit 1 --poll
"""

import os
import sys
import argparse
import json
import time
import signal
import threading
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import providers
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from twelvedata import TDClient
    TWELVEDATA_AVAILABLE = True
except ImportError:
    TWELVEDATA_AVAILABLE = False

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class AssetClass(Enum):
    """Asset class types"""
    CRYPTO = "crypto"
    FOREX = "forex"
    EQUITY = "equity"


@dataclass
class OHLCV:
    """Internal data model for OHLCV data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]
    symbol: str
    timeframe: str
    asset_class: AssetClass
    source: str


def to_utc(ts: datetime) -> datetime:
    """Convert datetime to timezone-aware UTC datetime."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def validate_ohlcv(dp: OHLCV) -> None:
    """Validate OHLCV data invariants. Raises ValueError on invalid data."""
    if dp.high < dp.low:
        raise ValueError("Invalid OHLCV: high < low")
    if dp.high < max(dp.open, dp.close):
        raise ValueError("Invalid OHLCV: high < open/close")
    if dp.low > min(dp.open, dp.close):
        raise ValueError("Invalid OHLCV: low > open/close")
    if dp.open <= 0 or dp.close <= 0:
        raise ValueError("Invalid OHLCV: non-positive price")


# Rate limiting for Twelve Data
_last_api_call_time = 0
_rate_limit_delay = 60


def wait_for_rate_limit():
    """Wait if necessary to respect rate limit (1 request per minute for Twelve Data)."""
    global _last_api_call_time
    
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    
    if time_since_last_call < _rate_limit_delay:
        wait_time = _rate_limit_delay - time_since_last_call
        print(f"⏳ Rate limit: Waiting {wait_time:.1f} seconds before next request...")
        time.sleep(wait_time)
    
    _last_api_call_time = time.time()


def detect_asset_class(symbol: str) -> AssetClass:
    """
    Detect asset class from symbol format.
    
    Rules:
    - Crypto: Contains 'USDT', 'BTC', 'ETH' or similar patterns, no '/' or spaces
    - Forex: Contains '/' separator (e.g., EUR/USD)
    - Equity: Simple uppercase letters, no special separators (e.g., AAPL, MSFT)
    """
    symbol_upper = symbol.upper().strip()
    
    # Check for forex pattern (contains / or _)
    if '/' in symbol or '_' in symbol:
        return AssetClass.FOREX
    
    # Check for crypto patterns (ends with USDT, BTC, ETH, etc. or contains common crypto patterns)
    crypto_patterns = ['USDT', 'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOGE', 'XRP', 'DOT', 'LINK']
    if any(pattern in symbol_upper for pattern in crypto_patterns) and '/' not in symbol_upper:
        return AssetClass.CRYPTO
    
    # Default to equity (simple uppercase letters)
    return AssetClass.EQUITY


def normalize_symbol(symbol: str, asset_class: AssetClass) -> str:
    """Normalize symbol format based on asset class."""
    if asset_class == AssetClass.FOREX:
        return symbol.replace("_", "/").upper()
    elif asset_class == AssetClass.EQUITY:
        return symbol.upper().strip()
    else:  # CRYPTO
        return symbol.upper()


def get_default_timezone(asset_class: AssetClass) -> str:
    """Get default timezone for asset class."""
    if asset_class == AssetClass.EQUITY:
        return "America/New_York"
    elif asset_class == AssetClass.FOREX:
        return "Exchange"
    else:  # CRYPTO
        return "UTC"


def authenticate_binance():
    """Authenticate with Binance API."""
    if not BINANCE_AVAILABLE:
        print("Error: python-binance library not installed.")
        print("Install it with: pip install python-binance")
        sys.exit(1)
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    if api_key and api_secret:
        try:
            client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
            print(f"✓ Authenticated with Binance API (testnet: {testnet})")
            return client
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            sys.exit(1)
    else:
        try:
            client = Client(testnet=testnet)
            print("✓ Using Binance public API (no authentication required)")
            print("  Note: For higher rate limits, set BINANCE_API_KEY and BINANCE_API_SECRET")
            return client
        except Exception as e:
            print(f"✗ Failed to initialize Binance client: {e}")
            sys.exit(1)


def authenticate_twelvedata():
    """Authenticate with Twelve Data API."""
    if not TWELVEDATA_AVAILABLE:
        print("Error: twelvedata library not installed.")
        print("Install it with: pip install twelvedata")
        sys.exit(1)
    
    api_key = os.getenv("TWELVEDATA_SECRET")
    
    if not api_key:
        print("✗ TWELVEDATA_SECRET environment variable not set.")
        print("  Set it in your .env file or export it as an environment variable.")
        sys.exit(1)
    
    try:
        client = TDClient(apikey=api_key)
        print("✓ Authenticated with Twelve Data API")
        return client
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)


def fetch_ohlcv_binance(
    client: Client,
    symbol: str,
    timeframe: str,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[OHLCV]:
    """Fetch OHLCV data from Binance."""
    interval_map = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "1w": Client.KLINE_INTERVAL_1WEEK,
        "1M": Client.KLINE_INTERVAL_1MONTH,
    }
    
    if timeframe not in interval_map:
        print(f"✗ Unsupported timeframe: {timeframe}")
        print(f"  Supported: {', '.join(interval_map.keys())}")
        sys.exit(1)
    
    interval = interval_map[timeframe]
    symbol_upper = symbol.upper()
    
    try:
        client.ping()
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        sys.exit(1)
    
    try:
        if limit:
            if limit > 1000:
                print("⚠ Warning: Binance limit is 1000 candles per request. Using 1000.")
                limit = 1000
            
            print(f"Fetching {limit} candles for {symbol_upper} ({timeframe})...")
            klines = client.get_klines(
                symbol=symbol_upper,
                interval=interval,
                limit=limit,
            )
        elif start and end:
            start_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000)
            
            print(f"Fetching {symbol_upper} ({timeframe}) from {start} to {end}...")
            
            all_klines = []
            current_start = start_ms
            
            while current_start < end_ms:
                klines = client.get_klines(
                    symbol=symbol_upper,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_ms,
                    limit=1000,
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                if len(klines) < 1000:
                    break
                
                current_start = klines[-1][0] + 1
            
            klines = all_klines
        else:
            print("✗ Either --limit or both --start and --end must be provided")
            sys.exit(1)
        
        if not klines:
            print(f"✗ No data returned for {symbol_upper}")
            sys.exit(1)
        
        ohlcv_data = []
        for kline in klines:
            ohlcv = OHLCV(
                timestamp=to_utc(datetime.fromtimestamp(kline[0] / 1000)),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5]),
                symbol=symbol_upper,
                timeframe=timeframe,
                asset_class=AssetClass.CRYPTO,
                source="binance",
            )
            validate_ohlcv(ohlcv)
            ohlcv_data.append(ohlcv)
        
        print(f"✓ Successfully fetched {len(ohlcv_data)} candles")
        return ohlcv_data
    
    except BinanceAPIException as e:
        print(f"✗ Binance API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        sys.exit(1)


def fetch_ohlcv_twelvedata(
    client: TDClient,
    symbol: str,
    timeframe: str,
    asset_class: AssetClass,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
) -> List[OHLCV]:
    """Fetch OHLCV data from Twelve Data."""
    interval_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1day",
        "1w": "1week",
        "1M": "1month",
    }
    
    if timeframe not in interval_map:
        print(f"✗ Unsupported timeframe: {timeframe}")
        print(f"  Supported: {', '.join(interval_map.keys())}")
        sys.exit(1)
    
    interval = interval_map[timeframe]
    symbol_normalized = normalize_symbol(symbol, asset_class)
    default_timezone = timezone if timezone else get_default_timezone(asset_class)
    
    try:
        wait_for_rate_limit()
        
        if limit:
            print(f"Fetching {limit} candles for {symbol_normalized} ({timeframe})...")
            
            ts = client.time_series(
                symbol=symbol_normalized,
                interval=interval,
                outputsize=limit,
                timezone=default_timezone,
            )
            
            df = ts.as_pandas()
        
        elif start and end:
            print(f"Fetching {symbol_normalized} ({timeframe}) from {start} to {end}...")
            
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            
            wait_for_rate_limit()
            
            ts = client.time_series(
                symbol=symbol_normalized,
                interval=interval,
                start_date=start_str,
                end_date=end_str,
                timezone=default_timezone,
            )
            
            df = ts.as_pandas()
        
        else:
            print("✗ Either --limit or both --start and --end must be provided")
            sys.exit(1)
        
        if df.empty:
            print(f"✗ No data returned for {symbol_normalized}")
            sys.exit(1)
        
        ohlcv_data = []
        for timestamp, row in df.iterrows():
            try:
                ts = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
                ohlcv = OHLCV(
                    timestamp=to_utc(ts),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]) if "volume" in row else None,
                    symbol=symbol_normalized,
                    timeframe=timeframe,
                    asset_class=asset_class,
                    source="twelvedata",
                )
                validate_ohlcv(ohlcv)
                ohlcv_data.append(ohlcv)
            except ValueError:
                # Validation errors must fail fast - do not suppress
                raise
            except Exception as e:
                print(f"⚠ Warning: Failed to process data point: {e}")
                continue
        
        print(f"✓ Successfully fetched {len(ohlcv_data)} candles")
        return ohlcv_data
    
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        sys.exit(1)


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    asset_class: AssetClass,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
) -> List[OHLCV]:
    """Unified function to fetch OHLCV data from appropriate provider."""
    if asset_class == AssetClass.CRYPTO:
        client = authenticate_binance()
        return fetch_ohlcv_binance(client, symbol, timeframe, limit, start, end)
    else:
        client = authenticate_twelvedata()
        return fetch_ohlcv_twelvedata(
            client, symbol, timeframe, asset_class, limit, start, end, timezone
        )


def stream_realtime_binance(
    symbol: str,
    timeframe: str,
    on_candle: Optional[Callable[[OHLCV], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """Stream real-time OHLCV kline data from Binance WebSocket."""
    if not WEBSOCKET_AVAILABLE:
        print("Error: websocket-client library not installed.")
        print("Install it with: pip install websocket-client")
        sys.exit(1)
    
    timeframe_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w", "1M": "1M",
    }
    
    if timeframe not in timeframe_map:
        print(f"✗ Unsupported timeframe for streaming: {timeframe}")
        sys.exit(1)
    
    symbol_lower = symbol.lower()
    interval = timeframe_map[timeframe]
    stream_name = f"{symbol_lower}@kline_{interval}"
    ws_url = f"wss://stream.binance.com:9443/ws/{stream_name}"
    
    print(f"Connecting to Binance WebSocket: {ws_url}")
    print(f"Streaming real-time {timeframe} candles for {symbol.upper()}...")
    print("Press Ctrl+C to stop streaming\n")
    
    last_pong_time = time.time()
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    
    def on_message(ws, message):
        nonlocal last_pong_time, reconnect_attempts
        
        try:
            data = json.loads(message)
            
            if isinstance(data, str) and data == "ping":
                ws.send("pong")
                last_pong_time = time.time()
                return
            
            if "k" in data:
                kline = data["k"]
                
                if kline.get("x", False):
                    candle = OHLCV(
                        timestamp=to_utc(datetime.fromtimestamp(kline["t"] / 1000)),
                        open=float(kline["o"]),
                        high=float(kline["h"]),
                        low=float(kline["l"]),
                        close=float(kline["c"]),
                        volume=float(kline["v"]),
                        symbol=symbol.upper(),
                        timeframe=timeframe,
                        asset_class=AssetClass.CRYPTO,
                        source="binance",
                    )
                    validate_ohlcv(candle)
                    
                    if on_candle:
                        on_candle(candle)
                    else:
                        timestamp_str = candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            f"[{timestamp_str}] {candle.symbol} {candle.timeframe}: "
                            f"O={candle.open:.8f} H={candle.high:.8f} "
                            f"L={candle.low:.8f} C={candle.close:.8f} "
                            f"V={candle.volume:.8f}"
                        )
        
        except json.JSONDecodeError as e:
            if on_error:
                on_error(e)
            else:
                print(f"✗ JSON decode error: {e}")
        except Exception as e:
            if on_error:
                on_error(e)
            else:
                print(f"✗ Error processing message: {e}")
    
    def on_error_handler(ws, error):
        nonlocal reconnect_attempts
        reconnect_attempts += 1
        
        if on_error:
            on_error(error)
        else:
            print(f"✗ WebSocket error: {error}")
        
        if reconnect_attempts >= max_reconnect_attempts:
            print(f"✗ Max reconnection attempts ({max_reconnect_attempts}) reached. Exiting.")
            ws.close()
            sys.exit(1)
    
    def on_close(ws, close_status_code, close_msg):
        if close_status_code:
            print(f"\n✗ WebSocket closed: {close_status_code} - {close_msg}")
        else:
            print("\n✓ WebSocket connection closed")
    
    def on_open(ws):
        nonlocal reconnect_attempts
        reconnect_attempts = 0
        print("✓ WebSocket connected successfully")
    
    def on_pong(ws, message):
        nonlocal last_pong_time
        last_pong_time = time.time()
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error_handler,
        on_close=on_close,
        on_open=on_open,
        on_pong=on_pong,
    )
    
    def ping_thread():
        while ws.sock and ws.sock.connected:
            time.sleep(20)
            try:
                ws.send("ping")
            except:
                break
    
    ping_thread_obj = threading.Thread(target=ping_thread, daemon=True)
    ping_thread_obj.start()
    
    def signal_handler(sig, frame):
        print("\n\nStopping WebSocket stream...")
        ws.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        ws.run_forever(ping_interval=20, ping_timeout=10)
    except KeyboardInterrupt:
        print("\n\nStopping WebSocket stream...")
        ws.close()


def stream_realtime_twelvedata(
    symbol: str,
    asset_class: AssetClass,
    on_price: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """Stream real-time price data from Twelve Data WebSocket."""
    if not WEBSOCKET_AVAILABLE:
        print("Error: websocket-client library not installed.")
        print("Install it with: pip install websocket-client")
        sys.exit(1)
    
    api_key = os.getenv("TWELVEDATA_SECRET")
    
    if not api_key:
        print("✗ TWELVEDATA_SECRET environment variable not set.")
        sys.exit(1)
    
    symbol_normalized = normalize_symbol(symbol, asset_class)
    ws_url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
    
    print(f"Connecting to Twelve Data WebSocket: {ws_url}")
    print(f"Streaming real-time prices for {symbol_normalized}...")
    print("Press Ctrl+C to stop streaming\n")
    
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    
    def on_message(ws, message):
        nonlocal reconnect_attempts
        
        try:
            data = json.loads(message)
            
            if data.get("event") == "subscribe-status":
                if data.get("status") == "ok":
                    print("✓ Successfully subscribed to price stream")
                    if "success" in data:
                        for item in data["success"]:
                            print(f"  - {item.get('symbol', 'N/A')} on {item.get('exchange', 'N/A')}")
                elif "fails" in data and data["fails"]:
                    print(f"✗ Subscription failed: {data['fails']}")
                    print("\nPossible reasons:")
                    print("  1. Free/Basic tier may have limited WebSocket access")
                    print("  2. Symbol might not be available for real-time streaming")
                    print("  3. WebSocket credits may be exhausted")
                    print("\nNote: Historical data fetching works fine - this is a WebSocket limitation.")
                return
            
            if data.get("event") == "price":
                price_data = {
                    "timestamp": datetime.fromtimestamp(data.get("timestamp", time.time())),
                    "symbol": data.get("symbol", symbol_normalized),
                    "price": float(data.get("price", 0)),
                    "bid": float(data.get("bid", 0)) if "bid" in data else None,
                    "ask": float(data.get("ask", 0)) if "ask" in data else None,
                    "day_volume": int(data.get("day_volume", 0)) if "day_volume" in data else None,
                }
                
                if on_price:
                    on_price(price_data)
                else:
                    timestamp_str = price_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    if asset_class == AssetClass.EQUITY:
                        price_str = f"${price_data['price']:.2f}"
                        if price_data["bid"] and price_data["ask"]:
                            price_str += f" (Bid: ${price_data['bid']:.2f}, Ask: ${price_data['ask']:.2f})"
                        if price_data["day_volume"]:
                            price_str += f" Volume: {price_data['day_volume']:,}"
                    else:
                        price_str = f"{price_data['price']:.5f}"
                        if price_data["bid"] and price_data["ask"]:
                            price_str += f" (Bid: {price_data['bid']:.5f}, Ask: {price_data['ask']:.5f})"
                    print(f"[{timestamp_str}] {price_data['symbol']}: {price_str}")
        
        except json.JSONDecodeError as e:
            if on_error:
                on_error(e)
            else:
                print(f"✗ JSON decode error: {e}")
        except Exception as e:
            if on_error:
                on_error(e)
            else:
                print(f"✗ Error processing message: {e}")
    
    def on_error_handler(ws, error):
        nonlocal reconnect_attempts
        reconnect_attempts += 1
        
        if on_error:
            on_error(error)
        else:
            print(f"✗ WebSocket error: {error}")
        
        if reconnect_attempts >= max_reconnect_attempts:
            print(f"✗ Max reconnection attempts ({max_reconnect_attempts}) reached. Exiting.")
            ws.close()
            sys.exit(1)
    
    def on_close(ws, close_status_code, close_msg):
        if close_status_code:
            print(f"\n✗ WebSocket closed: {close_status_code} - {close_msg}")
        else:
            print("\n✓ WebSocket connection closed")
    
    def on_open(ws):
        nonlocal reconnect_attempts
        reconnect_attempts = 0
        print("✓ WebSocket connected successfully")
        
        symbol_type = "Forex" if asset_class == AssetClass.FOREX else "Stock"
        subscribe_msg = {
            "action": "subscribe",
            "params": {
                "symbols": [{
                    "symbol": symbol_normalized,
                    "type": symbol_type
                }]
            }
        }
        ws.send(json.dumps(subscribe_msg))
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error_handler,
        on_close=on_close,
        on_open=on_open,
    )
    
    def heartbeat_thread():
        while ws.sock and ws.sock.connected:
            time.sleep(10)
            try:
                heartbeat_msg = {"action": "heartbeat"}
                ws.send(json.dumps(heartbeat_msg))
            except:
                break
    
    heartbeat_thread_obj = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat_thread_obj.start()
    
    def signal_handler(sig, frame):
        print("\n\nStopping WebSocket stream...")
        try:
            unsubscribe_msg = {
                "action": "unsubscribe",
                "params": {
                    "symbols": symbol_normalized
                }
            }
            ws.send(json.dumps(unsubscribe_msg))
        except:
            pass
        ws.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n\nStopping WebSocket stream...")
        ws.close()


def format_output(
    ohlcv_data: List[OHLCV],
    format_type: str = "table",
    asset_class: AssetClass = AssetClass.CRYPTO
) -> None:
    """
    Format and display OHLCV data with asset-class-aware formatting.
    
    Args:
        ohlcv_data: List of OHLCV objects
        format_type: Output format ('table', 'csv', 'json')
        asset_class: Asset class for formatting (crypto: 8 decimals, forex: 5, equity: 2 with $)
    """
    if format_type == "table":
        print("\n" + "=" * 100)
        print(f"{'Timestamp':<20} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>20}")
        print("=" * 100)
        
        for candle in ohlcv_data:
            timestamp_str = candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            if asset_class == AssetClass.EQUITY:
                open_str = f"${candle.open:>10.2f}"
                high_str = f"${candle.high:>10.2f}"
                low_str = f"${candle.low:>10.2f}"
                close_str = f"${candle.close:>10.2f}"
                volume_str = f"{candle.volume:>20,.0f}" if candle.volume else " " * 20
            elif asset_class == AssetClass.FOREX:
                open_str = f"{candle.open:>12.5f}"
                high_str = f"{candle.high:>12.5f}"
                low_str = f"{candle.low:>12.5f}"
                close_str = f"{candle.close:>12.5f}"
                volume_str = f"{candle.volume:>20.8f}" if candle.volume else " " * 20
            else:  # CRYPTO
                open_str = f"{candle.open:>12.8f}"
                high_str = f"{candle.high:>12.8f}"
                low_str = f"{candle.low:>12.8f}"
                close_str = f"{candle.close:>12.8f}"
                volume_str = f"{candle.volume:>20.8f}" if candle.volume else " " * 20
            
            print(
                f"{timestamp_str:<20} "
                f"{open_str} "
                f"{high_str} "
                f"{low_str} "
                f"{close_str} "
                f"{volume_str}"
            )
        
        print("=" * 100)
    
    elif format_type == "csv":
        print("timestamp,open,high,low,close,volume")
        for candle in ohlcv_data:
            timestamp_str = candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            if asset_class == AssetClass.EQUITY:
                volume_str = str(int(candle.volume)) if candle.volume else ""
            elif asset_class == AssetClass.FOREX:
                volume_str = str(candle.volume) if candle.volume else ""
            else:  # CRYPTO
                volume_str = str(candle.volume) if candle.volume else ""
            
            print(
                f"{timestamp_str},"
                f"{candle.open},"
                f"{candle.high},"
                f"{candle.low},"
                f"{candle.close},"
                f"{volume_str}"
            )
    
    elif format_type == "json":
        output = []
        for candle in ohlcv_data:
            output.append({
                "timestamp": candle.timestamp.isoformat(),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            })
        print(json.dumps(output, indent=2))


def parse_dates(start_str: Optional[str], end_str: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse date strings to datetime objects."""
    if not start_str or not end_str:
        return None, None
    
    try:
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        
        try:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        return start_dt, end_dt
    
    except ValueError as e:
        print(f"✗ Invalid date format: {e}")
        print("  Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch OHLCV data from Binance (Crypto) or Twelve Data (Forex/Equities)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cryptocurrency
  python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100
  
  # Forex
  python pull_ohlcv.py --symbol EUR/USD --timeframe 1h --limit 100
  
  # US Equities
  python pull_ohlcv.py --symbol AAPL --timeframe 1h --limit 100
  
  # Real-time streaming
  python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --stream
  
  # Polling mode (Forex/Equities only)
  python pull_ohlcv.py --symbol EUR/USD --timeframe 1m --limit 1 --poll
        """,
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Symbol (e.g., BTCUSDT, EUR/USD, AAPL)",
    )
    
    parser.add_argument(
        "--timeframe",
        type=str,
        required=False,
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"],
        help="Timeframe interval (required for historical data, optional for streaming)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of candles to fetch. Required if --start/--end not provided.",
    )
    
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). Required with --end.",
    )
    
    parser.add_argument(
        "--end",
        type=str,
        help="End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). Required with --start.",
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table). Ignored in streaming mode.",
    )
    
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable real-time WebSocket streaming.",
    )
    
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Poll REST API every 60 seconds (Forex/Equities only). Requires --timeframe and --limit.",
    )
    
    parser.add_argument(
        "--timezone",
        type=str,
        help="Timezone for timestamps (Forex/Equities only). Defaults: Exchange (Forex), America/New_York (Equity)",
    )
    
    args = parser.parse_args()
    
    # Detect asset class
    asset_class = detect_asset_class(args.symbol)
    print(f"Detected asset class: {asset_class.value.upper()}")
    
    # Validate arguments
    if not args.stream and not args.poll:
        if not args.timeframe:
            parser.error("--timeframe is required when not using --stream or --poll")
        if not args.limit and not (args.start and args.end):
            parser.error("Either --limit or both --start and --end must be provided (or use --stream/--poll)")
    
    if args.poll:
        if asset_class == AssetClass.CRYPTO:
            parser.error("--poll is not supported for cryptocurrency (use --stream instead)")
        if not args.timeframe:
            parser.error("--timeframe is required when using --poll")
        if not args.limit:
            parser.error("--limit is required when using --poll (typically use --limit 1)")
    
    if args.start and not args.end:
        parser.error("--end is required when --start is provided")
    
    if args.end and not args.start:
        parser.error("--start is required when --end is provided")
    
    # Parse dates
    start_dt, end_dt = parse_dates(args.start, args.end)
    
    # Handle polling mode
    if args.poll:
        print("=" * 80)
        print("POLLING MODE: Fetching latest data every 60 seconds")
        print("=" * 80)
        print(f"Symbol: {args.symbol}")
        print(f"Timeframe: {args.timeframe}")
        print(f"Limit: {args.limit} candle(s) per request")
        print("Press Ctrl+C to stop polling\n")
        
        def signal_handler(sig, frame):
            print("\n\nStopping polling...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        iteration = 0
        while True:
            iteration += 1
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Poll #{iteration}")
                print("-" * 80)
                
                ohlcv_data = fetch_ohlcv(
                    symbol=args.symbol,
                    timeframe=args.timeframe,
                    asset_class=asset_class,
                    limit=args.limit,
                    start=None,
                    end=None,
                    timezone=args.timezone,
                )
                
                format_output(ohlcv_data, format_type=args.format, asset_class=asset_class)
                
                print(f"\n⏳ Waiting 60 seconds before next poll...")
                print("   (Press Ctrl+C to stop)")
                time.sleep(60)
            
            except KeyboardInterrupt:
                print("\n\nStopping polling...")
                sys.exit(0)
            except Exception as e:
                print(f"✗ Error during polling: {e}")
                print("   Retrying in 60 seconds...")
                time.sleep(60)
    
    # Handle streaming mode
    elif args.stream:
        if args.limit or (args.start and args.end):
            if not args.timeframe:
                print("✗ --timeframe is required when fetching historical data")
                sys.exit(1)
            
            print("=" * 80)
            print("FETCHING HISTORICAL DATA")
            print("=" * 80)
            
            ohlcv_data = fetch_ohlcv(
                symbol=args.symbol,
                timeframe=args.timeframe,
                asset_class=asset_class,
                limit=args.limit,
                start=start_dt,
                end=end_dt,
                timezone=args.timezone,
            )
            
            format_output(ohlcv_data, format_type=args.format, asset_class=asset_class)
            
            print("\n" + "=" * 80)
            print("STARTING REAL-TIME STREAMING")
            print("=" * 80 + "\n")
        
        if asset_class == AssetClass.CRYPTO:
            if not args.timeframe:
                print("✗ --timeframe is required for crypto streaming")
                sys.exit(1)
            
            def on_new_candle(candle: OHLCV):
                timestamp_str = candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"[{timestamp_str}] {candle.symbol} {candle.timeframe}: "
                    f"O={candle.open:.8f} H={candle.high:.8f} "
                    f"L={candle.low:.8f} C={candle.close:.8f} "
                    f"V={candle.volume:.8f}"
                )
            
            def on_error_handler(error: Exception):
                print(f"✗ Streaming error: {error}")
            
            stream_realtime_binance(
                symbol=args.symbol,
                timeframe=args.timeframe,
                on_candle=on_new_candle,
                on_error=on_error_handler,
            )
        else:
            def on_new_price(price_data: Dict[str, Any]):
                timestamp_str = price_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                if asset_class == AssetClass.EQUITY:
                    price_str = f"${price_data['price']:.2f}"
                    if price_data.get("bid") and price_data.get("ask"):
                        price_str += f" (Bid: ${price_data['bid']:.2f}, Ask: ${price_data['ask']:.2f})"
                    if price_data.get("day_volume"):
                        price_str += f" Volume: {price_data['day_volume']:,}"
                else:
                    price_str = f"{price_data['price']:.5f}"
                    if price_data.get("bid") and price_data.get("ask"):
                        price_str += f" (Bid: {price_data['bid']:.5f}, Ask: {price_data['ask']:.5f})"
                print(f"[{timestamp_str}] {price_data['symbol']}: {price_str}")
            
            def on_error_handler(error: Exception):
                print(f"✗ Streaming error: {error}")
            
            stream_realtime_twelvedata(
                symbol=args.symbol,
                asset_class=asset_class,
                on_price=on_new_price,
                on_error=on_error_handler,
            )
    
    else:
        # Historical data only
        ohlcv_data = fetch_ohlcv(
            symbol=args.symbol,
            timeframe=args.timeframe,
            asset_class=asset_class,
            limit=args.limit,
            start=start_dt,
            end=end_dt,
            timezone=args.timezone,
        )
        
        format_output(ohlcv_data, format_type=args.format, asset_class=asset_class)


if __name__ == "__main__":
    main()
