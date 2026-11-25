from datetime import date

import pandas as pd
import pytest

from portfolio_models import model_portfolios as mp


def prices():
    idx = pd.bdate_range("2026-01-05", periods=6)
    return pd.DataFrame({"A": [10, 11, 12, 12, 12, 13.2], "B": [20, 20, 20, 10, 10, 10], "Nakit TRY": 1.0},
                        index=idx, dtype=float)


def cfg(*revs):
    return {"revisions": [{"date": d, "holdings": h} for d, h in revs]}


A = {"kind": "yahoo", "symbol": "A"}
B = {"kind": "yahoo", "symbol": "B"}


def test_validate_merges_scales_and_rejects():
    rows, warns = mp.validate_holdings([{**A, "weight": 30}, {**A, "weight": 30}, {"kind": "bist", "symbol": "thyao.is",
                                                                                  "weight": 20}, {**B, "weight": 0}])
    assert {r["symbol"]: r["weight"] for r in rows} == {"A": 75.0, "THYAO": 25.0}
    assert warns
    with pytest.raises(ValueError):
        mp.validate_holdings([{"kind": "spaceship", "symbol": "X", "weight": 10}])
    with pytest.raises(ValueError):
        mp.validate_holdings([])


def test_index_buy_and_hold_then_rebalance():
    c = cfg(("2026-01-05", [{**A, "weight": 50}, {**B, "weight": 50}]),
            ("2026-01-08", [{**A, "weight": 100}]))
    s, w = mp.index_series(c, prices())
    assert not w
    # 05→07: 0.5*A/10 + 0.5*B/20 → 07: 0.5*1.2 + 0.5*1 = 110
    assert s.loc["2026-01-07"] == pytest.approx(110)
    # 08: B yarıya düştü, A 12 → 0.5*1.2 + 0.5*0.5 = 85; sonra tamamen A: 85 * 13.2/12
    assert s.loc["2026-01-08"] == pytest.approx(85)
    assert s.iloc[-1] == pytest.approx(85 * 1.1)
    assert s.index.is_unique and s.iloc[0] == 100


def test_missing_asset_reweighted_with_warning():
    c = cfg(("2026-01-05", [{**A, "weight": 50}, {"kind": "yahoo", "symbol": "ZZZ", "weight": 50}]))
    s, w = mp.index_series(c, prices())
    assert s.iloc[-1] == pytest.approx(132) and w


def test_add_revision_replaces_same_day_and_rejects_future():
    c, _ = mp.add_revision(None, "2026-01-05", [{**A, "weight": 100}], provider="X", country="TR")
    c, _ = mp.add_revision(c, "2026-02-01", [{**B, "weight": 100}])
    c, _ = mp.add_revision(c, "2026-01-05", [{**B, "weight": 100}])
    assert [r["date"] for r in c["revisions"]] == ["2026-01-05", "2026-02-01"] and c["provider"] == "X"
    assert mp.current_holdings(c)[0]["symbol"] == "B"
    with pytest.raises(ValueError):
        mp.add_revision(c, "2999-01-01", [{**A, "weight": 100}])


def test_metrics_and_compare_with_benchmark():
    p = prices().rename(columns={"B": "XU100.IS"})
    c = cfg(("2026-01-05", [{**A, "weight": 100}]))
    comp = mp.compare_models({"M": c}, p, p, "TRY", benchmarks=["BIST100"])
    names = [r["name"] for r in comp.table]
    assert names == ["M", "BIST100"]
    m = comp.table[0]
    assert m["total"] == pytest.approx(0.32) and m["1G"] == pytest.approx(0.1)
    assert m["max_dd"] == pytest.approx(0) and comp.table[1]["max_dd"] == pytest.approx(-0.5)
    assert comp.price_date == date(2026, 1, 12)


def test_usd_view_divides_by_fx():
    p = prices()
    closes = pd.DataFrame({"USDTRY=X": [40.0] * 5 + [44.0]}, index=p.index)
    comp = mp.compare_models({"M": cfg(("2026-01-05", [{**A, "weight": 100}]))}, p, closes, "USD")
    assert comp.table[0]["total"] == pytest.approx(1.32 / 1.1 - 1)


def test_examples_are_valid_and_store_roundtrip(tmp_path):
    from portfolio_models import store

    eng = store.make_engine(f"sqlite:///{tmp_path / 'x.db'}")
    for name, c in mp.examples(date(2026, 11, 25)).items():
        for r in c["revisions"]:
            mp.validate_holdings(r["holdings"])
        store.save_portfolio(eng, "u@x.com", name, c, kind=mp.STORE_KIND)
    assert len(mp.load_all(eng, "u@x.com")) == 3 and mp.load_all(eng, "v@x.com") == {}
