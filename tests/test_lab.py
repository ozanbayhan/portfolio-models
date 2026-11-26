import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from portfolio_models import api, lab, store


def fake_prices(tickers, start=None, end=None, **kw):
    rng = np.random.default_rng(len(tickers))
    idx = pd.bdate_range("2023-01-02", "2026-11-20")
    vols = {"THYAO.IS": 0.02, "ASELS.IS": 0.025, "VOO": 0.01, "GLD": 0.008, "QQQ": 0.015}
    return pd.DataFrame({t: 100 * np.cumprod(1 + rng.normal(0.0004, vols.get(t, 0.012), len(idx)))
                         for t in tickers if t != "NOPE"}, index=idx)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "load_prices", fake_prices)
    api._lab_cache.clear()
    arc = api.Archive(engine=store.make_engine(f"sqlite:///{tmp_path / 'p.db'}"))
    return TestClient(api.create_app(arc, background=False))


BODY = {"bist_symbols": ["THYAO", "ASELS"], "symbols": ["VOO", "GLD", "NOPE"], "start": "2023-01-01",
        "models": ["equal_weighted", "min_variance", "hrp", "max_sharpe"]}


def test_models_list(client):
    r = client.get("/api/lab/models?lang=en").json()
    assert len(r["models"]) == len(lab.MODELS) and set(r["defaults"]) <= {m["key"] for m in r["models"]}
    hrp = next(m for m in r["models"] if m["key"] == "hrp")
    assert hrp["guide"] and "Hierarchical" in hrp["label"]


def test_optimize(client):
    r = client.post("/api/lab/optimize", json=BODY | {"max_weight_pct": 40})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["missing_symbols"] == ["NOPE"]
    res = d["result"]
    assert [m["key"] for m in res["models"]] == BODY["models"] and not res["errors"]
    for m in BODY["models"]:
        assert sum(w[m] for w in res["weights"]) == pytest.approx(1, abs=1e-6)
    assert max(w["min_variance"] for w in res["weights"]) <= 0.4 + 1e-6  # üst sınır
    assert {w["label"] for w in res["weights"]} == {"THYAO", "ASELS", "VOO", "GLD"}
    assert len(res["frontier"]) > 5 and len(res["points"]) == 4 and len(res["assets"]) == 4
    assert res["comments"]["overview"] and set(res["comments"]["models"]) == set(BODY["models"])
    assert d["data"]["correlation"]["assets"] == ["THYAO", "ASELS", "VOO", "GLD"]
    assert d["data"]["prices"][0]["points"][0][1] == 100.0


def test_backtest(client):
    r = client.post("/api/lab/backtest", json=BODY | {"train": 252, "test": 21})
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert {s["key"] for s in res["summary"]} == set(BODY["models"])
    sh = [s["sharpe"] for s in res["summary"]]
    assert sh == sorted(sh, reverse=True)
    assert res["cumulative"][0]["points"][0][1] > 0 and res["comments"]
    assert all(p[1] <= 0 for p in res["drawdowns"][0]["points"])
    assert client.post("/api/lab/backtest", json=BODY | {"train": 10}).status_code == 400


def test_black_litterman(client):
    views = [{"type": "absolute", "asset": "THYAO", "annual_return_pct": 60},
             {"type": "relative", "asset": "VOO", "asset2": "GLD", "annual_return_pct": 5}]
    r = client.post("/api/lab/black-litterman", json=BODY | {"views": views, "tau": 0.1})
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    thy = next(w for w in res["weights"] if w["label"] == "THYAO")
    assert thy["black_litterman"] >= thy["base"] - 1e-6  # olumlu görüş ağırlığı azaltmaz
    assert len(res["views"]) == 2 and res["comments"]
    bad = client.post("/api/lab/black-litterman", json=BODY | {"views": [{"asset": "XYZ", "annual_return_pct": 5}]})
    assert bad.status_code == 400


def test_validation(client):
    assert client.post("/api/lab/optimize", json={"symbols": ["VOO"]}).status_code == 400
    assert client.post("/api/lab/optimize", json=BODY | {"models": ["nope"]}).status_code == 400
    assert client.post("/api/lab/optimize", content=b"[1,2]").status_code == 400
    many = {"symbols": [f"S{i}" for i in range(30)]}
    assert client.post("/api/lab/optimize", json=many).status_code == 400
    assert client.get("/api/lab/optimize").status_code == 405
