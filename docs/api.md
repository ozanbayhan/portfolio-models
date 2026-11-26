# JSON API

`portfolio-models api` serves the model portfolio archive as a **read-only JSON API**, so a separate front end
(for example a React site) can show it. Public instance: `https://portfolio.orbitcashflow.com/api`.

```bash
portfolio-models api --port 8770 --data-dir ~/.portfolio-models      # http://127.0.0.1:8770/api
docker run -d -p 127.0.0.1:8770:8770 -v pm-data:/data ghcr.io/ozanbayhan/portfolio-models api
```

It reads the model portfolios of the archive user (`PM_ARCHIVE_USER`, default the local-mode user) from the same
database as the web app and the [MCP server](ai-assistants.md); add and update them there. With no portfolios saved
it returns three examples with made-up firm names and `"example": true`.

Prices are kept in memory and refreshed every day after the Borsa Istanbul and US closes (15:45 and 21:45 UTC), and
within five minutes of any change to the archive. Responses are cached until the next refresh and warmed up in the
background.

## Conventions

- Ratios are fractions (`0.123` = 12.3 %). Missing values are `null`. Dates are `YYYY-MM-DD`.
- Series are `[["YYYY-MM-DD", value], …]` and start at 100.
- Every endpoint accepts `lang=tr|en` (labels, notes, disclaimer). `currency` is `TRY`, `USD` or `EUR`;
  `benchmark` is one of `BIST100`, `S&P 500`, `DAX`, `Gram altın`, `USD`, `EUR` or `none`.
- Errors: `{"error": "…"}` with status 400 or 404. CORS is open for `GET` (`PM_API_CORS` to restrict).

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Status, version, latest price date |
| `GET /api/meta` | Currencies, benchmarks, rankings (label, help), windows, analysis models, countries, disclaimer |
| `GET /api/portfolios?currency=` | One card per model portfolio: returns 1D–1Y, YTD, since inception, volatility, drawdown, Sharpe, sparkline |
| `GET /api/leaderboard?by=&window=&currency=&benchmark=` | Ranking by `return`, `risk_adjusted`, `alpha`, `hit_rate`, `consistency`, `drawdown`, `volatility`; `window` = `since_inception`, `ytd`, `1y`, `3m` |
| `GET /api/portfolios/{slug}?currency=&benchmark=` | Holdings, revision history, index and benchmark series, full scorecard |
| `GET /api/portfolios/{slug}/analysis?currency=&benchmark=&revision=` | [Optimisation analysis](model-portfolios.md#optimisation-analysis) of one revision |
| `GET /api/analysis?currency=&benchmark=` | Optimisation analysis of **all** portfolios: per portfolio the firm's rank among the models by Sharpe, closest and best model, selection/weighting split; per model how often it beat the firm and was closest |
| `GET /api/compare?slugs=a,b&currency=&benchmark=` | Index series and returns of up to 8 portfolios plus the benchmark |

The analysis, rankings and performance are a statistical summary of past prices computed by this app and are not
investment advice.
