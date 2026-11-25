# Library & CLI

## Install

```bash
uv add git+https://github.com/ozanbayhan/portfolio-models     # in a project
uv tool install git+https://github.com/ozanbayhan/portfolio-models   # the CLI only
```

## Command line

```bash
portfolio-models list                                     # all models with descriptions
portfolio-models weights  --bist THYAO ASELS --tickers GC=F AAPL --start 2020-01-01
portfolio-models backtest --bist THYAO ASELS --tickers GC=F --train 252 --test 21 --out results
portfolio-models weights  --csv my_prices.csv --models hrp risk_parity
portfolio-models serve    --port 8501 --host 0.0.0.0 --data-dir ~/pm-data
portfolio-models report   --dry-run --out emails/        # weekly email summaries
```

`weights` and `backtest` write CSV and HTML results to `--out` (default `results/`).

## Python

```python
from portfolio_models import bist, load_prices, to_returns, fit_weights, backtest, summarize
from portfolio_models.models import list_models, get_model

prices = load_prices(bist("THYAO", "ASELS") + ["GC=F", "AAPL"], start="2020-01-01")
returns = to_returns(prices)

weights = fit_weights(returns, ["hrp", "risk_parity", "max_sharpe"], max_weight=0.4)  # DataFrame: assets × models
results = backtest(returns, ["equal_weighted", "hrp", "risk_parity"], train_size=252, test_size=21)
print(summarize(results))
```

Every model is a scikit-learn style estimator (skfolio interface), so you can use it directly:

```python
model = get_model("hrp")
model.fit(returns)
print(model.weights_)
```

Other modules you may find useful:

| Module | What's inside |
|---|---|
| `portfolio_models.holdings` | positions, transactions, cash, valuation, XIRR, rebalancing |
| `portfolio_models.benchmarks` | TWR index, benchmark comparison in TRY/USD/EUR, CPI for TR/US/DE (`fetch_cpi_best(region=...)`) |
| `portfolio_models.charts` | efficient frontier, risk contributions (Plotly) |
| `portfolio_models.insights` | rule-based commentary |
| `portfolio_models.model_guide` | model guide and metrics glossary in TR/EN/DE |
