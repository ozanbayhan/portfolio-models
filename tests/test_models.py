"""İnternet gerektirmeyen testler: sentetik veriyle her model çalışıyor mu?

Haftalık CI bu testleri kütüphanelerin en yeni sürümleriyle de çalıştırır;
bir güncelleme bir modeli bozarsa burada yakalanır.
"""

import numpy as np
import pandas as pd
import pytest

from portfolio_models import MODELS, backtest, fit_weights, get_model, summarize


@pytest.fixture(scope="module")
def returns() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_days, n_assets = 600, 6
    market = rng.normal(0.0004, 0.01, n_days)
    data = {
        f"A{i}": 0.0002 * (i + 1) + (0.5 + 0.1 * i) * market + rng.normal(0, 0.008 + 0.002 * i, n_days)
        for i in range(n_assets)
    }
    index = pd.bdate_range("2022-01-03", periods=n_days)
    return pd.DataFrame(data, index=index)


@pytest.mark.parametrize("name", list(MODELS))
def test_model_weights(name, returns):
    est = get_model(name).fit(returns)
    w = np.asarray(est.weights_)
    assert w.shape == (returns.shape[1],)
    assert np.all(np.isfinite(w))
    assert w.sum() == pytest.approx(1.0, abs=1e-3)
    assert w.min() >= -1e-6  # varsayılan modeller açığa satış yapmaz


def test_fit_weights_table(returns):
    table = fit_weights(returns, ["equal_weighted", "hrp"])
    assert list(table.columns) == ["equal_weighted", "hrp"]
    assert table.loc["A0", "equal_weighted"] == pytest.approx(1 / 6)


def test_backtest_summary(returns):
    pop = backtest(returns, ["equal_weighted", "min_variance", "pypfopt_cla_min_vol"], train_size=252, test_size=63)
    table = summarize(pop)
    assert len(table) == 3
    assert "Sharpe" in table.columns


def test_max_weight_constraint(returns):
    from portfolio_models.models import supports_max_weight

    for name in ["min_variance", "max_sharpe", "hrp", "risk_parity"]:
        assert supports_max_weight(name)
        w = np.asarray(get_model(name, max_weight=0.25).fit(returns).weights_)
        assert w.max() <= 0.25 + 1e-4, name
    assert not supports_max_weight("equal_weighted")
    table = fit_weights(returns, ["max_sharpe"], max_weight=0.3)
    assert table["max_sharpe"].max() <= 0.3 + 1e-4
