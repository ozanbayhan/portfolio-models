"""Grafikler: etkin sınır, risk katkısı ve ortak Plotly teması.

Hesaplama fonksiyonları (efficient_frontier, risk_contributions) Streamlit'ten bağımsızdır ve test edilir.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

TRADING_DAYS = 252

# Erişilebilir, birbirinden ayırt edilebilir kategorik palet (vurgu rengi: indigo)
PALETTE = ["#4F46E5", "#0EA5E9", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316",
           "#64748B", "#EC4899", "#84CC16", "#06B6D4"]
ACCENT = PALETTE[0]


def register_template() -> None:
    """Uygulamanın tüm grafiklerinde kullanılan sade Plotly teması."""
    tmpl = go.layout.Template(pio.templates["plotly_white"])
    tmpl.layout.colorway = PALETTE
    tmpl.layout.font = dict(family="Inter, -apple-system, Segoe UI, Roboto, sans-serif", size=13, color="#0F172A")
    tmpl.layout.title = dict(font=dict(size=15))
    tmpl.layout.margin = dict(t=40, b=30, l=10, r=10)
    tmpl.layout.xaxis = dict(gridcolor="#EEF2F7", zerolinecolor="#E2E8F0", linecolor="#E2E8F0")
    tmpl.layout.yaxis = dict(gridcolor="#EEF2F7", zerolinecolor="#E2E8F0", linecolor="#E2E8F0")
    tmpl.layout.legend = dict(bgcolor="rgba(0,0,0,0)")
    tmpl.layout.hoverlabel = dict(font=dict(family="Inter, sans-serif"))
    pio.templates["pm"] = tmpl
    pio.templates.default = "pm"


def _moments(returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    return returns.mean() * TRADING_DAYS, returns.cov() * TRADING_DAYS


def portfolio_point(w: pd.Series, returns: pd.DataFrame) -> tuple[float, float]:
    """(yıllık oynaklık, yıllık getiri)."""
    mu, cov = _moments(returns)
    w = w.reindex(returns.columns).fillna(0.0)
    return float(np.sqrt(max(float(w @ cov @ w), 0.0))), float(w @ mu)


def efficient_frontier(returns: pd.DataFrame, size: int = 30, max_weight: float | None = None) -> pd.DataFrame:
    """Markowitz etkin sınırı (açığa satış yok): sütunlar 'vol', 'ret'."""
    from skfolio.optimization import MeanRisk

    params = {"efficient_frontier_size": size}
    if max_weight is not None and max_weight < 1:
        params["max_weights"] = max_weight
    model = MeanRisk(**params).fit(returns)
    w = np.atleast_2d(model.weights_)
    mu, cov = _moments(returns)
    vols = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", w, cov.values, w), 0))
    rets = w @ mu.values
    df = pd.DataFrame({"vol": vols, "ret": rets}).sort_values("vol")
    return df.drop_duplicates().reset_index(drop=True)


def risk_contributions(weights: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    """Her modelin (sütun) toplam riskinin varlıklara (satır) dağılımı; sütun toplamı 1."""
    _, cov = _moments(returns)
    out = {}
    for model in weights.columns:
        w = weights[model].reindex(returns.columns).fillna(0.0)
        var = float(w @ cov @ w)
        out[model] = (w * (cov @ w)) / var if var > 0 else w * 0
    return pd.DataFrame(out)


def frontier_figure(returns: pd.DataFrame, weights: pd.DataFrame, labels: dict[str, str],
                    max_weight: float | None = None) -> go.Figure:
    """Etkin sınır eğrisi + her modelin ve her varlığın konumu. labels: eksen/lejant metinleri (çevrilmiş)."""
    ef = efficient_frontier(returns, max_weight=max_weight)
    mu, cov = _moments(returns)
    fig = go.Figure()
    fig.add_scatter(x=ef["vol"], y=ef["ret"], mode="lines", name=labels["frontier"],
                    line=dict(color="#CBD5E1", width=4), hoverinfo="skip")
    fig.add_scatter(x=np.sqrt(np.diag(cov)), y=mu.values, mode="markers+text", name=labels["assets"],
                    text=list(returns.columns), textposition="top center", textfont=dict(size=11, color="#64748B"),
                    marker=dict(size=9, color="#94A3B8", symbol="diamond"),
                    hovertemplate="%{text}<br>σ %{x:.1%} · μ %{y:.1%}<extra></extra>")
    for i, model in enumerate(weights.columns):
        vol, ret = portfolio_point(weights[model], returns)
        fig.add_scatter(x=[vol], y=[ret], mode="markers", name=model,
                        marker=dict(size=13, color=PALETTE[i % len(PALETTE)], line=dict(width=2, color="white")),
                        hovertemplate=f"<b>{model}</b><br>σ %{{x:.1%}} · μ %{{y:.1%}}<extra></extra>")
    fig.update_layout(height=460, xaxis_title=labels["x"], yaxis_title=labels["y"],
                      xaxis_tickformat=".0%", yaxis_tickformat=".0%", legend=dict(orientation="h", y=-0.18))
    return fig


def risk_figure(weights: pd.DataFrame, returns: pd.DataFrame, labels: dict[str, str]) -> go.Figure:
    rc = risk_contributions(weights, returns)
    fig = go.Figure()
    for i, asset in enumerate(rc.index):
        fig.add_bar(x=list(rc.columns), y=rc.loc[asset].values, name=str(asset),
                    marker_color=PALETTE[i % len(PALETTE)],
                    hovertemplate=f"{asset}: %{{y:.1%}}<extra>%{{x}}</extra>")
    fig.update_layout(barmode="stack", height=420, yaxis_tickformat=".0%", yaxis_title=labels["y"],
                      legend=dict(orientation="h", y=-0.18))
    return fig
