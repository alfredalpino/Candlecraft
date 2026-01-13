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
import importlib.util
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable, Tuple, Protocol
import csv
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import from candlecraft library
from candlecraft import fetch_ohlcv, OHLCV, AssetClass
from candlecraft.utils import detect_asset_class, to_utc, normalize_symbol, validate_ohlcv
from candlecraft.providers import authenticate_binance, authenticate_twelvedata
from candlecraft.api import load_indicator

# Import providers for streaming
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


class Sink(Protocol):
    """
    Output sink for OHLCV data.
    Implementations decide where and how data is written.
    """
    def write(self, data: List[OHLCV]) -> None:
        ...


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


def format_ohlcv_table(data: List[OHLCV], asset_class: AssetClass = AssetClass.CRYPTO, indicator_data: Optional[List[Dict[str, Any]]] = None) -> str:
    """Format OHLCV data as a table. Returns formatted string."""
    lines = []
    lines.append("\n" + "=" * 100)
    
    # Build header
    header = f"{'Timestamp':<20} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>20}"
    
    # Add indicator columns if present
    if indicator_data and len(indicator_data) > 0:
        indicator_keys = sorted(set(key for row in indicator_data if row for key in row.keys()))
        for key in indicator_keys:
            header += f" {key.capitalize():>12}"
    
    lines.append(header)
    lines.append("=" * 100)
    
    for idx, candle in enumerate(data):
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
        
        row = (
            f"{timestamp_str:<20} "
            f"{open_str} "
            f"{high_str} "
            f"{low_str} "
            f"{close_str} "
            f"{volume_str}"
        )
        
        # Add indicator values if present
        if indicator_data and idx < len(indicator_data) and indicator_data[idx]:
            indicator_keys = sorted(set(key for row in indicator_data if row for key in row.keys()))
            for key in indicator_keys:
                val = indicator_data[idx].get(key) if idx < len(indicator_data) else None
                if val is not None:
                    row += f" {val:>12.8f}"
                else:
                    row += " " * 13
        
        lines.append(row)
    
    lines.append("=" * 100)
    return "\n".join(lines)


