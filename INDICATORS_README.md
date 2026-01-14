# Technical Indicators Reference

Reference documentation for technical indicators available in Candlecraft.

**Repository:** <https://github.com/alfredalpino/Candlecraft>

## Overview

Indicators are dynamically loaded from `indicators/` and calculated on OHLCV data fetched via `pull_ohlcv.py`. All indicators follow a consistent contract:

- **Pure functions** - No side effects, no API calls
- **Timestamp-aligned** - Output values match input data timestamps
- **Non-destructive** - Original OHLCV data is never modified

## Usage

```bash
python pull_ohlcv.py --symbol <SYMBOL> --timeframe <TF> --limit <N> --indicator <NAME>
```

Indicators work with all asset classes (Crypto, Forex, Equities) and output formats (table, CSV, JSON).

## Indicator Contract

Each indicator module in `indicators/` must export a `calculate` function:

```python
def calculate(ohlcv_data: List[OHLCV], **params) -> List[Dict[str, Any]]:
    """
    Returns list of dictionaries with indicator values.
    Values are None for periods before sufficient data is available.
    """
```

## Supported Indicators

| Indicator | Output Fields | Min Data | Default Period |
| --------- | ------------- | -------- | -------------- |
| MACD | `macd`, `signal`, `histogram` | 35 | 12/26/9 |
| RSI | `rsi` | 15 | 14 |
| SMA | `sma` | 20 | 20 |
| EMA | `ema` | 20 | 20 |
| VWAP | `vwap` | 1 (with volume) | N/A |
| Bollinger Bands | `bb_upper`, `bb_middle`, `bb_lower` | 20 | 20 |
| ATR | `atr` | 15 | 14 |
| Stochastic | `stoch_k`, `stoch_d` | 16 | 14/3 |
| ADX | `adx`, `di_plus`, `di_minus` | 28 | 14 |
| OBV | `obv` | 1 (with volume) | N/A |

## Indicator Reference

### MACD (Moving Average Convergence Divergence)

**Formula:**

- MACD Line = EMA(12) - EMA(26)
- Signal Line = EMA(MACD Line, 9)
- Histogram = MACD Line - Signal Line

**Output Fields:** `macd`, `signal`, `histogram`

**Minimum Data:** 35 candles

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator macd
```

---

### RSI (Relative Strength Index)

**Formula:**

- RS = Average Gain / Average Loss (Wilder's smoothing)
- RSI = 100 - (100 / (1 + RS))

**Output Fields:** `rsi` (0-100)

**Minimum Data:** 15 candles

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator rsi
```

---

### SMA (Simple Moving Average)

**Formula:**

- SMA = Σ(Close) / Period

**Output Fields:** `sma`

**Minimum Data:** Period value (default: 20)

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator sma
```

---

### EMA (Exponential Moving Average)

**Formula:**

- EMA = Price × k + Previous EMA × (1 - k)
- k = 2 / (Period + 1)

**Output Fields:** `ema`

**Minimum Data:** Period value (default: 20)

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator ema
```

---

### VWAP (Volume Weighted Average Price)

**Formula:**

- VWAP = Σ(Price × Volume) / Σ(Volume)
- Price = (High + Low + Close) / 3

**Output Fields:** `vwap`

**Minimum Data:** 1 candle (requires volume)

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator vwap
```

**Note:** Returns `None` if volume data is missing.

---

### Bollinger Bands

**Formula:**

- Middle Band = SMA(period)
- Upper Band = SMA + (StdDev × multiplier)
- Lower Band = SMA - (StdDev × multiplier)
- Default multiplier: 2.0

**Output Fields:** `bb_upper`, `bb_middle`, `bb_lower`

**Minimum Data:** Period value (default: 20)

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator bollinger
```

---

### ATR (Average True Range)

**Formula:**

- True Range = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
- ATR = EMA(True Range)

**Output Fields:** `atr`

**Minimum Data:** 15 candles

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator atr
```

---

### Stochastic Oscillator

**Formula:**

- %K = ((Close - Lowest Low) / (Highest High - Lowest Low)) × 100
- %D = SMA(%K, 3)

**Output Fields:** `stoch_k`, `stoch_d` (0-100)

**Minimum Data:** 16 candles

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator stochastic
```

---

### ADX (Average Directional Index)

**Formula:**

- DI+ = (+DM / TR) × 100
- DI- = (-DM / TR) × 100
- DX = |DI+ - DI-| / (DI+ + DI-) × 100
- ADX = EMA(DX)

**Output Fields:** `adx`, `di_plus`, `di_minus`

**Minimum Data:** 28 candles

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator adx
```

---

### OBV (On-Balance Volume)

**Formula:**

- If Close > PrevClose: OBV = PrevOBV + Volume
- If Close < PrevClose: OBV = PrevOBV - Volume
- If Close = PrevClose: OBV = PrevOBV

**Output Fields:** `obv`

**Minimum Data:** 1 candle (requires volume)

**Usage:**

```bash
python pull_ohlcv.py --symbol BTCUSDT --timeframe 1h --limit 100 --indicator obv
```

**Note:** Returns `None` if volume data is missing.
