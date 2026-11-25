# Getting started

## 1. Try the demo

Open <https://portfolio-models.streamlit.app> (add `?lang=en` or `?lang=de` for English or German). Go to
**My portfolio** and click **🎯 Try a sample portfolio** — every chart, table and comment is filled with example data.
Nothing is saved unless you sign in.

## 2. Run it locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (one command on macOS, Linux and Windows), then:

```bash
uvx --from git+https://github.com/ozanbayhan/portfolio-models portfolio-models serve
```

Your browser opens <http://localhost:8501>. The app runs in **local mode**: no sign-in, a single user, and
your data is saved to `~/.portfolio-models/portfolios.db`.

Prefer Docker?

```bash
docker run -d --name portfolio-models -p 8501:8501 -v pm-data:/data ghcr.io/ozanbayhan/portfolio-models:latest
```

## 3. Your first analysis

1. On **Model analysis**, type a few BIST symbols (e.g. `THYAO ASELS BIMAS`) and/or Yahoo symbols (`GC=F`, `AAPL`,
   `USDTRY=X`) in the sidebar.
2. Choose a start date and, optionally, a maximum weight per asset.
3. Press **Run**. The *Weights* tab shows every model's allocation with commentary, the efficient frontier and risk
   contributions; the *Backtest* tab compares the models on unseen data.

## 4. Your first portfolio

1. Go to **My portfolio** → *Positions* and add rows (type, symbol, quantity, optional cost), or switch to
   *Transactions* and enter dated buys/sells — or import a CSV/Excel statement.
2. Click **Save** to keep it (local mode saves to your disk; on a multi-user server it is saved to your account).
3. Scroll down for value over time, P/L, benchmark comparison and rebalancing suggestions.

Next: the full [user guide](user-guide.md), or [host it on a server](self-hosting.md).