def format_ohlcv_json(data: List[OHLCV], indicator_data: Optional[List[Dict[str, Any]]] = None) -> str:
    """Format OHLCV data as JSON. Returns formatted string."""
    output = []
    for idx, candle in enumerate(data):
        row = {
            "timestamp": candle.timestamp.isoformat(),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        
        # Add indicator values if present
        if indicator_data and idx < len(indicator_data) and indicator_data[idx]:
            row.update(indicator_data[idx])
        
        output.append(row)
    return json.dumps(output, indent=2)


class StdoutSink:
    """
    Writes formatted OHLCV data to stdout.
    """
    def __init__(self, formatter: Callable[[List[OHLCV]], str]):
        self.formatter = formatter

    def write(self, data: List[OHLCV]) -> None:
        output = self.formatter(data)
        print(output)
    
    def write_with_indicators(self, data: List[OHLCV], indicator_data: Optional[List[Dict[str, Any]]]) -> None:
        """Write data with indicator values."""
        output = self.formatter(data, indicator_data)
        print(output)


class CSVSink:
    """
    Writes OHLCV data to a CSV file.
    """
    def __init__(self, path: str, indicator_data: Optional[List[Dict[str, Any]]] = None):
        self.path = Path(path)
        self.indicator_data = indicator_data

    def write(self, data: List[OHLCV]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("w", newline="") as f:
            writer = csv.writer(f)
            
            # Build header
            header = [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "symbol",
                "timeframe",
                "asset_class",
                "source"
            ]
            
            # Add indicator columns if present
            if self.indicator_data and len(self.indicator_data) > 0:
                indicator_keys = sorted(set(key for row in self.indicator_data if row for key in row.keys()))
                header.extend(indicator_keys)
            
            writer.writerow(header)

            for idx, dp in enumerate(data):
                row = [
                    dp.timestamp.isoformat(),
                    dp.open,
                    dp.high,
                    dp.low,
                    dp.close,
                    dp.volume,
                    dp.symbol,
                    dp.timeframe,
                    dp.asset_class.value,
                    dp.source
                ]
                
                # Add indicator values if present
                if self.indicator_data and idx < len(self.indicator_data) and self.indicator_data[idx]:
                    indicator_keys = sorted(set(key for r in self.indicator_data if r for key in r.keys()))
                    for key in indicator_keys:
                        val = self.indicator_data[idx].get(key) if idx < len(self.indicator_data) else None
                        row.append(val)
                
                writer.writerow(row)


def load_indicator_cli(indicator_name: str) -> Optional[Callable[[List[OHLCV]], List[Dict[str, Any]]]]:
    """
    Dynamically load an indicator module from the indicators/ directory.
    CLI wrapper that handles errors with sys.exit.
    
    Args:
        indicator_name: Name of the indicator (e.g., 'macd')
    
    Returns:
        The indicator's calculate function, or None if not found.
    """
    indicators_dir = Path(__file__).parent / "indicators"
    
    try:
        return load_indicator(indicator_name, indicators_dir)
    except FileNotFoundError as e:
        print(f"✗ {e}")
        sys.exit(1)
    except (AttributeError, ImportError) as e:
        print(f"✗ {e}")
        sys.exit(1)


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
    
    parser.add_argument(
        "--indicator",
        type=str,
        help="Calculate and display technical indicator (e.g., 'macd'). Indicator module must exist in indicators/ directory.",
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
    
    # Load indicator if specified
    indicator_func = None
    if args.indicator:
        indicator_func = load_indicator_cli(args.indicator)
        print(f"✓ Loaded indicator: {args.indicator}")
    
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
                
                # Calculate indicator if specified
                indicator_data = None
                if indicator_func:
                    try:
                        indicator_data = indicator_func(ohlcv_data)
                    except Exception as e:
                        print(f"✗ Error calculating indicator: {e}")
                        indicator_data = None
                
                if args.format == "table":
                    if indicator_data:
                        print(format_ohlcv_table(ohlcv_data, asset_class, indicator_data))
                    else:
                        sink = StdoutSink(lambda data: format_ohlcv_table(data, asset_class))
                        sink.write(ohlcv_data)
                elif args.format == "csv":
                    sink = CSVSink("output.csv", indicator_data)
                    sink.write(ohlcv_data)
                else:
                    if indicator_data:
                        print(format_ohlcv_json(ohlcv_data, indicator_data))
                    else:
                        sink = StdoutSink(format_ohlcv_json)
                        sink.write(ohlcv_data)
                
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
            
            # Calculate indicator if specified
            indicator_data = None
            if indicator_func:
                try:
                    indicator_data = indicator_func(ohlcv_data)
                except Exception as e:
                    print(f"✗ Error calculating indicator: {e}")
                    indicator_data = None
            
            if args.format == "table":
                if indicator_data:
                    print(format_ohlcv_table(ohlcv_data, asset_class, indicator_data))
                else:
                    sink = StdoutSink(lambda data: format_ohlcv_table(data, asset_class))
                    sink.write(ohlcv_data)
            elif args.format == "csv":
                sink = CSVSink("output.csv", indicator_data)
                sink.write(ohlcv_data)
            else:
                if indicator_data:
                    print(format_ohlcv_json(ohlcv_data, indicator_data))
                else:
                    sink = StdoutSink(format_ohlcv_json)
                    sink.write(ohlcv_data)
            
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
        
        # Calculate indicator if specified
        indicator_data = None
        if indicator_func:
            try:
                indicator_data = indicator_func(ohlcv_data)
            except Exception as e:
                print(f"✗ Error calculating indicator: {e}")
                indicator_data = None
        
        if args.format == "table":
            if indicator_data:
                print(format_ohlcv_table(ohlcv_data, asset_class, indicator_data))
            else:
                sink = StdoutSink(lambda data: format_ohlcv_table(data, asset_class))
                sink.write(ohlcv_data)
        elif args.format == "csv":
            sink = CSVSink("output.csv", indicator_data)
            sink.write(ohlcv_data)
        else:
            if indicator_data:
                print(format_ohlcv_json(ohlcv_data, indicator_data))
            else:
                sink = StdoutSink(format_ohlcv_json)
                sink.write(ohlcv_data)


if __name__ == "__main__":
    main()
