"""Modelleri tek seferde ağırlıklandırma ve walk-forward backtest ile karşılaştırma."""

from __future__ import annotations

import warnings
from typing import Callable

import pandas as pd
from skfolio import Population
from skfolio.model_selection import WalkForward, cross_val_predict

from .models import MODELS, get_model

SUMMARY_ROWS = {
    "Annualized Mean": "Yıllık getiri",
    "Annualized Standard Deviation": "Yıllık volatilite",
    "Annualized Sharpe Ratio": "Sharpe",
    "Annualized Sortino Ratio": "Sortino",
    "MAX Drawdown": "Maks. düşüş",
    "CVaR at 95%": "CVaR %95",
}


def _report(name: str, exc: Exception) -> None:
    print(f"[atlandı] {name}: {exc}")


def _names(models: list[str] | None) -> list[str]:
    return list(MODELS) if not models else models


def fit_weights(
    returns: pd.DataFrame,
    models: list[str] | None = None,
    on_error: Callable[[str, Exception], None] = _report,
) -> pd.DataFrame:
    """Her modeli tüm veriyle eğitir; satır = varlık, sütun = model olan ağırlık tablosu döner."""
    out: dict[str, pd.Series] = {}
    for name in _names(models):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                est = get_model(name).fit(returns)
            out[name] = pd.Series(est.weights_, index=returns.columns)
        except Exception as exc:  # noqa: BLE001 - bir model çökerse diğerleri sürsün
            on_error(name, exc)
    return pd.DataFrame(out)


def backtest(
    returns: pd.DataFrame,
    models: list[str] | None = None,
    train_size: int = 252,
    test_size: int = 21,
    on_error: Callable[[str, Exception], None] = _report,
) -> Population:
    """Walk-forward backtest: train_size gün eğit, test_size gün tut, kaydır, tekrarla."""
    cv = WalkForward(train_size=train_size, test_size=test_size)
    portfolios = []
    for name in _names(models):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pred = cross_val_predict(
                    get_model(name), returns, cv=cv, portfolio_params={"name": name}
                )
            portfolios.append(pred)
        except Exception as exc:  # noqa: BLE001
            on_error(name, exc)
    return Population(portfolios)


def summarize(population: Population) -> pd.DataFrame:
    """Okunabilir performans tablosu (Sharpe'a göre sıralı)."""
    summary = population.summary(formatted=False)
    rows = [r for r in SUMMARY_ROWS if r in summary.index]
    table = summary.loc[rows].rename(index=SUMMARY_ROWS).T
    table = table.apply(pd.to_numeric, errors="coerce")
    return table.sort_values("Sharpe", ascending=False)
