"""Minimal candlecraft quickstart — fetch latest BTC hourly candles."""

from candlecraft import fetch_ohlcv

candles = fetch_ohlcv("BTCUSDT", "1h", limit=5)

for candle in candles:
    print(f"{candle.timestamp:%Y-%m-%d %H:%M}  close={candle.close:.2f}  vol={candle.volume}")
