#!/usr/bin/env python3
"""
US Equities OHLCV Data Puller with Real-time Streaming

Supports both historical data (REST API) and real-time streaming (WebSocket) using Twelve Data.

Usage:
    # Historical data (REST API)
    python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 100
    python pull_us-eq.py --symbol MSFT --timeframe 1d --start 2024-01-01 --end 2024-01-31
    
    # Real-time streaming (WebSocket)
    python pull_us-eq.py --symbol AAPL --stream
    
    # Historical + Real-time (backfill then stream)
    python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 100 --stream
    
    # Poll REST API every 60 seconds (1 call per minute, free tier compliant)
    python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 1 --poll
"""

import os
import sys
import argparse
import json
import time
import signal
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

try:
    from twelvedata import TDClient
except ImportError:
    print("Error: twelvedata library not installed.")
    print("Install it with: pip install twelvedata")
    sys.exit(1)

try:
    import websocket
except ImportError:
    print("Error: websocket-client library not installed.")
    print("Install it with: pip install websocket-client")
    sys.exit(1)


# Rate limiting: Track last API call time
_last_api_call_time = 0
_rate_limit_delay = 60  # 60 seconds between REST API calls for free tier


def wait_for_rate_limit():
    """Wait if necessary to respect rate limit (1 request per minute)."""
    global _last_api_call_time
    
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    
    if time_since_last_call < _rate_limit_delay:
        wait_time = _rate_limit_delay - time_since_last_call
        print(f"⏳ Rate limit: Waiting {wait_time:.1f} seconds before next request...")
        time.sleep(wait_time)
    
    _last_api_call_time = time.time()


def authenticate() -> TDClient:
    """
    Authenticate with Twelve Data API using environment variables.
    
    Returns:
        Authenticated Twelve Data Client instance
    
    Raises:
        SystemExit: If authentication fails or API key is missing
    """
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


