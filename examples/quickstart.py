"""Python içinden kullanım örneği.

Çalıştır:  uv run python examples/quickstart.py
"""

from portfolio_models import backtest, bist, fit_weights, load_prices, summarize, to_returns

tickers = bist("THYAO", "ASELS", "EREGL", "GARAN", "BIMAS") + ["GC=F", "USDTRY=X"]
returns = to_returns(load_prices(tickers, start="2020-01-01"))

# 1) Bugünkü ağırlıklar (tüm veriyle eğitilmiş)
weights = fit_weights(returns, ["hrp", "risk_parity", "max_sharpe", "min_cvar"])
print((weights * 100).round(1))

# 2) Geçmiş performans: 1 yıl eğit, ayda bir yeniden dengele
population = backtest(returns, ["equal_weighted", "hrp", "risk_parity", "max_sharpe"])
print(summarize(population).round(3))
population.plot_cumulative_returns().show()
