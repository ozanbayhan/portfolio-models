# Model portfolios

Brokers, banks and asset managers in many countries publish **model portfolios**: a list of assets with target
weights, revised every few weeks. The **🏛️ Model portfolios** page tracks any number of them side by side with
end-of-day prices, so you can see whose calls actually worked.

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
| `delete_model_portfolio` | Delete one and its history |

## Entering them by hand

Under **Add or update → ✍️ Manually**, choose a model portfolio (or a new one) and fill in the firm, country, source
link and effective date. Then list the assets and weights; weights are scaled to 100% if they don't add up. Saving
with a new date adds a revision. Saving with the same date replaces that revision.

## Limits

- Trading costs, taxes and dividends are not included (price returns).
- BIST-listed ETFs have no price history on Yahoo Finance and cannot be tracked.
- Only use content you are allowed to use. Model portfolios are the firms' views; this page only measures them with
  past prices. It is not investment advice.
