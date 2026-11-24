"""Riskfolio-Lib ve PyPortfolioOpt modellerini skfolio arayüzüne bağlayan adaptör.

Böylece bu kütüphanelerin modelleri de skfolio'nun backtest araçlarıyla
(WalkForward, cross_val_predict, Population) yan yana karşılaştırılabilir.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
import sklearn.utils.validation as skv
from skfolio.optimization import BaseOptimization

WeightFn = Callable[[pd.DataFrame], pd.Series]


# --- Riskfolio-Lib -----------------------------------------------------------


def riskfolio_hrp(returns: pd.DataFrame) -> pd.Series:
    import riskfolio as rp

    port = rp.HCPortfolio(returns=returns)
    w = port.optimization(
        model="HRP", codependence="pearson", rm="MV", rf=0, linkage="ward", leaf_order=True
    )
    return w["weights"]


def riskfolio_max_sharpe_cvar(returns: pd.DataFrame) -> pd.Series:
    import riskfolio as rp

    port = rp.Portfolio(returns=returns)
    port.assets_stats(method_mu="hist", method_cov="hist")
    w = port.optimization(model="Classic", rm="CVaR", obj="Sharpe", rf=0, l=0, hist=True)
    if w is None:
        raise ValueError("Riskfolio optimizasyonu çözüm bulamadı.")
    return w["weights"]


def riskfolio_min_cdar(returns: pd.DataFrame) -> pd.Series:
    import riskfolio as rp

    port = rp.Portfolio(returns=returns)
    port.assets_stats(method_mu="hist", method_cov="hist")
    w = port.optimization(model="Classic", rm="CDaR", obj="MinRisk", rf=0, l=0, hist=True)
    if w is None:
        raise ValueError("Riskfolio optimizasyonu çözüm bulamadı.")
    return w["weights"]


# --- PyPortfolioOpt ----------------------------------------------------------


def pypfopt_max_sharpe(returns: pd.DataFrame) -> pd.Series:
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    mu = expected_returns.mean_historical_return(returns, returns_data=True)
    cov = risk_models.CovarianceShrinkage(returns, returns_data=True).ledoit_wolf()
    ef = EfficientFrontier(mu, cov)
    ef.max_sharpe(risk_free_rate=0.0)
    return pd.Series(ef.clean_weights())


def pypfopt_cla_min_vol(returns: pd.DataFrame) -> pd.Series:
    from pypfopt import CLA, expected_returns, risk_models

    mu = expected_returns.mean_historical_return(returns, returns_data=True)
    cov = risk_models.sample_cov(returns, returns_data=True)
    cla = CLA(mu, cov)
    cla.min_volatility()
    return pd.Series(cla.clean_weights())


def pypfopt_hrp(returns: pd.DataFrame) -> pd.Series:
    from pypfopt import HRPOpt

    hrp = HRPOpt(returns=returns)
    hrp.optimize()
    return pd.Series(hrp.clean_weights())


METHODS: dict[str, WeightFn] = {
    "riskfolio_hrp": riskfolio_hrp,
    "riskfolio_max_sharpe_cvar": riskfolio_max_sharpe_cvar,
    "riskfolio_min_cdar": riskfolio_min_cdar,
    "pypfopt_max_sharpe": pypfopt_max_sharpe,
    "pypfopt_cla_min_vol": pypfopt_cla_min_vol,
    "pypfopt_hrp": pypfopt_hrp,
}


class ExternalOptimization(BaseOptimization):
    """Herhangi bir `getiriler -> ağırlıklar` fonksiyonunu skfolio tahmincisine çevirir."""

    def __init__(self, method: str = "riskfolio_hrp", portfolio_params: dict | None = None):
        super().__init__(portfolio_params=portfolio_params)
        self.method = method

    def fit(self, X, y=None) -> "ExternalOptimization":
        columns = list(X.columns) if isinstance(X, pd.DataFrame) else None
        arr = skv.validate_data(self, X)
        df = pd.DataFrame(arr, columns=columns or [f"x{i}" for i in range(arr.shape[1])])
        if isinstance(X, pd.DataFrame):
            df.index = X.index
        weights = METHODS[self.method](df).reindex(df.columns).fillna(0.0)
        w = weights.to_numpy(dtype=float)
        total = w.sum()
        if not np.isfinite(total) or total <= 0:
            raise ValueError(f"{self.method}: geçersiz ağırlıklar")
        self.weights_ = w / total
        return self
