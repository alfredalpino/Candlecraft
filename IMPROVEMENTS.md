# Candlecraft — Elite Portfolio Upgrade Plan

> **Goal:** Turn Candlecraft from "decent PyPI library" into a reference-quality financial data package — the kind of repo that makes a data engineer or fintech backend team say "this person ships real libraries."

**Current state:** Published on [PyPI v0.1.4](https://pypi.org/project/candlecraft/), unified OHLCV API across Binance + Twelve Data, indicator modules, ~1.2K lines of tests. Strong foundation, packaging gaps.

**Target state:** Pip-install works end-to-end (including indicators), CI runs without API keys, logging not print, clean repo, live docs badge.

---

## North Star (what "elite" looks like)

A stranger landing on your GitHub should see:

1. **PyPI badge** + install one-liner that actually works for all features
2. **Green CI badge** — unit tests pass on every push (no API keys)
3. **Clean README** — problem → solution → 3 examples → link to docs
4. **No contradictions** — not "production-ready" while classifiers say Alpha
5. **Portfolio link** — "Powers data layer for MMMM trading platform"

---

## P0 — Fix the pip-install break (~4 hours)

### 1. Indicators not in the package (critical bug)

**Problem:** `list_indicators()` and `load_indicator()` resolve paths relative to repo root:

```python
project_root = Path(__file__).parent.parent.parent
indicators_dir = project_root / "indicators"
```

After `pip install candlecraft`, `indicators/` does not exist. **Indicators are silently broken for all PyPI users.**

**Fix:**

1. Move `indicators/` → `candlecraft/indicators/`
2. Add `candlecraft/indicators/__init__.py`
3. Update `list_indicators()` / `load_indicator()` to use package resources:

```python
from importlib import resources

def list_indicators() -> list[str]:
    pkg = resources.files("candlecraft.indicators")
    return sorted(p.stem for p in pkg.iterdir() if p.suffix == ".py" and p.stem != "__init__")
```

4. Update `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
include = ["candlecraft*"]
```

5. Bump to **v0.2.0** (breaking path change for anyone using repo-relative indicators)

### 2. Replace `print()` with `logging` in library code

**Problem:** `candlecraft/providers.py` uses `print()` for auth success, fetch progress, warnings. Libraries must not pollute stdout.

**Fix:**

```python
import logging
logger = logging.getLogger(__name__)

# print("✓ Authenticated...")  →  logger.info("Authenticated with Binance (testnet=%s)", testnet)
```

- CLI (`pull_ohlcv.py`) can keep `print()` or use `rich` for tables
- Library layer: logging only, default level WARNING (silent unless configured)

### 3. Align "production-ready" claim with reality

**Pick one:**

| Option A (recommended) | Option B |
|---------------------|----------|
| README: "Stable beta — used in production at 3poch Labs" | Keep "production-ready" but change classifier to `Development Status :: 4 - Beta` |

Remove duplicate README sections (provider docs appear 3+ times). One canonical block.

---

## P0 — README slim-down (~2 hours)

**Current:** 500+ lines, repetitive provider examples, overwhelming for reviewers.

**Target structure (~150 lines):**

```markdown
# Candlecraft
[![PyPI](https://img.shields.io/pypi/v/candlecraft)](https://pypi.org/project/candlecraft/)
[![CI](https://github.com/alfredalpino/Candlecraft/actions/workflows/ci.yml/badge.svg)]
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]

Unified OHLCV fetching for crypto, forex, and equities.

## Install
pip install candlecraft

## 30-second example
(fetch_ohlcv code block)

## Features (bullet list, 5 items max)

## Providers
(table: Binance | Twelve Data | asset classes | keys required)

## Indicators
(one example after package fix)

## CLI
pip install candlecraft[cli]  # or document pull_ohlcv separately

## Docs
- [Full API reference](docs/api.md)
- [CLI guide](docs/cli.md)
- [Architecture](ARCHITECTURE.md)

## Related
Powers market data for [MarketMakingMegaMachine](https://github.com/alfredalpino/MarketMakingMegaMachine)

## License
```

Move long CLI docs, indicator tables, and rate-limit deep-dive to `docs/`.

---

## P1 — CI that actually runs tests (~1 day)

**Current:** `.github/workflows/publish.yml` only — tests never run on PR/push.

### Add `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --ignore=tests/test_ohlcv_pull.py  # unit only in CI
      - run: ruff check candlecraft/
```

### Split tests into two tiers

| Tier | File | Runs in CI | Needs API keys |
|------|------|------------|----------------|
| **Unit** | `tests/test_unit_*.py` | Yes | No |
| **Integration** | `tests/test_ohlcv_pull.py` | Manual / nightly | Yes |

### New unit tests (mocked)

| Test | Covers |
|------|--------|
| `test_detect_asset_class` | BTCUSDT → CRYPTO, EUR/USD → FOREX, AAPL → EQUITY |
| `test_validate_ohlcv` | Invalid candles rejected |
| `test_fetch_ohlcv_binance_mocked` | Mock `client.get_klines` → OHLCV list |
| `test_fetch_ohlcv_twelvedata_mocked` | Mock TDClient response |
| `test_rate_limit_raise` | RateLimitException raised with retry_after |
| `test_rate_limit_sleep` | Sleep path (mock `time.sleep`) |
| `test_provider_unavailable` | Clear ValueError when no provider |
| `test_list_indicators` | Returns expected names from package |
| `test_load_indicator_rsi` | `calculate()` runs on sample data |

Refactor existing `test_ohlcv_pull.py` — keep as `@pytest.mark.integration` for local runs with keys.

---

## P1 — Package structure cleanup (~half day)

### 1. Remove or archive `Legacy Scripts/`

Four old scripts (`pull_crypto.py`, `pull_fx.py`, etc.) duplicate what the library now does. Options:

- **Delete** (recommended) — git history preserves them
- **Move** to `archive/legacy-scripts/` with README explaining deprecation

### 2. CLI entry point in `pyproject.toml`

```toml
[project.scripts]
candlecraft = "candlecraft.cli:main"
```

Move core CLI logic from `pull_ohlcv.py` into `candlecraft/cli.py`. Keep `pull_ohlcv.py` as thin wrapper or remove.

### 3. Optional dependencies

```toml
[project.optional-dependencies]
binance = ["python-binance>=1.0.0"]
twelvedata = ["twelvedata>=1.0.0"]
cli = ["rich>=13.0.0"]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.1.0"]
all = ["candlecraft[binance,twelvedata,cli,dev]"]
```

Core install shouldn't force both providers if user only needs Binance.

---

## P1 — ARCHITECTURE.md (~2 hours)

**Sections:**

1. **Design goal** — one `fetch_ohlcv()` for all asset classes
2. **Layer diagram:**

```
fetch_ohlcv (api.py)
    → detect_asset_class (utils.py)
    → provider selection (api.py)
    → fetch_ohlcv_binance | fetch_ohlcv_twelvedata (providers.py)
    → validate_ohlcv → List[OHLCV] (models.py)
```

3. **OHLCV model** — why a dataclass, not raw dicts
4. **Rate limit strategy** — raise vs sleep, when to use each
5. **Indicator plugin pattern** — `calculate(ohlcv: list) -> dict`
6. **Extension point** — how to add a third provider (e.g. Coinbase, Polygon)

---

## P2 — Documentation site (~1 day)

**Options (pick easiest):**

| Approach | Effort | Result |
|----------|--------|--------|
| GitHub Pages + MkDocs Material | Medium | `alfredalpino.github.io/Candlecraft` |
| README + `docs/` folder only | Low | Good enough for now |
| ReadTheDocs | Medium | Auto-build on tag |

**Minimum:** `docs/api.md` with every public function, params, raises, example.

Add to `pyproject.toml`:

```toml
Documentation = "https://alfredalpino.github.io/Candlecraft"
```

(Don't link until site exists.)

---

## P2 — Developer experience polish

### CHANGELOG.md

Follow [Keep a Changelog](https://keepachangelog.com/). Document v0.2.0:

- **Fixed:** Indicators ship inside package
- **Changed:** print → logging in providers
- **Added:** CI, unit test suite

### Pre-commit (optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
```

### Type hints

- `providers.py` return types on all public functions
- Enable `mypy --strict` on `candlecraft/models.py` and `candlecraft/api.py` first

### `__init__.py` exports

```python
from candlecraft.api import fetch_ohlcv, list_indicators, load_indicator, get_available_providers
from candlecraft.models import OHLCV, AssetClass, Provider, RateLimitException
__all__ = [...]
```

One import path: `from candlecraft import fetch_ohlcv, OHLCV`

---

## P2 — Portfolio synergy with MMMM

### Add `examples/with_mmmm.py`

```python
"""Example: feed Candlecraft OHLCV into MMMM spread adjustment."""
from candlecraft import fetch_ohlcv
from candlecraft import load_indicator

ohlcv = fetch_ohlcv("BTCUSDT", "1h", limit=50)
rsi = load_indicator("rsi")
signal = rsi(ohlcv)
# Widen spreads when RSI extreme — pseudo-code for interview story
```

### Cross-link READMEs

- Candlecraft README → "Used by MarketMakingMegaMachine for signal-aware market making"
- MMMM README → "Market data via Candlecraft (PyPI)"

---

## P3 — Feature depth (when P0–P2 done)

| Feature | Value | Effort |
|---------|-------|--------|
| Async `fetch_ohlcv_async` | High for concurrent multi-symbol | Medium |
| Parquet/CSV export helper | Data eng appeal | Low |
| Caching layer (disk or Redis) | Rate limit + repeat queries | Medium |
| Third provider (Polygon, CoinGecko) | Shows extensibility | Medium |
| Pandas DataFrame return option | `return_df=True` kwarg | Low |
| WebSocket unified API | CLI has WS; library doesn't | High |

Don't add features before fixing indicators-in-package and CI.

---

## PyPI release checklist (v0.2.0)

- [ ] Indicators inside `candlecraft/indicators/`
- [ ] Logging replaces print in library
- [ ] Unit tests pass locally
- [ ] CI green on 3.10, 3.11, 3.12
- [ ] CHANGELOG.md updated
- [ ] Version bump in `pyproject.toml`
- [ ] `git tag v0.2.0 && git push --tags` (triggers publish workflow)
- [ ] Verify on PyPI: `pip install candlecraft==0.2.0` → `from candlecraft import load_indicator; load_indicator("rsi")`

---

## Interview talking points

1. **Why unified OHLCV?** — One interface for crypto/forex/equity; provider abstraction
2. **Rate limiting design** — raise vs sleep; `RateLimitException` with `retry_after`
3. **PyPI shipping** — setuptools, trusted publishing, semver
4. **Bug you found in your own code** — indicators path breaks on pip install (shows self-review)
5. **Testing strategy** — unit vs integration split, no keys in CI
6. **Connection to trading** — Candlecraft data → MMMM execution at 3poch

---

## Checklist (copy to issue tracker)

- [ ] Move indicators into `candlecraft/indicators/`
- [ ] Fix `list_indicators` / `load_indicator` for installed package
- [ ] Replace print with logging in `providers.py`
- [ ] Slim README + move docs to `docs/`
- [ ] Delete or archive `Legacy Scripts/`
- [ ] Add CI workflow + badge
- [ ] Add mocked unit tests; mark integration tests
- [ ] ARCHITECTURE.md
- [ ] CHANGELOG.md
- [ ] Optional deps in pyproject.toml
- [ ] CLI entry point (`candlecraft` command)
- [ ] Cross-link MMMM in README
- [ ] Release v0.2.0 to PyPI
- [ ] (Optional) MkDocs site on GitHub Pages

---

## What NOT to do

- Don't claim "production-ready" until indicators work via pip and CI is green
- Don't run live API tests in CI (flaky, burns rate limits, needs secrets)
- Don't keep 900-line `pull_ohlcv.py` duplicating library logic — thin CLI wrapper only
- Don't add 20 indicators before fixing packaging — 9 working indicators > 20 broken ones
- Don't rewrite in Rust — polish the Python package first

---

## Comparison: you vs typical portfolio libs

| Dimension | Typical junior repo | Candlecraft after P0–P2 |
|-----------|--------------------|-------------------------|
| Published | No | PyPI with semver |
| Tests | None or trivial | Unit + integration split |
| CI | None | Matrix 3.10–3.12 |
| Docs | README only | README + architecture + API |
| Install | `git clone` only | `pip install` works fully |
| Story | "I built a script" | "I ship libraries used in production MM" |

---

*Generated from portfolio analysis — 2026-06-24. Update this file as items ship.*
