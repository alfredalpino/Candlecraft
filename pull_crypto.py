#!/usr/bin/env python3
"""
Standalone Crypto OHLCV Data Puller

A simple script to fetch OHLCV (Open, High, Low, Close, Volume) data from Binance.
This script focuses solely on authentication, data retrieval, and clean output.

Usage:
    python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100
    python pull_crypto.py --symbol ETHUSDT --timeframe 1d --start 2024-01-01 --end 2024-01-31
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Optional, Dict, Any

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    print("Error: python-binance library not installed.")
    print("Install it with: pip install python-binance")
    sys.exit(1)


def authenticate() -> Client:
    """
    Authenticate with Binance API using environment variables.
    
    Returns:
        Authenticated Binance Client instance
    
    Raises:
        SystemExit: If authentication fails or API keys are missing
    """
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    # Binance allows public data access without API key, but API key is recommended
    if api_key and api_secret:
        try:
            client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
            print(f"✓ Authenticated with Binance API (testnet: {testnet})")
            return client
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            sys.exit(1)
    else:
        # Use public client (no API key required, but rate limits are lower)
        try:
            client = Client(testnet=testnet)
            print("✓ Using Binance public API (no authentication required)")
            print("  Note: For higher rate limits, set BINANCE_API_KEY and BINANCE_API_SECRET")
            return client
        except Exception as e:
            print(f"✗ Failed to initialize Binance client: {e}")
            sys.exit(1)


def fetch_ohlcv(
    client: Client,
    symbol: str,
    timeframe: str,
    limit: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV data from Binance.
    
    Args:
        client: Authenticated Binance client
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        timeframe: Kline interval (e.g., '1m', '5m', '1h', '1d')
        limit: Number of candles to fetch (max 1000)
        start: Start datetime (optional, used with end)
        end: End datetime (optional, used with start)
    
    Returns:
        List of OHLCV dictionaries with keys: timestamp, open, high, low, close, volume
    
    Raises:
        SystemExit: If data fetching fails
    """
    # Map timeframe to Binance interval
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
        # Test connection
        client.ping()
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        sys.exit(1)
    
    try:
        if limit:
            # Fetch by limit
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
            # Fetch by date range
            start_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000)
            
            print(f"Fetching {symbol_upper} ({timeframe}) from {start} to {end}...")
            
            # Binance limits to 1000 klines per request, so we paginate if needed
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
                
                # Move to next batch
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
        
        # Format data
        ohlcv_data = []
        for kline in klines:
            ohlcv_data.append({
                "timestamp": datetime.fromtimestamp(kline[0] / 1000),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
            })
        
        print(f"✓ Successfully fetched {len(ohlcv_data)} candles")
        return ohlcv_data
    
    except BinanceAPIException as e:
        print(f"✗ Binance API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        sys.exit(1)


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
            print(
                f"{timestamp_str:<20} "
                f"{candle['open']:>12.8f} "
                f"{candle['high']:>12.8f} "
                f"{candle['low']:>12.8f} "
                f"{candle['close']:>12.8f} "
                f"{candle['volume']:>20.8f}"
            )
        
        print("=" * 100)
    
    elif format_type == "csv":
        # CSV format
        print("timestamp,open,high,low,close,volume")
        for candle in ohlcv_data:
            timestamp_str = candle["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{timestamp_str},"
                f"{candle['open']},"
                f"{candle['high']},"
                f"{candle['low']},"
                f"{candle['close']},"
                f"{candle['volume']}"
            )
    
    elif format_type == "json":
        # JSON format
        import json
        output = []
        for candle in ohlcv_data:
            output.append({
                "timestamp": candle["timestamp"].isoformat(),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"],
            })
        print(json.dumps(output, indent=2))


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch OHLCV data from Binance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch last 100 hourly candles
  python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 100
  
  # Fetch daily candles for date range
  python pull_crypto.py --symbol ETHUSDT --timeframe 1d --start 2024-01-01 --end 2024-01-31
  
  # Output as CSV
  python pull_crypto.py --symbol BTCUSDT --timeframe 1h --limit 10 --format csv
        """,
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Trading pair symbol (e.g., BTCUSDT, ETHUSDT)",
    )
    
    parser.add_argument(
        "--timeframe",
        type=str,
        required=True,
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"],
        help="Timeframe interval",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of candles to fetch (max 1000). Required if --start/--end not provided.",
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
        help="Output format (default: table)",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.limit and not (args.start and args.end):
        parser.error("Either --limit or both --start and --end must be provided")
    
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
    
    # Authenticate
    client = authenticate()
    
    # Fetch data
    ohlcv_data = fetch_ohlcv(
        client=client,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        start=start_dt,
        end=end_dt,
    )
    
    # Output data
    format_output(ohlcv_data, format_type=args.format)


if __name__ == "__main__":
    main()
