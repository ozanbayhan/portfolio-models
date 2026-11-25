# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] — 2026-11-26

### Added
- **🏆 Ranking** of model portfolios by return, risk-adjusted return (Sharpe/Sortino), alpha vs. benchmark, hit rate,
  monthly consistency, drawdown or volatility, since inception or over a common window.
- **📐 Optimisation analysis:** the same assets are given to seven optimisation models with only the data before
  each revision date; compares weights, risk profile and performance ("same assets, different weights") and splits
  the excess return into selection and weighting.
- MCP tools `rank_model_portfolios` and `analyze_model_portfolio`.

### Changed
- Model portfolios are framed as an archive of openly published portfolios: `source_url` is required when saving
  through MCP and must be an http(s) link, notes are limited to 280 characters, and the assistant is told to skip
  portfolios behind a login or whose terms forbid reuse and never to copy report text. Clearer disclaimer on the page.

## [0.3.0] — 2026-11-26

### Added
- **🏛️ Model portfolios page:** track model portfolios published by brokers, banks and asset managers in any country
  side by side with end-of-day prices — chart and table in TRY/USD/EUR, 1D–1Y, YTD and since-inception returns,
  volatility, max drawdown, optional benchmarks. Every update is stored as a dated revision and applied on its date.
  Add them by hand or let your AI assistant keep them current through the new MCP tools (`save_model_portfolio`,
  `compare_model_portfolios`, …). See `docs/model-portfolios.md`.
- **MCP server for AI assistants:** `portfolio-models mcp` lets Claude, ChatGPT, Cursor, VS Code and other MCP clients
  read your portfolio and live valuation, add or remove positions and transactions, run optimisations and backtests,
  and fetch prices and CPI (TR/US/DE). stdio by default, `--http` for Streamable HTTP, `--read-only` to hide write
  tools; also available as the `mcp` command of the Docker image. See `docs/ai-assistants.md`.

### Changed
- The symbol fields and position help now say explicitly that US/global ETFs (VOO, QQQ, IWDA.AS) are supported as
  Yahoo symbols.

## [0.2.2] — 2026-11-25

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

[Unreleased]: https://github.com/ozanbayhan/portfolio-models/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/ozanbayhan/portfolio-models/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ozanbayhan/portfolio-models/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/ozanbayhan/portfolio-models/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ozanbayhan/portfolio-models/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ozanbayhan/portfolio-models/releases/tag/v0.2.0