def fetch_ohlcv(
    client: TDClient,
    symbol: str,
    timeframe: str,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timezone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV data from Twelve Data for US equities.
    
    Args:
        client: Authenticated Twelve Data client
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        timeframe: Timeframe interval (e.g., '1min', '1hour', '1day')
        limit: Number of candles to fetch
        start: Start datetime (optional, used with end)
        end: End datetime (optional, used with start)
        timezone: Timezone for timestamps (default: 'America/New_York' for US stocks)
    
    Returns:
        List of OHLCV dictionaries with keys: timestamp, open, high, low, close, volume
    
    Raises:
        SystemExit: If data fetching fails
    """
    # Map timeframe to Twelve Data interval format
    # Twelve Data supports: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 8h, 1day, 1week, 1month
    interval_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",  # Twelve Data uses "1h" not "1hour"
        "4h": "4h",  # Twelve Data uses "4h" not "4hour"
        "1d": "1day",
        "1w": "1week",
        "1M": "1month",
    }
    
    if timeframe not in interval_map:
        print(f"✗ Unsupported timeframe: {timeframe}")
        print(f"  Supported: {', '.join(interval_map.keys())}")
        sys.exit(1)
    
    interval = interval_map[timeframe]
    
    # Normalize symbol format (uppercase, no spaces)
    symbol_normalized = symbol.upper().strip()
    
    # Default timezone for US stocks is America/New_York
    default_timezone = timezone if timezone else "America/New_York"
    
    try:
        wait_for_rate_limit()  # Respect rate limit
        
        if limit:
            # Fetch by limit
            print(f"Fetching {limit} candles for {symbol_normalized} ({timeframe})...")
            
            ts = client.time_series(
                symbol=symbol_normalized,
                interval=interval,
                outputsize=limit,
                timezone=default_timezone,
            )
            
            df = ts.as_pandas()
        
        elif start and end:
            # Fetch by date range
            print(f"Fetching {symbol_normalized} ({timeframe}) from {start} to {end}...")
            
            # Twelve Data accepts date strings in YYYY-MM-DD format
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            
            wait_for_rate_limit()  # Respect rate limit
            
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
        
        # Format data
        ohlcv_data = []
        for timestamp, row in df.iterrows():
            try:
                ohlcv_data.append({
                    "timestamp": timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]) if "volume" in row else None,
                })
            except Exception as e:
                print(f"⚠ Warning: Failed to process data point: {e}")
                continue
        
        print(f"✓ Successfully fetched {len(ohlcv_data)} candles")
        return ohlcv_data
    
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        sys.exit(1)


def stream_realtime_prices(
    symbol: str,
    on_price: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """
    Stream real-time price data from Twelve Data WebSocket for US equities.
    
    Note: Twelve Data WebSocket provides real-time prices, not OHLCV candles.
    For OHLCV candles, you would need to aggregate the price data or use
    the REST API with rate limiting.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        on_price: Callback function called when a new price is received
        on_error: Callback function called on errors
    """
    api_key = os.getenv("TWELVEDATA_SECRET")
    
    if not api_key:
        print("✗ TWELVEDATA_SECRET environment variable not set.")
        sys.exit(1)
    
    # Normalize symbol format
    symbol_normalized = symbol.upper().strip()
    
    # Twelve Data WebSocket URL
    ws_url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
    
    print(f"Connecting to Twelve Data WebSocket: {ws_url}")
    print(f"Streaming real-time prices for {symbol_normalized}...")
    print("Press Ctrl+C to stop streaming\n")
    
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    
    def on_message(ws, message):
        """Handle incoming WebSocket messages."""
        nonlocal reconnect_attempts
        
        try:
            data = json.loads(message)
            
            # Handle status events
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
                    print("  4. Try using major stocks like AAPL, MSFT, TSLA (more commonly available)")
                    print("\nNote: Historical data fetching works fine - this is a WebSocket limitation.")
                return
            
            # Handle price events
            if data.get("event") == "price":
                price_data = {
                    "timestamp": datetime.fromtimestamp(data.get("timestamp", time.time())),
                    "symbol": data.get("symbol", symbol_normalized),
                    "price": float(data.get("price", 0)),
                    "bid": float(data.get("bid", 0)) if "bid" in data else None,
                    "ask": float(data.get("ask", 0)) if "ask" in data else None,
                    "day_volume": int(data.get("day_volume", 0)) if "day_volume" in data else None,
                }
                
                # Call callback if provided
                if on_price:
                    on_price(price_data)
                else:
                    # Default: print the price
                    timestamp_str = price_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    price_str = f"${price_data['price']:.2f}"
                    if price_data["bid"] and price_data["ask"]:
                        price_str += f" (Bid: ${price_data['bid']:.2f}, Ask: ${price_data['ask']:.2f})"
                    if price_data["day_volume"]:
                        price_str += f" Volume: {price_data['day_volume']:,}"
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
        """Handle WebSocket errors."""
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
        """Handle WebSocket close."""
        if close_status_code:
            print(f"\n✗ WebSocket closed: {close_status_code} - {close_msg}")
        else:
            print("\n✓ WebSocket connection closed")
    
    def on_open(ws):
        """Handle WebSocket open."""
        nonlocal reconnect_attempts
        reconnect_attempts = 0
        print("✓ WebSocket connected successfully")
        
        # Subscribe to symbol using extended format with explicit type for stocks
        subscribe_msg = {
            "action": "subscribe",
            "params": {
                "symbols": [{
                    "symbol": symbol_normalized,
                    "type": "Stock"
                }]
            }
        }
        ws.send(json.dumps(subscribe_msg))
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error_handler,
        on_close=on_close,
        on_open=on_open,
    )
    
    # Set up heartbeat (send every 10 seconds as recommended)
    def heartbeat_thread():
        """Send periodic heartbeats to keep connection alive."""
        while ws.sock and ws.sock.connected:
            time.sleep(10)
            try:
                heartbeat_msg = {"action": "heartbeat"}
                ws.send(json.dumps(heartbeat_msg))
            except:
                break
    
    # Start heartbeat thread
    heartbeat_thread_obj = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat_thread_obj.start()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nStopping WebSocket stream...")
        # Unsubscribe before closing
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
    
    # Run WebSocket (blocks until connection closes)
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n\nStopping WebSocket stream...")
        ws.close()


def format_output(ohlcv_data: List[Dict[str, Any]], format_type: str = "table") -> None:
    """
    Format and display OHLCV data.
    
    Args:
        ohlcv_data: List of OHLCV dictionaries
        format_type: Output format ('table', 'csv', 'json')
    """
    if format_type == "table":
        # Table format
        print("\n" + "=" * 100)
        print(f"{'Timestamp':<20} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>20}")
        print("=" * 100)
        
        for candle in ohlcv_data:
            timestamp_str = candle["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            volume_str = f"{candle['volume']:>20,.0f}" if candle.get("volume") else " " * 20
            print(
                f"{timestamp_str:<20} "
                f"${candle['open']:>10.2f} "
                f"${candle['high']:>10.2f} "
                f"${candle['low']:>10.2f} "
                f"${candle['close']:>10.2f} "
                f"{volume_str}"
            )
        
        print("=" * 100)
    
    elif format_type == "csv":
        # CSV format
        print("timestamp,open,high,low,close,volume")
        for candle in ohlcv_data:
            timestamp_str = candle["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            volume_str = str(int(candle.get("volume", 0))) if candle.get("volume") else ""
            print(
                f"{timestamp_str},"
                f"{candle['open']},"
                f"{candle['high']},"
                f"{candle['low']},"
                f"{candle['close']},"
                f"{volume_str}"
            )
    
    elif format_type == "json":
        # JSON format
        output = []
        for candle in ohlcv_data:
            output.append({
                "timestamp": candle["timestamp"].isoformat(),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume"),
            })
        print(json.dumps(output, indent=2))


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch OHLCV data from Twelve Data (US Equities)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch last 100 hourly candles
  python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 100
  
  # Fetch daily candles for date range
  python pull_us-eq.py --symbol MSFT --timeframe 1d --start 2024-01-01 --end 2024-01-31
  
  # Stream real-time prices
  python pull_us-eq.py --symbol AAPL --stream
  
  # Historical + Real-time (backfill then stream)
  python pull_us-eq.py --symbol AAPL --timeframe 1h --limit 10 --stream
  
  # Poll REST API every 60 seconds (1 call per minute, free tier compliant)
  python pull_us-eq.py --symbol AAPL --timeframe 1m --limit 1 --poll
        """,
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Stock symbol (e.g., AAPL, MSFT, TSLA, GOOGL)",
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
        help="Number of candles to fetch (max depends on plan). Required if --start/--end not provided.",
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
        help="Enable real-time WebSocket streaming. Note: WebSocket provides real-time prices, "
             "not OHLCV candles. If --limit or --start/--end are provided, historical data will "
             "be fetched first, then streaming will begin.",
    )
    
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Poll REST API every 60 seconds to get latest data (1 API call per minute). "
             "Requires --timeframe and --limit (typically 1 for latest candle). "
             "Respects free tier rate limits.",
    )
    
    parser.add_argument(
        "--timezone",
        type=str,
        help="Timezone for timestamps. Options: 'UTC', 'America/New_York' (default for US stocks), or IANA timezone (e.g., 'America/Los_Angeles', 'Asia/Singapore')",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.stream and not args.poll:
        # For non-streaming/polling mode, require historical data parameters
        if not args.timeframe:
            parser.error("--timeframe is required when not using --stream or --poll")
        if not args.limit and not (args.start and args.end):
            parser.error("Either --limit or both --start and --end must be provided (or use --stream/--poll for real-time)")
    
    if args.poll:
        if not args.timeframe:
            parser.error("--timeframe is required when using --poll")
        if not args.limit:
            parser.error("--limit is required when using --poll (typically use --limit 1 for latest candle)")
    
    if args.start and not args.end:
        parser.error("--end is required when --start is provided")
    
    if args.end and not args.start:
        parser.error("--start is required when --end is provided")
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    
    if args.start and args.end:
        try:
            # Try parsing with time
            try:
                start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                start_dt = datetime.strptime(args.start, "%Y-%m-%d")
            
            try:
                end_dt = datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_dt = datetime.strptime(args.end, "%Y-%m-%d")
                # Set to end of day
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        except ValueError as e:
            print(f"✗ Invalid date format: {e}")
            print("  Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    # Handle polling mode (REST API polling every 60 seconds)
    if args.poll:
        client = authenticate()
        
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
                    client=client,
                    symbol=args.symbol,
                    timeframe=args.timeframe,
                    limit=args.limit,
                    start=None,
                    end=None,
                    timezone=args.timezone,
                )
                
                # Output latest data
                format_output(ohlcv_data, format_type=args.format)
                
                # Wait 60 seconds before next poll (rate limit: 1 call per minute)
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
        # If historical data requested, fetch it first
        if args.limit or (args.start and args.end):
            if not args.timeframe:
                print("✗ --timeframe is required when fetching historical data")
                sys.exit(1)
            
            print("=" * 80)
            print("FETCHING HISTORICAL DATA")
            print("=" * 80)
            
            client = authenticate()
            ohlcv_data = fetch_ohlcv(
                client=client,
                symbol=args.symbol,
                timeframe=args.timeframe,
                limit=args.limit,
                start=start_dt,
                end=end_dt,
                timezone=args.timezone,
            )
            
            # Output historical data
            format_output(ohlcv_data, format_type=args.format)
            
            print("\n" + "=" * 80)
            print("STARTING REAL-TIME STREAMING")
            print("=" * 80 + "\n")
        
        # Define callback for real-time prices
        def on_new_price(price_data: Dict[str, Any]):
            """Handle new price from WebSocket."""
            timestamp_str = price_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            price_str = f"${price_data['price']:.2f}"
            if price_data.get("bid") and price_data.get("ask"):
                price_str += f" (Bid: ${price_data['bid']:.2f}, Ask: ${price_data['ask']:.2f})"
            if price_data.get("day_volume"):
                price_str += f" Volume: {price_data['day_volume']:,}"
            print(f"[{timestamp_str}] {price_data['symbol']}: {price_str}")
        
        def on_error_handler(error: Exception):
            """Handle streaming errors."""
            print(f"✗ Streaming error: {error}")
        
        # Start streaming
        stream_realtime_prices(
            symbol=args.symbol,
            on_price=on_new_price,
            on_error=on_error_handler,
        )
    
    else:
        # Historical data only (original functionality)
        if not args.timeframe:
            parser.error("--timeframe is required for historical data")
        
        client = authenticate()
        
        ohlcv_data = fetch_ohlcv(
            client=client,
            symbol=args.symbol,
            timeframe=args.timeframe,
            limit=args.limit,
            start=start_dt,
            end=end_dt,
            timezone=args.timezone,
        )
        
        format_output(ohlcv_data, format_type=args.format)


if __name__ == "__main__":
    main()
