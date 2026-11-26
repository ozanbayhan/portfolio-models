import numpy as np
import pandas as pd
import pytest

from portfolio_models import model_analysis as ma


def market(n=500, seed=1):
    """Sentetik fiyatlar: A sakin, B oynak, C orta; kıyas (BIST100 = XU100.IS) üçünün ortalaması."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    r = pd.DataFrame({"A": rng.normal(0.0006, 0.005, n), "B": rng.normal(0.0004, 0.03, n),
                      "C": rng.normal(0.0003, 0.015, n)}, index=idx)
    p = (1 + r).cumprod() * 100
    p["XU100.IS"] = p[["A", "B", "C"]].mean(axis=1)
    p["Nakit TRY"] = 1.0
    return p


def holding(sym, w):
    return {"kind": "cash", "symbol": "TRY", "weight": w} if sym == "cash" else {"kind": "yahoo", "symbol": sym,
                                                                                 "weight": w}


def cfg(*revs):
    return {"provider": "Test", "revisions": [{"date": d, "holdings": [holding(s, w) for s, w in h]}
                                              for d, h in revs]}


def test_fit_models_keeps_cash_sleeve_and_sums_to_one():
    p = market()
    w = pd.Series({"A": 0.3, "B": 0.5, "Nakit TRY": 0.2})
    rets = ma._window_returns(p, list(w.index), p.index[300])
    table, notes = ma.fit_models(w, rets, ["equal_weighted", "min_variance"])
    assert set(table.columns) == {ma.ACTUAL, "equal_weighted", "min_variance"}
    assert table.sum().round(6).eq(1).all()
    assert (table.loc["Nakit TRY"] == 0.2).all()  # modeller nakde dokunmaz
    assert table.loc["A", "equal_weighted"] == pytest.approx(0.4)
    assert table.loc["A", "min_variance"] > table.loc["B", "min_variance"]  # sakin varlık ağır basar
    assert notes  # nakit sabit dilim notu


def test_analyze_no_lookahead_and_decomposition():
    p = market()
    c = cfg((f"{p.index[300]:%Y-%m-%d}", [("A", 20), ("B", 60), ("C", 20)]),
            (f"{p.index[400]:%Y-%m-%d}", [("A", 50), ("B", 50)]))
    a = ma.analyze(c, p, models=["equal_weighted", "min_variance", "hrp"])
    assert a.as_of == f"{p.index[400]:%Y-%m-%d}"
    assert {ma.ACTUAL, "equal_weighted", "min_variance", "hrp", "BIST100"} <= set(a.paths)
    for s in a.paths.values():
        assert s.index[0] == p.index[300] and s.iloc[0] == pytest.approx(100)
    # model ağırlıkları yalnızca revizyondan önceki veriye bakar: sonradan gelen fiyatlar sonucu değiştirmez
    p2 = p.copy()
    p2.loc[p.index[401]:, "B"] *= 3
    a2 = ma.analyze(c, p2, models=["min_variance"])
    assert a2.weights["min_variance"].round(8).equals(a.weights["min_variance"].round(8))
    d = a.decomposition
    assert d["selection"] + d["weighting"] == pytest.approx(d["total_vs_benchmark"])
    assert a.profiles[ma.ACTUAL].distance == 0
    assert a.closest in {"equal_weighted", "min_variance", "hrp"}
    assert a.risk_contrib.sum() == pytest.approx(1)


def test_scorecard_against_itself_and_hit_rate():
    p = market()
    s = p["XU100.IS"] / p["XU100.IS"].iloc[0] * 100
    sc = ma.scorecard(s, s)
    assert sc["alpha"] == pytest.approx(0, abs=1e-9) and sc["beta"] == pytest.approx(1)
    assert sc["monthly_win"] == 0 and sc["sharpe"] is not None
    # tek varlık A, kıyası açık ara geçiyorsa isabet 1
    p.loc[p.index[200]:, "A"] = np.linspace(1, 5, len(p) - 200) * 100
    c = cfg((f"{p.index[200]:%Y-%m-%d}", [("A", 90), ("cash", 10)]))
    assert ma.hit_rate(c, p, "XU100.IS") == 1


def test_leaderboard_and_rank():
    p = market()
    good = cfg((f"{p.index[100]:%Y-%m-%d}", [("A", 100)]))
    risky = cfg((f"{p.index[100]:%Y-%m-%d}", [("B", 100)]))
    late = cfg((f"{p.index[480]:%Y-%m-%d}", [("C", 100)]))
    lb = ma.leaderboard({"good": good, "risky": risky, "late": late}, p)
    assert set(lb.index) == {"good", "risky", "late"}
    assert ma.rank(lb, "volatility").index[0] in {"good", "late"}
    assert ma.rank(lb, "volatility").loc["risky", "vol"] == lb["vol"].max()
    # pencere: geç başlayan portföy 1 yıllık kıyasa girmez
    assert "late" not in ma.leaderboard({"good": good, "late": late}, p, window=365).index


def test_in_ccy():
    p = market(50)
    closes = pd.DataFrame({"USDTRY=X": 40.0}, index=p.index)
    usd = ma.in_ccy(p, closes, "USD")
    assert usd["A"].iloc[0] == pytest.approx(p["A"].iloc[0] / 40)
    with pytest.raises(ValueError):
        ma.in_ccy(p, closes, "EUR")


def test_black_litterman_implied_and_posterior():
    p = market()
    w = pd.Series({"A": 0.5, "B": 0.2, "C": 0.3})
    rets = ma._window_returns(p, list(w.index), p.index[300])
    pi = ma.implied_returns(w, rets)
    cov = rets.cov() * 252
    assert pi.values == pytest.approx((ma.RISK_AVERSION * cov @ w).values)
    # kurumun ağırlıkları π altında maks. Sharpe portföyü olmalı (ters optimizasyonun tanımı)
    assert ma.max_sharpe_weights(pi, cov).values == pytest.approx(w.values, abs=0.02)
    mu = ma.bl_posterior(w, rets)
    q = rets.mean() * 252
    lo, hi = pd.concat([pi, q], axis=1).min(axis=1), pd.concat([pi, q], axis=1).max(axis=1)
    assert ((mu >= lo - 0.05) & (mu <= hi + 0.05)).all()  # sonsal, önsel ile görüş arasında
    bw = ma.black_litterman_weights(w, rets)
    assert bw.sum() == pytest.approx(1) and (bw >= 0).all()


def test_analysis_has_black_litterman_and_chart_data():
    p = market()
    c = cfg((f"{p.index[300]:%Y-%m-%d}", [("A", 30), ("B", 40), ("C", 20), ("cash", 10)]))
    a = ma.analyze(c, p)
    assert ma.BLACK_LITTERMAN in a.weights and a.weights[ma.BLACK_LITTERMAN].sum() == pytest.approx(1)
    assert a.weights.loc["Nakit TRY", ma.BLACK_LITTERMAN] == pytest.approx(0.1)
    assert {"vol", "past_return", "implied_return", "bl_return"} <= set(a.assets.columns)
    assert list(a.correlation.index) == ["A", "B", "C"] and len(a.frontier) > 5
    assert a.risk_contrib_all.sum().round(6).eq(1).all()
    assert ma.model_desc(ma.BLACK_LITTERMAN).startswith("Black-Litterman") and ma.model_desc("hrp")
