# Technical Indicators Guide

A comprehensive guide to using technical indicators with the Data Puller All-in-One system.

**Repository:** https://github.com/alfredalpino/Data-Puller-AiO

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Available Indicators](#available-indicators)
  - [1. MACD (Moving Average Convergence Divergence)](#1-macd-moving-average-convergence-divergence)
  - [2. RSI (Relative Strength Index)](#2-rsi-relative-strength-index)
  - [3. SMA (Simple Moving Average)](#3-sma-simple-moving-average)
  - [4. EMA (Exponential Moving Average)](#4-ema-exponential-moving-average)
  - [5. VWAP (Volume Weighted Average Price)](#5-vwap-volume-weighted-average-price)
  - [6. Bollinger Bands](#6-bollinger-bands)
  - [7. ATR (Average True Range)](#7-atr-average-true-range)
  - [8. Stochastic Oscillator](#8-stochastic-oscillator)
  - [9. ADX (Average Directional Index)](#9-adx-average-directional-index)
  - [10. OBV (On-Balance Volume)](#10-obv-on-balance-volume)
- [Output Formats](#output-formats)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Data Puller All-in-One system supports **10 technical indicators** that can be dynamically loaded and calculated on OHLCV data. All indicators are:

- ✅ **Pure functions** - No API calls, no side effects
- ✅ **Timestamp-aligned** - Values match input data timestamps
- ✅ **Non-destructive** - Original OHLCV data is never modified
- ✅ **Dynamically loaded** - No hardcoded imports, plug-in style architecture

### How It Works

1. Fetch OHLCV data using `pull_ohlcv.py`
2. Specify an indicator with `--indicator <name>`
3. The system dynamically loads the indicator module from `indicators/`
4. Indicator values are calculated and appended to the output
5. Results are displayed in your chosen format (table, CSV, or JSON)

---

## Quick Start

### Basic Usage

```bash
# Use an indicator with cryptocurrency data
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi

# Use an indicator with forex data
python pull_ohlcv.py --symbol EUR/USD --timeframe 1h --limit 100 --indicator macd

# Use an indicator with equity data
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 50 --indicator bollinger
```

### Output Formats

Indicators work with all output formats:

```bash
# Table format (default)
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi

# CSV format
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi --format csv

# JSON format
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi --format json
```

---

## Available Indicators

### 1. MACD (Moving Average Convergence Divergence)

**Purpose:** Trend-following momentum indicator that shows the relationship between two moving averages.

**Use Cases:**
- Identify trend changes
- Generate buy/sell signals (when MACD crosses signal line)
- Detect momentum shifts

**Formula:**
- MACD Line = Fast EMA (12) - Slow EMA (26)
- Signal Line = EMA of MACD Line (9 periods)
- Histogram = MACD Line - Signal Line

**Parameters:**
- `fast_period` (default: 12)
- `slow_period` (default: 26)
- `signal_period` (default: 9)

**Output Fields:**
- `macd` - MACD line value
- `signal` - Signal line value
- `histogram` - Histogram value (MACD - Signal)

**Example Commands:**

```bash
# Basic MACD with default parameters
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator macd

# MACD with custom parameters (requires code modification)
# Note: Parameter customization requires modifying the indicator module
```

**Interpretation:**
- **Bullish Signal:** MACD crosses above signal line
- **Bearish Signal:** MACD crosses below signal line
- **Histogram > 0:** Bullish momentum
- **Histogram < 0:** Bearish momentum

**Minimum Data Required:** 35 candles (26 + 9 - 1)

---

### 2. RSI (Relative Strength Index)

**Purpose:** Momentum oscillator that measures the speed and magnitude of price changes. Identifies overbought (>70) and oversold (<30) conditions.

**Use Cases:**
- Identify overbought/oversold conditions
- Spot potential reversal points
- Confirm trend strength

**Formula (Wilder's Smoothing):**
- RS = Average Gain / Average Loss
- RSI = 100 - (100 / (1 + RS))

**Parameters:**
- `period` (default: 14)

**Output Fields:**
- `rsi` - RSI value (0-100)

**Example Commands:**

```bash
# RSI with default 14-period
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi

# RSI for forex pair
python pull_ohlcv.py --symbol EUR/USD --timeframe 4h --limit 200 --indicator rsi

# RSI for equity
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 50 --indicator rsi
```

**Interpretation:**
- **RSI > 70:** Overbought (potential sell signal)
- **RSI < 30:** Oversold (potential buy signal)
- **RSI = 50:** Neutral
- **RSI Divergence:** Price makes new high/low but RSI doesn't (potential reversal)

**Minimum Data Required:** 15 candles (14 + 1)

---

### 3. SMA (Simple Moving Average)

**Purpose:** Baseline trend indicator that smooths price data by creating a constantly updated average price.

**Use Cases:**
- Identify trend direction
- Support/resistance levels
- Compare with price for entry/exit signals

**Formula:**
- SMA = Sum of Closing Prices / Number of Periods

**Parameters:**
- `period` (default: 20)

**Output Fields:**
- `sma` - Simple Moving Average value

**Example Commands:**

```bash
# 20-period SMA (default)
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator sma

# SMA for different timeframes
python pull_ohlcv.py --symbol ETHUSDT --timeframe 4h --limit 200 --indicator sma
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 50 --indicator sma
```

**Interpretation:**
- **Price > SMA:** Uptrend
- **Price < SMA:** Downtrend
- **Price crosses SMA:** Potential trend change
- **Longer periods:** Smoother, less sensitive
- **Shorter periods:** More sensitive, more signals

**Minimum Data Required:** Period value (default: 20)

---

### 4. EMA (Exponential Moving Average)

**Purpose:** Faster-reacting moving average that gives more weight to recent prices. More responsive than SMA.

**Use Cases:**
- Quick trend identification
- Entry/exit signals
- Often used in pairs (fast and slow EMA)

**Formula:**
- EMA = Price × k + Previous EMA × (1 - k)
- k = 2 / (Period + 1)

**Parameters:**
- `period` (default: 20)

**Output Fields:**
- `ema` - Exponential Moving Average value

**Example Commands:**

```bash
# 20-period EMA (default)
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator ema

# EMA for intraday trading
python pull_ohlcv.py --symbol EUR/USD --timeframe 15m --limit 200 --indicator ema
```

**Interpretation:**
- **Price > EMA:** Bullish trend
- **Price < EMA:** Bearish trend
- **Faster than SMA:** Reacts quicker to price changes
- **Common pairs:** 12/26 EMA (like MACD), 50/200 EMA

**Minimum Data Required:** Period value (default: 20)

---

### 5. VWAP (Volume Weighted Average Price)

**Purpose:** Institutional benchmark that gives the average price a security has traded at throughout the day, based on both volume and price.

**Use Cases:**
- Institutional trading benchmark
- Intraday support/resistance
- Fair value assessment

**Formula:**
- VWAP = Cumulative (Price × Volume) / Cumulative Volume
- Price = (High + Low + Close) / 3 (Typical Price)

**Parameters:**
- None (uses all available data from start)

**Output Fields:**
- `vwap` - Volume Weighted Average Price

**Example Commands:**

```bash
# VWAP calculation
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator vwap

# VWAP for equity (requires volume data)
python pull_ohlcv.py --symbol AAPL --timeframe 5m --limit 500 --indicator vwap
```

**Interpretation:**
- **Price > VWAP:** Bullish (trading above average)
- **Price < VWAP:** Bearish (trading below average)
- **VWAP as Support/Resistance:** Price often bounces off VWAP
- **Institutional Benchmark:** Many traders use VWAP as fair value

**Note:** Requires volume data. Returns `None` if volume is missing.

**Minimum Data Required:** 1 candle (with volume)

---

### 6. Bollinger Bands

**Purpose:** Volatility indicator that consists of a middle band (SMA) and two outer bands (standard deviations). Identifies overbought/oversold conditions and volatility.

**Use Cases:**
- Volatility measurement
- Mean reversion trading
- Breakout identification

**Formula:**
- Middle Band = SMA(period)
- Upper Band = SMA + (Standard Deviation × Multiplier)
- Lower Band = SMA - (Standard Deviation × Multiplier)

**Parameters:**
- `period` (default: 20)
- `std_mult` (default: 2.0)

**Output Fields:**
- `bb_upper` - Upper Bollinger Band
- `bb_middle` - Middle Band (SMA)
- `bb_lower` - Lower Bollinger Band

**Example Commands:**

```bash
# Bollinger Bands with default parameters
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator bollinger

# Bollinger Bands for different assets
python pull_ohlcv.py --symbol EUR/USD --timeframe 4h --limit 200 --indicator bollinger
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 50 --indicator bollinger
```

**Interpretation:**
- **Price touches Upper Band:** Potentially overbought
- **Price touches Lower Band:** Potentially oversold
- **Bands widen:** Increased volatility
- **Bands narrow:** Decreased volatility (squeeze - potential breakout)
- **Price bounces between bands:** Range-bound market

**Minimum Data Required:** Period value (default: 20)

---

### 7. ATR (Average True Range)

**Purpose:** Volatility indicator that measures market volatility by decomposing the entire range of an asset price for that period.

**Use Cases:**
- Risk management and position sizing
- Volatility measurement
- Stop-loss placement
- Market condition assessment

**Formula:**
- True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
- ATR = EMA of True Range

**Parameters:**
- `period` (default: 14)

**Output Fields:**
- `atr` - Average True Range value

**Example Commands:**

```bash
# ATR with default 14-period
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator atr

# ATR for risk assessment
python pull_ohlcv.py --symbol ETHUSDT --timeframe 4h --limit 200 --indicator atr
```

**Interpretation:**
- **High ATR:** High volatility (wider price swings)
- **Low ATR:** Low volatility (tighter price swings)
- **Stop Loss:** Often placed at 2× ATR from entry
- **Position Sizing:** Use ATR to adjust position size based on volatility

**Minimum Data Required:** 15 candles (14 + 1)

---

### 8. Stochastic Oscillator

**Purpose:** Momentum indicator that compares a security's closing price to its price range over a given time period. Identifies momentum turning points.

**Use Cases:**
- Identify overbought/oversold conditions
- Spot momentum turning points
- Generate entry/exit signals

**Formula:**
- %K = ((Close - Lowest Low) / (Highest High - Lowest Low)) × 100
- %D = SMA of %K

**Parameters:**
- `k_period` (default: 14)
- `d_period` (default: 3)

**Output Fields:**
- `stoch_k` - %K value (0-100)
- `stoch_d` - %D value (0-100)

**Example Commands:**

```bash
# Stochastic with default parameters
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator stochastic

# Stochastic for different timeframes
python pull_ohlcv.py --symbol EUR/USD --timeframe 4h --limit 200 --indicator stochastic
```

**Interpretation:**
- **%K > 80:** Overbought (potential sell)
- **%K < 20:** Oversold (potential buy)
- **%K crosses above %D:** Bullish signal
- **%K crosses below %D:** Bearish signal
- **Divergence:** Price makes new high/low but Stochastic doesn't

**Minimum Data Required:** 16 candles (14 + 3 - 1)

---

### 9. ADX (Average Directional Index)

**Purpose:** Trend strength indicator (not direction). Measures the strength of a trend regardless of whether it's up or down.

**Use Cases:**
- Measure trend strength
- Filter trades (only trade when ADX > 25)
- Confirm trend continuation

**Formula:**
- Uses +DM, -DM, True Range
- DI+ = (+DM / TR) × 100
- DI- = (-DM / TR) × 100
- DX = |DI+ - DI-| / (DI+ + DI-) × 100
- ADX = EMA of DX

**Parameters:**
- `period` (default: 14)

**Output Fields:**
- `adx` - Average Directional Index (0-100)
- `di_plus` - Positive Directional Indicator
- `di_minus` - Negative Directional Indicator

**Example Commands:**

```bash
# ADX with default 14-period
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator adx

# ADX for trend analysis
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 50 --indicator adx
```

**Interpretation:**
- **ADX < 20:** Weak trend (ranging market)
- **ADX 20-25:** Developing trend
- **ADX > 25:** Strong trend
- **ADX > 50:** Very strong trend
- **DI+ > DI-:** Bullish trend
- **DI- > DI+:** Bearish trend

**Minimum Data Required:** 28 candles (14 × 2)

---

### 10. OBV (On-Balance Volume)

**Purpose:** Volume-based indicator that uses volume flow to predict changes in stock price. Confirms price movements.

**Use Cases:**
- Confirm price trends
- Identify accumulation/distribution
- Spot divergences

**Formula:**
- If Close > Previous Close: OBV = Previous OBV + Volume
- If Close < Previous Close: OBV = Previous OBV - Volume
- If Close = Previous Close: OBV = Previous OBV (unchanged)

**Parameters:**
- None

**Output Fields:**
- `obv` - On-Balance Volume value

**Example Commands:**

```bash
# OBV calculation
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator obv

# OBV for equity analysis
python pull_ohlcv.py --symbol AAPL --timeframe 1d --limit 200 --indicator obv
```

**Interpretation:**
- **OBV rising with price:** Confirms uptrend
- **OBV falling with price:** Confirms downtrend
- **OBV divergence:** Price rises but OBV falls (weak trend, potential reversal)
- **OBV trend:** More important than absolute value

**Note:** Requires volume data. Returns `None` if volume is missing.

**Minimum Data Required:** 1 candle (with volume)

---

## Output Formats

### Table Format (Default)

Indicators are displayed as additional columns in the table:

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --indicator rsi
```

**Example Output:**
```
====================================================================================================
Timestamp            Open         High          Low          Close            Volume            Rsi
====================================================================================================
2024-01-01 10:00:00  42000.00     42500.00     41800.00     42200.00     1500.50000000     65.50
2024-01-01 11:00:00  42200.00     42800.00     42100.00     42600.00     1800.25000000     68.20
...
```

### CSV Format

Indicator values are added as additional columns:

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --indicator rsi --format csv
```

**Example Output:**
```csv
timestamp,open,high,low,close,volume,symbol,timeframe,asset_class,source,rsi
2024-01-01T10:00:00+00:00,42000.0,42500.0,41800.0,42200.0,1500.5,BTCUSDT,1h,crypto,binance,65.50
...
```

### JSON Format

Indicator values are included in each data point:

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 10 --indicator rsi --format json
```

**Example Output:**
```json
[
  {
    "timestamp": "2024-01-01T10:00:00+00:00",
    "open": 42000.0,
    "high": 42500.0,
    "low": 41800.0,
    "close": 42200.0,
    "volume": 1500.5,
    "rsi": 65.50
  },
  ...
]
```

---

## Best Practices

### 1. Data Requirements

- **Minimum Data:** Ensure you have enough candles for the indicator calculation
- **Volume Indicators:** VWAP and OBV require volume data
- **Timeframe Selection:** Longer timeframes (1d, 1w) provide more reliable signals

### 2. Indicator Selection

- **Trend Following:** MACD, SMA, EMA, ADX
- **Momentum:** RSI, Stochastic
- **Volatility:** Bollinger Bands, ATR
- **Volume:** VWAP, OBV

### 3. Combining Indicators

While the system doesn't support indicator chaining yet, you can:

1. Run multiple commands with different indicators
2. Export to CSV and combine in spreadsheet/external tool
3. Use JSON output for programmatic analysis

### 4. Timeframe Considerations

- **Intraday (1m, 5m, 15m):** More signals, more noise
- **Hourly (1h, 4h):** Balanced signals
- **Daily (1d):** Stronger, more reliable signals
- **Weekly (1w):** Long-term trends

### 5. Asset Class Considerations

- **Cryptocurrency:** High volatility, 24/7 trading
- **Forex:** Lower volatility, session-based
- **Equities:** Market hours, earnings events affect indicators

---

## Troubleshooting

### Indicator Returns All None Values

**Problem:** Indicator values are all `None` in the output.

**Solutions:**
1. **Insufficient Data:** Check minimum data requirements for the indicator
2. **Missing Volume:** VWAP and OBV require volume data
3. **Timeframe Too Short:** Some indicators need more historical data

**Example:**
```bash
# MACD needs at least 35 candles
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 50 --indicator macd
```

### Indicator Module Not Found

**Problem:** Error message: "Indicator module not found"

**Solutions:**
1. Check that the indicator file exists in `indicators/` directory
2. Verify the indicator name matches the filename (without `.py`)
3. Ensure proper file permissions

### Import Errors

**Problem:** Error loading indicator module

**Solutions:**
1. Verify `pull_ohlcv.py` is in the parent directory
2. Check Python path and imports
3. Ensure all dependencies are installed

### Volume Data Missing

**Problem:** VWAP or OBV returns `None` values

**Solutions:**
1. Verify the data source provides volume data
2. Check if the symbol/timeframe combination supports volume
3. Some forex pairs may not have volume data

---

## Summary

The Data Puller All-in-One system provides **10 professional-grade technical indicators** that can be easily integrated into your trading analysis workflow. All indicators:

- ✅ Work with all asset classes (Crypto, Forex, Equities)
- ✅ Support all timeframes
- ✅ Integrate seamlessly with existing data fetching
- ✅ Output in multiple formats (table, CSV, JSON)
- ✅ Follow industry-standard formulas
- ✅ Are production-ready and well-tested

For more information about the main system, see [README.md](README.md).

---

**Last Updated:** 2024
**Version:** 1.0.1
