import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from portfolio_models import api, store
from portfolio_models import model_portfolios as mp

IDX = pd.bdate_range("2025-06-02", "2026-11-20")


def market(positions, years=1):
    rng = np.random.default_rng(3)
    cols = {t: 100 * np.cumprod(1 + rng.normal(0.0004, s, len(IDX)))
            for t, s in (("VOO", 0.01), ("QQQ", 0.02), ("GLD", 0.008), ("XU100.IS", 0.015), ("^GSPC", 0.01),
                         ("^GDAXI", 0.012), ("GC=F", 0.009))}
    cols |= {"USDTRY=X": np.linspace(38, 42, len(IDX)), "EURTRY=X": np.linspace(44, 48, len(IDX))}
    cur = {t: "USD" for t in cols} | {"XU100.IS": "TRY", "USDTRY=X": "TRY", "EURTRY=X": "TRY", "^GDAXI": "EUR"}
    return pd.DataFrame(cols, index=IDX), cur


@pytest.fixture
def client(tmp_path):
    engine = store.make_engine(f"sqlite:///{tmp_path / 'p.db'}")
    for name, h, d in (("Acme · Global ETF", [("VOO", 60), ("GLD", 40)], "2026-01-05"),
                       ("Büyüme Şirketi · Teknoloji", [("QQQ", 70), ("VOO", 30)], "2026-03-02")):
        cfg, _ = mp.add_revision(None, d, [{"kind": "yahoo", "symbol": s, "weight": w} for s, w in h],
                                 provider=name.split(" · ")[0], country="US", source_url="https://example.com")
        if name.startswith("Acme"):
            cfg, _ = mp.add_revision(cfg, "2026-07-01", [{"kind": "yahoo", "symbol": "VOO", "weight": 50},
                                                         {"kind": "yahoo", "symbol": "QQQ", "weight": 30},
                                                         {"kind": "cash", "symbol": "USD", "weight": 20}])
        store.save_portfolio(engine, api.LOCAL_USER, name, cfg, kind=mp.STORE_KIND)
    arc = api.Archive(engine=engine, market=market)
    return TestClient(api.create_app(arc, background=False))


def test_slugify():
    assert api.slugify("Büyüme Şirketi · Teknoloji") == "buyume-sirketi-teknoloji"
    assert api.slugify("İŞ Yatırım") == "is-yatirim"


def test_meta_and_list(client):
    m = client.get("/api/meta").json()
    assert m["example"] is False and m["count"] == 2 and m["price_date"] == "2026-11-20"
    assert {r["key"] for r in m["rankings"]} == set(api.ma.RANKINGS)
    assert "yatırım tavsiyesi" in m["disclaimer"]
    assert "investment advice" in client.get("/api/meta?lang=en").json()["disclaimer"]
    items = client.get("/api/portfolios?currency=USD").json()["items"]
    assert [i["slug"] for i in items] == ["acme-global-etf", "buyume-sirketi-teknoloji"]
    acme = items[0]
    assert acme["revision_count"] == 2 and acme["asset_count"] == 3 and acme["source_url"]
    assert acme["sparkline"][0] == 100 and len(acme["sparkline"]) > 10
    assert -1 < acme["returns"]["since_inception"] < 5


def test_leaderboard(client):
    r = client.get("/api/leaderboard?by=volatility&currency=EUR").json()
    assert r["field"] == "vol" and r["higher_is_better"] is False
    vols = [i["value"] for i in r["items"]]
    assert vols == sorted(vols) and [i["rank"] for i in r["items"]] == [1, 2]
    r = client.get("/api/leaderboard?by=alpha&window=1y&benchmark=S%26P%20500").json()
    assert r["benchmark"] == "S&P 500"
    assert r["items"] == []  # ikisi de 1 yıldan yeni
    assert client.get("/api/leaderboard?by=nope").status_code == 400
    assert client.get("/api/leaderboard?currency=JPY").status_code == 400


