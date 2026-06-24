"""
Example: Candlecraft data + indicators for trading signal context.

Pairs with MarketMakingMegaMachine — use OHLCV/RSI to reason about spread width
before placing quotes (illustrative; does not place orders).
"""

from candlecraft import fetch_ohlcv, load_indicator

SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
LIMIT = 50

ohlcv = fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
rsi_calc = load_indicator("rsi")
rsi_values = rsi_calc(ohlcv)

latest_close = ohlcv[-1].close
latest_rsi = rsi_values[-1].get("rsi")

print(f"{SYMBOL} {TIMEFRAME} — close: {latest_close:.2f}, RSI: {latest_rsi}")

if latest_rsi is not None:
    if latest_rsi >= 70:
        print("Signal context: overbought — consider wider ask spread in MMMM")
    elif latest_rsi <= 30:
        print("Signal context: oversold — consider wider bid spread in MMMM")
    else:
        print("Signal context: neutral — standard spreads")
