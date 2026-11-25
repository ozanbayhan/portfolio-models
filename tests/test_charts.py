import numpy as np
import pandas as pd
import pytest

from portfolio_models import fit_weights
from portfolio_models.charts import (
    efficient_frontier,
    frontier_figure,
    portfolio_point,
    risk_contributions,
    risk_figure,
)


@pytest.fixture(scope="module")
def returns():
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2024-01-01", periods=400)
    return pd.DataFrame({f"A{i}": rng.normal(0.0003 * (i + 1), 0.006 * (i + 1), 400) for i in range(4)}, index=idx)


def test_frontier_monotone_and_bounded(returns):
    ef = efficient_frontier(returns, size=15)
    assert len(ef) >= 5
    assert ef["vol"].is_monotonic_increasing
    # sınırın en düşük oynaklık noktası, min. varyans portföyüne eşit (ya da çok yakın)
    mv = fit_weights(returns, ["min_variance"])["min_variance"]
    assert ef["vol"].iloc[0] == pytest.approx(portfolio_point(mv, returns)[0], rel=1e-2)
    # her model sınırın üzerinde ya da altında kalır (sınırın üstüne çıkamaz)
    ms = fit_weights(returns, ["max_sharpe"])["max_sharpe"]
    vol, ret = portfolio_point(ms, returns)
    assert ret <= np.interp(vol, ef["vol"], ef["ret"]) + 1e-3


def test_risk_contributions_sum_to_one(returns):
    w = fit_weights(returns, ["equal_weighted", "risk_parity"])
    rc = risk_contributions(w, returns)
    assert rc.sum().round(6).eq(1).all()
    # risk paritesinde katkılar eşit
    assert rc["risk_parity"].std() < 0.02


def test_figures_build(returns):
    w = fit_weights(returns, ["equal_weighted", "hrp"])
    f1 = frontier_figure(returns, w, {"frontier": "F", "assets": "A", "x": "x", "y": "y"})
    assert len(f1.data) == 2 + 2
    f2 = risk_figure(w, returns, {"y": "y"})
    assert len(f2.data) == returns.shape[1]
