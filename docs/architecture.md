# Architecture

```
src/portfolio_models/
├── models.py         registry of 24 models (skfolio / Riskfolio-Lib / PyPortfolioOpt) behind one interface
├── adapters.py       wraps Riskfolio-Lib and PyPortfolioOpt as skfolio-style estimators
├── data.py           price download (Yahoo Finance), CSV loading, returns
├── backtest.py       fit_weights, walk-forward backtest, summary statistics
├── charts.py         efficient frontier, risk contribution, Plotly theme
├── holdings.py       positions, transactions, cash, valuation, XIRR, rebalancing
├── fund_prices.py    TEFAS export parsing, manual price history
├── trades_io.py      CSV/Excel import & export of transactions (TR/EN/DE)
├── benchmarks.py     TWR, benchmarks in TRY/USD/EUR, CPI for Türkiye (EVDS), US (FRED/BLS), Germany (Bundesbank), OECD fallback
├── insights.py       rule-based commentary
├── model_guide.py    model history & reading guide, metrics glossary (TR/EN/DE)
├── i18n.py           t() — Turkish source strings are the keys
├── locales.py        English & German catalogue
├── store.py          SQLAlchemy storage, every row keyed by user e-mail
├── report.py         weekly email summaries
├── cli.py            `portfolio-models` command
└── web/
    ├── app.py            Streamlit entry point, navigation, auth, model analysis page
    ├── holdings_page.py  "My portfolio" page
    └── ui.py             CSS, hero, footer
app.py                shim for Streamlit Community Cloud
docker/entrypoint.sh  turns PM_* environment variables into Streamlit secrets
```

## Design decisions

- **Library first.** All maths lives in plain, tested Python modules; the Streamlit UI only calls them. You can use
  everything without the UI.
- **One estimator interface.** Models from three libraries are exposed as skfolio-style estimators, so backtests,
  frontiers and weight caps work the same for all of them.
- **No hidden services.** Prices from Yahoo Finance, CPI from TCMB EVDS, FRED/BLS, Bundesbank or OECD, storage in SQLite or your Postgres.
  Nothing else is contacted.
- **Per-user isolation in the data layer.** Every query in `store.py` filters by the signed-in user's e-mail; local
  mode uses a fixed local user.
- **Translations without tooling.** Turkish strings are the catalogue keys; `scripts/i18n_keys.py` lists keys that
  lack English or German translations, and a test fails if any are missing.

## Tests

```bash
uv sync
uv run pytest -q
```

The suite (~500 tests) covers models, backtests, holdings maths, imports, storage isolation, benchmarks, emails,
commentary, translations and the Streamlit pages (via `AppTest`).