def test_detail_and_analysis(client):
    d = client.get("/api/portfolios/acme-global-etf").json()
    assert [h["asset"] for h in d["holdings"]] == ["VOO", "QQQ", "Nakit USD"]
    assert d["holdings"][2]["label"] == "Nakit USD" and d["holdings"][0]["weight"] == 0.5
    assert [r["date"] for r in d["revisions"]] == ["2026-07-01", "2026-01-05"]
    assert d["series"]["portfolio"][0] == ["2026-01-05", 100.0]
    assert d["series"]["benchmark"][0][1] == 100.0
    assert d["scorecard"]["beta"] is not None
    assert client.get("/api/portfolios/yok").status_code == 404

    a = client.get("/api/portfolios/acme-global-etf/analysis?currency=USD").json()
    assert a["revision"] == "2026-07-01" and a["revisions"] == ["2026-07-01", "2026-01-05"]
    keys = [p["key"] for p in a["portfolios"]]
    assert keys[0] == "firm" and "hrp" in keys
    cash = next(w for w in a["weights"] if w["asset"] == "Nakit USD")
    assert all(cash[k] == pytest.approx(0.2) for k in keys)  # modeller nakde dokunmaz
    assert {p["key"] for p in a["paths"]} >= {"firm", "equal_weighted", "BIST100"}
    assert a["closest_model"]["key"] in keys
    assert set(a["decomposition"]) == {"selection", "weighting", "total_vs_benchmark"}
    assert "black_litterman" in keys
    ch = a["charts"]
    assert len(ch["frontier"]) > 5 and {p["key"] for p in ch["points"]} >= {"firm", "black_litterman"}
    assert {x["asset"] for x in ch["assets"]} == {"VOO", "QQQ", "Nakit USD"}
    assert next(x for x in ch["assets"] if x["asset"] == "VOO")["implied_return"] is not None
    assert ch["correlation"]["assets"] == ["VOO", "QQQ"] and ch["correlation"]["matrix"][0][0] == 1.0
    assert set(ch["risk_contributions"][0]) >= {"asset", "label", "firm", "black_litterman"}
    old = client.get("/api/portfolios/acme-global-etf/analysis?revision=2026-01-05&benchmark=none").json()
    assert old["revision"] == "2026-01-05" and old["benchmark"] is None
    assert client.get("/api/portfolios/acme-global-etf/analysis?revision=2020-01-01").status_code == 400


def test_compare_and_cache(client):
    r = client.get("/api/compare?slugs=acme-global-etf,buyume-sirketi-teknoloji").json()
    names = [i["name"] for i in r["items"]]
    assert names[:2] == ["Acme · Global ETF", "Büyüme Şirketi · Teknoloji"] and r["items"][2]["is_benchmark"]
    arc = client.app.state.archive
    v = arc.version
    assert arc.refresh() is False and arc.version == v  # değişiklik yoksa fiyat yeniden çekilmez
    assert client.get("/api/compare").status_code == 400


def test_examples_when_empty(tmp_path):
    arc = api.Archive(engine=store.make_engine(f"sqlite:///{tmp_path / 'e.db'}"), market=market)
    c = TestClient(api.create_app(arc, background=False))
    m = c.get("/api/meta").json()
    assert m["example"] is True and m["count"] == 3


def test_next_refresh():
    from datetime import datetime, timezone

    assert api._next_refresh(datetime(2026, 11, 26, 10, tzinfo=timezone.utc)).hour == 15
    assert api._next_refresh(datetime(2026, 11, 26, 16, tzinfo=timezone.utc)).hour == 21
    nxt = api._next_refresh(datetime(2026, 11, 26, 22, tzinfo=timezone.utc))
    assert (nxt.day, nxt.hour) == (27, 15)


def test_analysis_overview(client):
    r = client.get("/api/analysis?currency=USD").json()
    assert [i["slug"] for i in r["items"]] == ["acme-global-etf", "buyume-sirketi-teknoloji"] and not r["failed"]
    it = r["items"][0]
    assert it["revision"] == "2026-07-01" and 1 <= it["firm_rank_by_sharpe"] <= it["ranked_out_of"]
    assert {m["key"] for m in it["models"]} >= {"equal_weighted", "hrp"} and "BIST100" not in {m["key"] for m in
                                                                                                it["models"]}
    assert it["best_model"]["sharpe"] == max(m["sharpe"] for m in it["models"] if m["sharpe"] is not None)
    keys = {m["key"] for m in r["models"]}
    assert "min_variance" in keys
    mv = next(m for m in r["models"] if m["key"] == "min_variance")
    assert mv["portfolios"] == 2 and 0 <= mv["beat_firm_sharpe"] <= 1
    assert sum(m["closest_count"] for m in r["models"]) == 2
    assert 0 <= r["firms"]["beat_all_models_sharpe"] <= 1
    # tekil analiz aynı önbelleği kullanır, sonuçlar tutarlı
    a = client.get("/api/portfolios/acme-global-etf/analysis?currency=USD").json()
    assert a["closest_model"]["key"] == it["closest_model"]["key"]
