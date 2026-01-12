#!/usr/bin/env python3
import os, sys, json, time, signal, argparse, threading
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple

# Optional deps
try:
    from dotenv import load_dotenv; load_dotenv()
except: pass

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except: Client = None

try:
    from twelvedata import TDClient
except: TDClient = None

try:
    import websocket
except: websocket = None


# =========================
# CONSTANTS
# =========================
BINANCE_LIMIT = 1000
TD_RATE_LIMIT = 60

BINANCE_INTERVALS = {}
if Client:
    BINANCE_INTERVALS = {
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

TD_INTERVALS = {
    "1m": "1min", "5m": "5min", "15m": "15min",
    "30m": "30min", "1h": "1h", "4h": "4h",
    "1d": "1day", "1w": "1week", "1M": "1month",
}


# =========================
# TYPES
# =========================
class Asset(Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    EQUITY = "equity"


# =========================
# UTILITIES
# =========================
_last_td_call = 0
def td_rate_limit():
    global _last_td_call
    dt = time.time() - _last_td_call
    if dt < TD_RATE_LIMIT:
        time.sleep(TD_RATE_LIMIT - dt)
    _last_td_call = time.time()


def die(msg: str):
    print(f"✗ {msg}")
    sys.exit(1)


def detect_asset(symbol: str) -> Asset:
    s = symbol.upper()
    if "/" in s or "_" in s:
        return Asset.FOREX
    if any(x in s for x in ("USDT","BTC","ETH","BNB","SOL","ADA","XRP")):
        return Asset.CRYPTO
    return Asset.EQUITY


def normalize(symbol: str, asset: Asset) -> str:
    return symbol.replace("_","/").upper() if asset == Asset.FOREX else symbol.upper()


def parse_dates(a: Optional[str], b: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    if not a or not b: return None, None
    try:
        s = datetime.fromisoformat(a)
        e = datetime.fromisoformat(b)
        return s, e
    except:
        die("Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")


# =========================
# AUTH
# =========================
def binance_client() -> Client:
    if not Client: die("python-binance not installed")
    return Client(
        os.getenv("BINANCE_API_KEY"),
        os.getenv("BINANCE_API_SECRET"),
        testnet=os.getenv("BINANCE_TESTNET","false").lower()=="true"
    )


def td_client() -> TDClient:
    if not TDClient: die("twelvedata not installed")
    key = os.getenv("TWELVEDATA_SECRET")
    if not key: die("TWELVEDATA_SECRET not set")
    return TDClient(apikey=key)


# =========================
# FETCHERS
# =========================
def fetch_binance(symbol, tf, limit, start, end):
    c = binance_client()
    if tf not in BINANCE_INTERVALS: die("Unsupported timeframe")
    symbol = symbol.upper()
    interval = BINANCE_INTERVALS[tf]

    if limit:
        limit = min(limit, BINANCE_LIMIT)
        klines = c.get_klines(symbol=symbol, interval=interval, limit=limit)
    elif start and end:
        s, e = int(start.timestamp()*1000), int(end.timestamp()*1000)
        klines, cur = [], s
        while cur < e:
            batch = c.get_klines(symbol=symbol, interval=interval, startTime=cur, endTime=e, limit=BINANCE_LIMIT)
            if not batch: break
            klines += batch
            cur = batch[-1][0] + 1
    else:
        die("Either --limit or both --start and --end must be provided")

    return [{
        "timestamp": datetime.fromtimestamp(k[0]/1000),
        "open": float(k[1]), "high": float(k[2]),
        "low": float(k[3]), "close": float(k[4]),
        "volume": float(k[5])
    } for k in klines]


def fetch_td(symbol, tf, asset, limit, start, end, tz):
    if tf not in TD_INTERVALS: die("Unsupported timeframe")
    td_rate_limit()
    c = td_client()

    params = dict(
        symbol=normalize(symbol, asset),
        interval=TD_INTERVALS[tf],
        timezone=tz or ("America/New_York" if asset==Asset.EQUITY else "Exchange")
    )

    if limit:
        params["outputsize"] = limit
    elif start and end:
        params["start_date"] = start.strftime("%Y-%m-%d")
        params["end_date"] = end.strftime("%Y-%m-%d")
    else:
        die("Either --limit or both --start and --end must be provided")

    df = c.time_series(**params).as_pandas()
    if df.empty: die("No data returned")

    out = []
    for t,r in df.iterrows():
        out.append({
            "timestamp": t.to_pydatetime() if hasattr(t,"to_pydatetime") else t,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["volume"]) if "volume" in r else None,
        })
    return out


def fetch(symbol, tf, asset, limit, start, end, tz):
    return (
        fetch_binance(symbol, tf, limit, start, end)
        if asset == Asset.CRYPTO
        else fetch_td(symbol, tf, asset, limit, start, end, tz)
    )


# =========================
# OUTPUT
# =========================
FMT = {
    Asset.CRYPTO: (8, ""),
    Asset.FOREX: (5, ""),
    Asset.EQUITY: (2, "$"),
}

def print_table(data, asset):
    dec, sym = FMT[asset]
    print("="*100)
    for c in data:
        ts = c["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"{ts:<20} "
            f"{sym}{c['open']:.{dec}f} "
            f"{sym}{c['high']:.{dec}f} "
            f"{sym}{c['low']:.{dec}f} "
            f"{sym}{c['close']:.{dec}f} "
            f"{c['volume'] or ''}"
        )
    print("="*100)


def output(data, fmt, asset):
    if fmt == "json":
        print(json.dumps([
            {**c,"timestamp":c["timestamp"].isoformat()} for c in data
        ], indent=2))
    elif fmt == "csv":
        print("timestamp,open,high,low,close,volume")
        for c in data:
            print(",".join(str(x) for x in (
                c["timestamp"], c["open"], c["high"],
                c["low"], c["close"], c.get("volume","")
            )))
    else:
        print_table(data, asset)


# =========================
# STREAMING
# =========================
def stream_binance(symbol, tf, on_candle=None):
    if not websocket: die("websocket-client not installed")
    if tf not in BINANCE_INTERVALS: die("Unsupported timeframe")
    
    symbol_lower = symbol.lower()
    interval_map = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d","1w":"1w","1M":"1M"}
    ws_url = f"wss://stream.binance.com:9443/ws/{symbol_lower}@kline_{interval_map[tf]}"
    
    def on_message(ws, msg):
        try:
            d = json.loads(msg)
            if isinstance(d, str) and d == "ping":
                ws.send("pong")
                return
            if "k" in d and d["k"].get("x"):
                k = d["k"]
                candle = {
                    "timestamp": datetime.fromtimestamp(k["t"]/1000),
                    "open": float(k["o"]), "high": float(k["h"]),
                    "low": float(k["l"]), "close": float(k["c"]),
                    "volume": float(k["v"])
                }
                if on_candle: on_candle(candle)
                else:
                    ts = candle["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{ts}] {symbol.upper()} {tf}: O={candle['open']:.8f} H={candle['high']:.8f} L={candle['low']:.8f} C={candle['close']:.8f} V={candle['volume']:.8f}")
        except: pass
    
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    signal.signal(signal.SIGINT, lambda s,f: (ws.close(), sys.exit(0)))
    ws.run_forever()


# =========================
# MAIN
# =========================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe")
    p.add_argument("--limit", type=int)
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--format", default="table", choices=["table","csv","json"])
    p.add_argument("--stream", action="store_true")
    p.add_argument("--poll", action="store_true")
    p.add_argument("--timezone")
    a = p.parse_args()

    asset = detect_asset(a.symbol)
    s,e = parse_dates(a.start, a.end)

    if a.stream:
        if asset == Asset.CRYPTO:
            if not a.timeframe: die("--timeframe required for crypto streaming")
            stream_binance(a.symbol, a.timeframe)
        else:
            die("Streaming not implemented for Forex/Equity (use --poll instead)")
    elif a.poll:
        if asset == Asset.CRYPTO: die("--poll not supported for crypto (use --stream)")
        if not a.timeframe or not a.limit: die("--timeframe and --limit required for --poll")
        signal.signal(signal.SIGINT, lambda s,f: sys.exit(0))
        i = 0
        while True:
            i += 1
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Poll #{i}")
            data = fetch(a.symbol, a.timeframe, asset, a.limit, None, None, a.timezone)
            output(data, a.format, asset)
            print("\n⏳ Waiting 60 seconds...")
            time.sleep(60)
    else:
        if not a.timeframe: die("--timeframe required")
        if not a.limit and not (s and e): die("--limit or --start/--end required")
        data = fetch(a.symbol, a.timeframe, asset, a.limit, s, e, a.timezone)
        output(data, a.format, asset)


if __name__ == "__main__":
    main()
