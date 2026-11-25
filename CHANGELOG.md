# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **US and German inflation:** the comparison can now run in USD against US CPI (FRED, BLS fallback) with S&P 500,
  or in EUR against German CPI (Deutsche Bundesbank / Destatis VPI) with DAX — alongside TRY and Turkish CPI.
  No API keys needed; OECD is the fallback for all three countries.

## [0.2.1] — 2026-11-25

### Fixed
- Docker image build (README and LICENSE are now copied into the build stage); `ghcr.io/ozanbayhan/portfolio-models:0.2.1`
  is the first published versioned image.
- Benchmark table showed "None" for missing values; now shows "—".
- Default portfolio name is translated (was always Turkish).

### Added
- Demo GIF in the README and docs.

## [0.2.0] — 2026-11-25

### Added
- **Self-hosting:** `portfolio-models serve` command (local mode without sign-in), Docker image on GHCR
  (multi-arch), Docker Compose with optional Postgres and weekly-email profiles, `.env` configuration.
- **Documentation site** with self-hosting, user guide, model guide, metrics glossary, library & CLI, FAQ.
- Efficient frontier and risk contribution charts; maximum weight per asset across all models that support it.
- "Try a sample portfolio" demo data; new visual theme.
- Model guide (history, idea, how to read, strengths, cautions) and metrics glossary in three languages.
- Rule-based commentary for weights, backtests, Black-Litterman and rebalancing.
- Türkçe / English / Deutsch interface, emails and statement import.
- Benchmark comparison against BIST100, USD/TRY, gold and CPI (TCMB EVDS or OECD), nominal and real.
- Weekly email summary (opt-in).
- Dividends, deposits, withdrawals and multi-currency cash tracking.
- Transaction history, CSV/Excel statement import/export, TEFAS fund price history.
- Portfolio tracker with positions, valuation, XIRR, TWR and rebalancing suggestions.
- Google sign-in with per-user storage (SQLite or Postgres).

### Changed
- The web UI moved into the package (`portfolio_models.web`); the root `app.py` is now a thin shim.

## [0.1.0] — 2026-11-24

### Added
- 24 portfolio models on skfolio, Riskfolio-Lib and PyPortfolioOpt behind one interface.
- Walk-forward backtests, CLI (`list`, `weights`, `backtest`), Streamlit UI, CI.

[Unreleased]: https://github.com/ozanbayhan/portfolio-models/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/ozanbayhan/portfolio-models/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ozanbayhan/portfolio-models/releases/tag/v0.2.0
