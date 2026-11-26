# Model portfolios

Brokers, banks and asset managers in many countries publish **model portfolios**: a list of assets with target
weights, revised every few weeks. The **🏛️ Model portfolios** page tracks any number of them side by side with
end-of-day prices, ranks them, and shows how each one looks through the optimisation models.
It is an **archive and a mathematical analysis** of portfolios that firms publish openly, not a recommendation service.

## What you get

- One chart (start = 100) and one table for all selected model portfolios, in **TRY, USD or EUR**.
- Returns for 1 day, 1 week, 1 and 3 months, year-to-date, 1 year and since inception; annualised return,
  volatility and maximum drawdown.
- Optional benchmarks: BIST100, S&P 500, DAX, gram gold, USD, EUR.
- **Dated revisions.** Every update is stored with the date it took effect. The portfolio is rebuilt with the new
  weights on that date and held until the next revision, so the history is not rewritten when a firm changes its
  picks.
- Prices refresh every 15 minutes (Yahoo Finance closes; intraday last price for today).

Assets can be BIST stocks, anything on Yahoo Finance (US/European stocks, ETFs, crypto), TEFAS funds (with a price
history uploaded on *My portfolio*), gram gold and cash. If an asset has no price on a revision date, it is left out
and its weight is spread over the others. A warning says so.

## 🏆 Ranking

The **Ranking** tab orders the selected model portfolios by one measure, since inception or over a window
(year-to-date, 1 year, 3 months; with a window all portfolios start on the same day and those that started later are
left out):

| Ranking | Measure |
|---|---|
| Highest return | Total return in the period |
| Risk-adjusted return | Sharpe ratio: mean daily return ÷ volatility, annualised (no risk-free rate deducted); Sortino shown too |
| Excess over benchmark | Alpha: annualised return minus the benchmark's (≥ 90 days); beta, tracking error and information ratio in the MCP output |
| Hit rate | Share of the assets picked in each revision (cash excluded) that beat the benchmark while they were held |
| Consistency | Share of calendar months in which the portfolio beat the benchmark (≥ 3 months) |
| Smallest drawdown / lowest volatility | Largest fall from a peak; annualised volatility |

## 📐 Optimisation analysis

How does a firm's portfolio look to an optimiser? For the chosen revision, the **same assets** are given to the
optimisation models (equal weight, inverse volatility, minimum variance, max Sharpe with shrinkage, risk parity, HRP,
maximum diversification and Black-Litterman) using **only prices before the revision date** (up to one year), so nothing looks ahead.

- **Weights** of the firm next to each model's, and how far each model is from the firm (½ Σ|wᵢ − aᵢ|: the share of
  the portfolio that would have to move). The closest model tells you which style the firm's weighting resembles.
- **Risk profile** with the same data: annual volatility, past return, return/risk, effective number of assets
  (1 / Σw²), diversification ratio (Σwσ / σₚ) and the asset that contributes most to risk.
- **Same assets, different weights:** each model is re-fitted on every revision date of the firm and held until the
  next one. The chart and table compare the firm's path with the models' and the benchmark.
- **Selection vs. weighting:** the difference to the benchmark since the first revision is split into *asset
  selection* (same assets equally weighted minus benchmark) and *weighting* (firm minus equal weight).

**Black-Litterman with the firm's view.** Reverse optimisation asks which annual returns the firm must expect for its
weights to be mean-variance optimal: π = δΣw (δ = 2.5). These implied returns are the prior; each asset's past mean
return is a view (P = I, Ω = diag(τΣ), τ = 0.05). The posterior expected returns give a long-only max-Sharpe
portfolio — the firm's conviction tempered by the data. The page charts past, implied and Black-Litterman returns per
asset.

**Charts** (all with data before the revision): efficient frontier with the firm, every model and every asset; stacked
weights and risk contributions; correlation heat map.

Cash and assets without enough price history (60 trading days) keep the firm's weight; the models only re-weight the
rest.

## Keeping them up to date with AI

Connect your assistant with [MCP](ai-assistants.md), then ask it, for example:

> *"Find Acme Securities' monthly model portfolio on their website and save it."*
> *"Check the source pages of my saved model portfolios and record any change with its date."*
> *"Compare the model portfolios in USD. Which did best over 3 months, and with what drawdown?"*

The assistant reads the firm's own published page and calls `save_model_portfolio` with the exact holdings and
weights, the effective date and the page URL as source. It is instructed not to guess weights. To keep things current
automatically, use your assistant's scheduled tasks (for example, every Monday morning).

| MCP tool | What it does |
|---|---|
| `list_model_portfolios` | Saved model portfolios with current weights |
| `get_model_portfolio` | Full revision history of one |
| `save_model_portfolio` | Create one, or add a dated revision |
| `compare_model_portfolios` | Performance table in TRY/USD/EUR with benchmarks |
| `rank_model_portfolios` | Rank by return, Sharpe, alpha, hit rate, consistency, drawdown or volatility |
| `analyze_model_portfolio` | The optimisation analysis above for one portfolio and revision |
| `delete_model_portfolio` | Delete one and its history |

## Entering them by hand

Under **Add or update → ✍️ Manually**, choose a model portfolio (or a new one) and fill in the firm, country, source
link and effective date. Then list the assets and weights; weights are scaled to 100% if they don't add up. Saving
with a new date adds a revision. Saving with the same date replaces that revision.

## Limits

- Trading costs, taxes and dividends are not included (price returns).
- BIST-listed ETFs have no price history on Yahoo Finance and cannot be tracked.
- Performance is computed by this app and may differ from the figures a firm publishes.

## Sources, copyright and investment advice

- Add only portfolios that are **publicly accessible** without login, paywall or client account, and only when the
  site's terms allow reuse. The AI assistant is instructed to skip anything else and tell you.
- Only **facts** are stored: assets, weights, the effective date and a link to the source (`source_url` is required
  through MCP). The reports' text, commentary, charts and files are not copied; a note is limited to 280 characters
  in your own words.
- Rankings are a statistical summary of past prices, not a recommendation. Nothing on the page is investment advice.
- If you run a public instance, offer a contact for corrections and removal requests and act on them promptly.
