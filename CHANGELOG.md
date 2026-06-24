# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-24

### Added

- Technical indicators ship inside the `candlecraft` package (`candlecraft.indicators`)
- Unit test suite with mocked providers (`tests/test_unit_api.py`)
- CI workflow on Python 3.10–3.12 (`.github/workflows/ci.yml`)
- `ARCHITECTURE.md`, `docs/api.md`, `docs/cli.md`
- `examples/quickstart.py` and `examples/with_mmmm.py`
- `py.typed` marker for type checkers

### Changed

- `list_indicators()` and `load_indicator()` resolve packaged indicators (pip install works)
- Library providers use `logging` instead of `print()` (silent by default)
- PyPI classifier updated to **Beta**
- README slimmed down; detailed docs moved to `docs/`
- Legacy standalone scripts moved to `archive/legacy-scripts/`

### Fixed

- Indicators were broken after `pip install candlecraft` (path pointed outside package)

## [0.1.4] - prior release

- Initial PyPI publish with Binance + Twelve Data providers
- CLI `pull_ohlcv.py` and root-level `indicators/` modules

[0.2.0]: https://github.com/alfredalpino/Candlecraft/compare/v0.1.4...v0.2.0
