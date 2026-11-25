# AI assistants (MCP)

Portfolio Models ships a [Model Context Protocol](https://modelcontextprotocol.io) server, so you can connect
Claude, ChatGPT, Cursor, VS Code or any other MCP client to it and ask in plain language:

> *"What's my portfolio worth today and which position lost most this week?"*
> *"Add 20 VOO at $610 to my portfolio."*
> *"Compare min-variance and HRP for THYAO, ASELS, VOO and BTC-USD since 2021."*
> *"Did I beat Turkish inflation? What is US CPI right now?"*

The server reads and writes **the same database as the web app**, so everything the assistant adds appears in
*My portfolio* and vice versa. It runs on your own machine; nothing is sent anywhere except price and inflation
requests (Yahoo Finance, TCMB EVDS, FRED/BLS, Bundesbank, OECD).

## Tools

| Tool | What it does | Changes data |
|---|---|---|
| `list_models` | The optimisation models with a short description | no |
| `optimize_portfolio` | Weights of each model for the given symbols | no |
| `backtest_models` | Walk-forward backtest, ranked by Sharpe | no |
| `get_prices` | Last close and 1-month / 1-year returns | no |
| `get_inflation` | Year-over-year CPI for Turkey, the US or Germany | no |
| `list_portfolios` | Your saved portfolios | no |
| `get_portfolio` | Positions, transactions and live valuation in TRY (value, weight, P&L, weekly change) | no |
| `list_model_portfolios` | Saved model portfolios (firm, country, last update) | no |
| `get_model_portfolio` | Current weights, source and revision history of one model portfolio | no |
| `compare_model_portfolios` | 1D–1Y, YTD and since-inception returns, volatility and drawdown vs. benchmarks | no |
| `rank_model_portfolios` | Rank by return, Sharpe, alpha, hit rate, consistency, drawdown or volatility | no |
| `analyze_model_portfolio` | Compare a model portfolio with optimisation models on the same assets | no |
| `add_position` | Add or update a holding (BIST stock, US/global stock/ETF, TEFAS fund, gold, cash) | **yes** |
| `remove_position` | Remove a holding | **yes** |
| `add_transaction` | Record a buy, sell, dividend, deposit or withdrawal | **yes** |
| `save_model_portfolio` | Save a firm's publicly published model portfolio (source link required), or a new dated revision | **yes** |
| `delete_model_portfolio` | Delete a model portfolio | **yes** |

Start with `--read-only` (or `PM_MCP_READ_ONLY=1`) to offer only the read tools. Most clients also ask you to
approve each write.

## Connect

=== "Claude Desktop"

    *Settings → Developer → Edit Config* and add:

    ```json
    {
      "mcpServers": {
        "portfolio-models": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/ozanbayhan/portfolio-models", "portfolio-models", "mcp"]
        }
      }
    }
    ```

    Restart Claude Desktop. The tools appear under the 🔌 icon.

=== "Claude Code"

    ```bash
    claude mcp add portfolio-models -- uvx --from git+https://github.com/ozanbayhan/portfolio-models portfolio-models mcp
    ```

=== "Cursor / VS Code"

    `.cursor/mcp.json` or `.vscode/mcp.json`:

    ```json
    {
      "servers": {
        "portfolio-models": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/ozanbayhan/portfolio-models", "portfolio-models", "mcp"]
        }
      }
    }
    ```

=== "Docker"

    Uses the same `pm-data` volume as the web app container:

    ```json
    {
      "mcpServers": {
        "portfolio-models": {
          "command": "docker",
          "args": ["run", "-i", "--rm", "-v", "pm-data:/data", "ghcr.io/ozanbayhan/portfolio-models:latest", "mcp"]
        }
      }
    }
    ```

=== "HTTP"

    For clients that connect to a URL (ChatGPT developer mode, remote agents):

    ```bash
    portfolio-models mcp --http                 # http://127.0.0.1:8765/mcp
    ```

    !!! warning
        The HTTP endpoint has **no authentication**. Keep it on `127.0.0.1`, or put it behind a reverse proxy
        with authentication / a private network (Tailscale, WireGuard) before exposing it.

If you already installed the app with `uv tool install`, the command is simply `portfolio-models mcp`.

## Options

| Flag / variable | Default | Purpose |
|---|---|---|
| `--data-dir` / `PM_DATA_DIR` | `~/.portfolio-models` | Folder of `portfolios.db` — use the same as `serve` |
| `PM_DATABASE_URL` | SQLite in the data dir | Postgres or another SQLAlchemy URL |
| `PM_MCP_USER` | the local-mode user | In multi-user setups: whose portfolio the assistant sees (an e-mail address) |
| `--read-only` / `PM_MCP_READ_ONLY` | off | Hide the write tools (`add_position`, `save_model_portfolio`, …) |
| `PM_EVDS_API_KEY` | — | Up-to-date Turkish CPI (OECD otherwise) |
| `--http`, `--host`, `--port` | stdio, `127.0.0.1`, `8765` | Streamable HTTP transport |

## Symbols

| Asset | Kind | Example |
|---|---|---|
| Borsa Istanbul stock | `bist` | `THYAO`, `ASELS` (BIST-listed ETFs have no history on Yahoo Finance) |
| US/global stock or ETF, crypto, anything on Yahoo Finance | `yahoo` | `AAPL`, `VOO`, `QQQ`, `IWDA.AS`, `BTC-USD` |
| TEFAS fund | `fund` | `TTE` (give `current_price` in TRY) |
| Gram gold | `gold` | no symbol |
| Cash | `cash` | `TRY`, `USD`, `EUR` |

!!! note
    Optimisation results are educational and based on past returns. They are not investment advice.
