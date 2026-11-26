"""Model analizi laboratuvarı: web arayüzündeki "📊 Model analizi" sayfasının hesapları, arayüzden bağımsız.

Streamlit sayfası ve JSON API (``/api/lab/*``) aynı fonksiyonları kullanır:

- :func:`optimize` — seçilen modellerin ağırlıkları, etkin sınır, risk katkıları, ağırlık ölçütleri ve yorumlar
- :func:`run_backtest` — walk-forward backtest özeti, kümülatif getiri ve düşüş serileri
- :func:`black_litterman` — kullanıcının görüşleriyle Black-Litterman ve görüşsüz maks. Sharpe karşılaştırması
- :func:`data_view` — normalize fiyatlar ve korelasyon

Tüm oranlar 0–1 kesir; seriler ``[["YYYY-MM-DD", değer], …]``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

from . import charts, insights, model_guide
from .backtest import backtest, fit_weights, summarize
from .data import bist, load_prices, to_returns
from .i18n import t as T
from .models import MODELS, supports_max_weight

TRADING_DAYS = 252
DEFAULT_MODELS = ["equal_weighted", "inverse_volatility", "min_variance", "max_sharpe", "risk_parity", "hrp", "min_cvar"]
MAX_SYMBOLS = 25
SUMMARY_KEYS = {"Yıllık getiri": "annual_return", "Yıllık volatilite": "annual_volatility", "Sharpe": "sharpe",
                "Sortino": "sortino", "Maks. düşüş": "max_drawdown", "CVaR %95": "cvar95"}


def _f(v):
    v = float(v)
    return v if math.isfinite(v) else None


def _points(s: pd.Series, every: int = 1) -> list[list]:
    s = s.dropna()
    if every > 1 and len(s) > every:
        s = pd.concat([s.iloc[::every], s.iloc[-1:]])
        s = s[~s.index.duplicated(keep="last")]
    return [[pd.Timestamp(d).strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in s.items()]


def label(ticker: str) -> str:
    """Ekranda: BIST hisselerinde .IS eki olmadan."""
    return ticker[:-3] if ticker.endswith(".IS") else ticker


# --- Veri ------------------------------------------------------------------------------------------------


def tickers_from(symbols: list[str] | None, bist_symbols: list[str] | None) -> list[str]:
    out = list(dict.fromkeys(bist(*[s.strip() for s in bist_symbols or [] if s.strip()])
                             + [s.strip() for s in symbols or [] if s.strip()]))
    if len(out) < 2:
        raise ValueError(T("En az 2 sembol girin."))
    if len(out) > MAX_SYMBOLS:
        raise ValueError(f"At most {MAX_SYMBOLS} symbols.")
    return out


def load(symbols, bist_symbols, start: str, end: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """(fiyatlar, günlük getiriler, bulunamayan semboller)."""
    tickers = tickers_from(symbols, bist_symbols)
    if pd.Timestamp(start) < pd.Timestamp("2000-01-01"):
        raise ValueError("start must be 2000-01-01 or later.")
    prices = load_prices(tickers, start=start, end=end)
    if prices.shape[1] < 2 or len(prices) < 30:
        raise ValueError(T("Bu ayarlar için veri kısa; başlangıç tarihini geriye alın veya eğitim penceresini küçültün."))
    missing = sorted(set(tickers) - set(prices.columns))
    return prices, to_returns(prices), missing


def check_models(models: list[str] | None) -> list[str]:
    models = list(dict.fromkeys(models or DEFAULT_MODELS))
    unknown = [m for m in models if m not in MODELS]
    if unknown:
        raise ValueError(f"Unknown models: {', '.join(unknown)}")
    return models


def model_list() -> list[dict]:
    return [{"key": k, "label": T(desc), "supports_max_weight": supports_max_weight(k),
             "default": k in DEFAULT_MODELS, "guide": model_guide.markdown(k)} for k, (_, desc) in MODELS.items()]


# --- Ağırlıklar ---------------------------------------------------------------------------------------------


def optimize(returns: pd.DataFrame, models: list[str], max_weight: float | None = None) -> dict:
    errors: dict[str, str] = {}
    weights = fit_weights(returns, models, on_error=lambda n, e: errors.__setitem__(n, str(e)), max_weight=max_weight)
    out: dict = {"errors": errors, "models": [], "weights": [], "frontier": [], "points": [], "assets": [],
                 "risk_contributions": [], "comments": {"overview": [], "models": {}}}
    if weights.empty:
        return out
    mu, cov = returns.mean() * TRADING_DAYS, returns.cov() * TRADING_DAYS
    baseline = insights.weight_metrics(pd.Series(1 / returns.shape[1], index=returns.columns), returns)
    for m in weights.columns:
        wm = insights.weight_metrics(weights[m], returns)
        out["models"].append({"key": m, "label": T(MODELS[m][1]), "annual_return": _f(wm.ann_ret),
                              "annual_volatility": _f(wm.ann_vol), "sharpe": _f(wm.sharpe),
                              "effective_assets": _f(wm.eff_n), "diversification_ratio": _f(wm.div_ratio),
                              "top_asset": label(wm.top), "top_weight": _f(wm.top_w),
                              "top_risk_asset": label(wm.top_risk), "top_risk_share": _f(wm.top_risk_share),
                              "max_weight_applied": max_weight is not None and supports_max_weight(m)})
        out["comments"]["models"][m] = insights.model_comment(m, weights[m], returns, baseline)
    out["weights"] = [{"asset": a, "label": label(a), **{m: _f(weights.loc[a, m]) for m in weights.columns}}
                      for a in weights.index]
    try:
        ef = charts.efficient_frontier(returns, max_weight=max_weight)
        out["frontier"] = [[_f(v), _f(r)] for v, r in zip(ef["vol"], ef["ret"])]
    except Exception as exc:  # noqa: BLE001
        errors["efficient_frontier"] = str(exc)
    for m in weights.columns:
        vol, ret = charts.portfolio_point(weights[m], returns)
        out["points"].append({"key": m, "label": T(MODELS[m][1]), "vol": _f(vol), "ret": _f(ret)})
    out["assets"] = [{"asset": a, "label": label(a), "vol": _f(math.sqrt(cov.loc[a, a])), "ret": _f(mu[a])}
                     for a in returns.columns]
    rc = charts.risk_contributions(weights, returns)
    out["risk_contributions"] = [{"asset": a, "label": label(a), **{m: _f(rc.loc[a, m]) for m in rc.columns}}
                                 for a in rc.index]
    out["comments"]["overview"] = insights.consensus(weights) + insights.asset_facts(returns)
    return out


# --- Backtest -------------------------------------------------------------------------------------------------


def run_backtest(returns: pd.DataFrame, models: list[str], train: int = 252, test: int = 21,
                 max_weight: float | None = None) -> dict:
    if not 63 <= train <= 756 or not 5 <= test <= 126:
        raise ValueError("train must be 63–756 and test 5–126 trading days.")
    if len(returns) <= train + test:
        raise ValueError(T("Bu ayarlar için veri kısa; başlangıç tarihini geriye alın veya eğitim penceresini küçültün."))
    errors: dict[str, str] = {}
    pop = backtest(returns, models, train_size=train, test_size=test,
                   on_error=lambda n, e: errors.__setitem__(n, str(e)), max_weight=max_weight)
    out: dict = {"errors": errors, "train": train, "test": test, "summary": [], "cumulative": [], "drawdowns": [],
                 "comments": []}
    if not len(pop):
        return out
    table = summarize(pop)
    for name, r in table.iterrows():
        out["summary"].append({"key": name, "label": T(MODELS[name][1]) if name in MODELS else name}
                              | {v: _f(r[k]) if k in r and pd.notna(r[k]) else None for k, v in SUMMARY_KEYS.items()})
    every = max(1, len(returns) // 400)
    for p in pop:
        rets = p.returns_df
        idx = (1 + rets).cumprod() * 100
        dd = idx / idx.cummax() - 1
        out["cumulative"].append({"key": p.name, "points": _points(idx, every)})
        out["drawdowns"].append({"key": p.name, "points": _points(dd, every)})
    out["comments"] = insights.backtest_comment(table.rename(columns=T))
    out["period"] = [pd.Timestamp(pop[0].observations[0]).strftime("%Y-%m-%d"),
                     pd.Timestamp(pop[0].observations[-1]).strftime("%Y-%m-%d")]
    return out


# --- Black-Litterman (kullanıcı görüşleriyle) ---------------------------------------------------------------------


def views_to_skfolio(views: list[dict], assets: list[str]) -> list[str]:
    """[{type: absolute|relative, asset, asset2?, annual_return_pct}] → skfolio görüş ifadeleri (günlük getiri)."""
    out = []
    by_label = {label(a): a for a in assets} | {a: a for a in assets}
    for v in views or []:
        a1 = by_label.get(str(v.get("asset", "")).strip().upper()) or by_label.get(str(v.get("asset", "")).strip())
        if a1 is None:
            raise ValueError(f"Unknown asset in view: {v.get('asset')!r}")
        daily = float(v["annual_return_pct"]) / 100 / TRADING_DAYS
        if v.get("type", "absolute") == "relative":
            a2 = by_label.get(str(v.get("asset2", "")).strip().upper()) or by_label.get(str(v.get("asset2", "")).strip())
            if a2 is None or a2 == a1:
                raise ValueError("A relative view needs a second, different asset.")
            out.append(f"{a1} - {a2} == {daily:.8f}")
        else:
            out.append(f"{a1} == {daily:.8f}")
    if not out:
        raise ValueError("Give at least one view.")
    return out


def black_litterman(returns: pd.DataFrame, views: list[dict], tau: float = 0.05) -> dict:
    from skfolio import RiskMeasure
    from skfolio.optimization import MeanRisk, ObjectiveFunction
    from skfolio.prior import BlackLitterman

    if not 0.001 <= tau <= 1:
        raise ValueError("tau must be between 0.001 and 1.")
    sk_views = views_to_skfolio(views, list(returns.columns))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        base = MeanRisk(objective_function=ObjectiveFunction.MAXIMIZE_RATIO, risk_measure=RiskMeasure.VARIANCE)
        bl = MeanRisk(objective_function=ObjectiveFunction.MAXIMIZE_RATIO, risk_measure=RiskMeasure.VARIANCE,
                      prior_estimator=BlackLitterman(views=sk_views, tau=tau))
        base.fit(returns)
        bl.fit(returns)
    assets = list(returns.columns)
    b, w = pd.Series(base.weights_, index=assets), pd.Series(bl.weights_, index=assets)
    return {"views": sk_views, "tau": tau,
            "weights": [{"asset": a, "label": label(a), "base": _f(b[a]), "black_litterman": _f(w[a])} for a in assets],
            "comments": insights.black_litterman_comment(b, w, sk_views),
            "guide": model_guide.markdown("black_litterman")}


# --- Veri görünümü ---------------------------------------------------------------------------------------------------


def data_view(prices: pd.DataFrame, returns: pd.DataFrame) -> dict:
    every = max(1, len(prices) // 400)
    norm = prices / prices.bfill().iloc[0] * 100
    corr = returns.corr()
    return {"prices": [{"asset": a, "label": label(a), "points": _points(norm[a], every)} for a in prices.columns],
            "correlation": {"assets": [label(a) for a in corr.index],
                            "matrix": [[round(float(v), 4) for v in row] for row in corr.values]},
            "period": [prices.index[0].strftime("%Y-%m-%d"), prices.index[-1].strftime("%Y-%m-%d")],
            "days": int(len(prices)), "asset_count": int(prices.shape[1])}
