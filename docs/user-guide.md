# User guide

The app has two pages, selectable in the sidebar, plus a language switcher (🌐 Türkçe / English / Deutsch).

## Model analysis

### Inputs (sidebar)

| Field | Meaning |
|---|---|
| BIST symbols | Borsa Istanbul tickers; `.IS` is added automatically |
| Other symbols | Any [Yahoo Finance](https://finance.yahoo.com) symbol: `AAPL`, `GC=F` (gold), `USDTRY=X`, `^XU100` … |
| CSV | Your own price file: first column date, other columns prices |
| Start / end date | Data window |
| Models | Which models to run (default: all) |
| Max weight per asset | Caps every asset (e.g. 25%) in models that support constraints |
| Training window / rebalance interval | Walk-forward backtest settings (default 252 / 21 trading days) |

Settings can be saved under a name and reloaded later.

### Tabs

- **Weights** — each model's allocation as a table and chart, with automatic commentary: concentration, effective
  number of assets, the largest risk source, and where the models agree (*consensus*). Below: the **efficient
  frontier** (every model as a point against the Markowitz frontier) and **risk contribution** per asset.
- **Backtest** — cumulative value of every model trained on a rolling window and tested on the next period, plus a
  summary table (annual return, volatility, Sharpe, Sortino, max drawdown, CVaR, turnover …). Commentary flags models
  that beat equal weight and warns about likely overfitting.
- **Black-Litterman** — add your own views ("THYAO will return 30%" or "ASELS will beat BIMAS by 5%") with a
  confidence level and see how they shift the weights relative to the market-implied portfolio.
- **📚 Models & guide** — the [model guide](models.md) and [metrics glossary](metrics.md), inside the app.

## My portfolio

### Positions

Each row is one holding. Types:

| Type | Symbol example | Priced from |
|---|---|---|
| BIST stock | `THYAO` | Yahoo Finance (`THYAO.IS`) |
| Yahoo symbol | `AAPL`, `VOO`, `BTC-USD` | Yahoo Finance, converted to TRY |
| Gram gold | — | gold ounce × USD/TRY |
| Cash | `TRY`, `USD`, `EUR` | FX rate |
| TEFAS fund | `TTE`, `AFT` | prices you upload or type in (see below) |

### Transactions

Switch to transaction mode to enter history instead of current quantities. Sides: **Buy**, **Sell**, **Dividend**,
**Deposit**, **Withdrawal**. The app computes quantities, average cost, realised P/L and dividends from them, and
optionally tracks cash (buys reduce cash, sells and dividends add to it).

**Importing statements** — upload CSV or Excel. Columns are recognised in English, Turkish and German:

| Date | Side | Type | Symbol | Quantity | Price | Amount |
|---|---|---|---|---|---|---|
| 2024-01-15 | Buy | BIST stock | THYAO | 100 | 245.5 | |
| 2024-06-03 | Dividend | BIST stock | THYAO | | | 1250 |
| 2024-02-01 | Deposit | Cash | TRY | | | 50000 |

German values (`Kauf`, `Verkauf`, `Dividende`, `Einzahlung`, `Auszahlung`) and Turkish values (`Al`, `Sat`,
`Temettü`, `Para yatır`, `Para çek`) work too. Decimal commas are understood. Rows already present are skipped, so
you can import overlapping statements. Download the template from the import panel to start.

### Fund prices (TEFAS)

TEFAS does not offer a public API, so fund prices come from you:

1. On [tefas.gov.tr](https://www.tefas.gov.tr), open *Historical data*, pick the fund and date range and export to
   Excel/CSV.
2. Upload it on the *Fund prices* tab — the file format is detected automatically. Or type prices in by hand.

Funds with a price history join the value chart, returns and rebalancing. The app warns when a fund price is stale.

### Results

- **Summary** — total value, invested capital, P/L, XIRR (money-weighted), TWR (time-weighted), number of assets.
- **Allocation** and **value over time** charts.
- **Comparison** — your TWR against BIST100, USD/TRY, gold and CPI, each as "what if every deposit had gone there".
  Real (inflation-adjusted) returns use TCMB EVDS CPI when configured, otherwise OECD.
- **Rebalancing** — choose a model's weights as target; get exact buy/sell quantities (whole shares for BIST) without
  overdrawing cash, plus a comment on the biggest moves. Mark assets as *fixed* to leave them untouched.
- **📧 Weekly email** — opt in to a Monday summary (multi-user servers with email configured).

## Privacy

In local mode everything stays on your computer. On a multi-user server, each signed-in user only ever sees their
own data. Prices are fetched from Yahoo Finance; no portfolio data is sent anywhere else.
