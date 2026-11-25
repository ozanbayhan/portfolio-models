import asyncio

import pandas as pd
import pytest

from portfolio_models import mcp_server as m
from portfolio_models import report


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DATABASE_URL", f"sqlite:///{tmp_path / 'p.db'}")
    monkeypatch.delenv("PM_MCP_USER", raising=False)
    monkeypatch.delenv("PM_MCP_READ_ONLY", raising=False)


def fake_market(positions, years=1):
    idx = pd.bdate_range("2026-11-02", "2026-11-20")
    closes = pd.DataFrame({"THYAO.IS": [300.0] * 10 + [330.0] * 5, "VOO": 500.0, "USDTRY=X": 40.0}, index=idx)
    return closes, {"THYAO.IS": "TRY", "VOO": "USD", "USDTRY=X": "TRY"}


def test_add_update_remove_position():
    r = m.add_position("bist", 100, "thyao", avg_cost=250)
    assert r["portfolio"] == m.DEFAULT_PORTFOLIO and r["action"] == "added"
    m.add_position("yahoo", 2, "VOO")  # ETF
    m.add_position("gold", 10)
    r = m.add_position("bist", 150, "THYAO.IS")  # aynı varlık: güncellenir, çoğalmaz
    assert r["action"] == "updated"
    syms = {(p["kind"], p["symbol"]) for p in r["positions"]}
    assert syms == {("bist", "THYAO.IS"), ("yahoo", "VOO"), ("gold", None)}
    r = m.remove_position("gold")
    assert r["removed"] == 1 and len(r["positions"]) == 2
    with pytest.raises(ValueError):
        m.remove_position("ASELS")


def test_portfolio_visible_to_web_local_user_and_valued(monkeypatch):
    m.add_position("bist", 100, "THYAO")
    m.add_position("yahoo", 2, "VOO")
    m.add_transaction("deposit", "cash", "2026-11-03", symbol="TRY", amount=1000)
    assert [p["name"] for p in m.list_portfolios()] == [m.DEFAULT_PORTFOLIO]
    orig = report.compute_summary
    monkeypatch.setattr(report, "compute_summary", lambda *a, **k: orig(*a, market=fake_market, **k))
    out = m.get_portfolio()
    v = out["valuation"]
    assert v["total_try"] == pytest.approx(100 * 330 + 2 * 500 * 40 + 1000)
    assert {h["asset"] for h in v["holdings"]} == {"THYAO", "VOO", "Nakit TRY"}
    assert out["transactions"][0]["side"] == "deposit"


def test_invalid_transaction_rejected():
    with pytest.raises(ValueError):
        m.add_transaction("buy", "bist", "2026-11-03", symbol="THYAO")  # adet/fiyat yok
    with pytest.raises(ValueError):
        m.add_position("bist", 0, "THYAO")


def test_user_isolation(monkeypatch):
    m.add_position("bist", 1, "THYAO")
    monkeypatch.setenv("PM_MCP_USER", "other@example.com")
    assert m.list_portfolios() == []


def test_server_tools_and_read_only():
    async def names(ro):
        return {t.name for t in await m.build_server(read_only=ro).list_tools()}

    full = asyncio.run(names(False))
    assert {"optimize_portfolio", "get_portfolio", "add_position", "remove_position", "add_transaction"} <= full
    ro = asyncio.run(names(True))
    assert "add_position" not in ro and "get_inflation" in ro


def test_list_models_in_english():
    ms = m.list_models()
    assert len(ms) == 24 and all(x["description"] for x in ms)


def test_model_portfolio_tools(monkeypatch):
    from portfolio_models import model_portfolios as mp

    r = m.save_model_portfolio("Acme · Hisse", [{"kind": "bist", "symbol": "THYAO", "weight": 60},
                                                {"kind": "yahoo", "symbol": "VOO", "weight": 40}],
                               as_of="2026-11-03", provider="Acme", country="tr", source_url="https://example.com")
    assert r["action"] == "created" and r["country"] == "TR"
    r = m.save_model_portfolio("Acme · Hisse", [{"kind": "bist", "symbol": "THYAO", "weight": 100}], as_of="2026-11-12")
    assert r["action"] == "revision added" and r["revision_count"] == 2
    assert [x["name"] for x in m.list_model_portfolios()] == ["Acme · Hisse"]
    assert len(m.get_model_portfolio("Acme · Hisse")["revisions"]) == 2

    orig = mp.market_for
    monkeypatch.setattr(mp, "market_for", lambda c, b, **k: orig(c, b, market=fake_market, **k))
    out = m.compare_model_portfolios(benchmarks=[])
    row = out["results"][0]
    # 03.11→12.11: THYAO 300→300, VOO sabit → 100; sonra %100 THYAO 300→330: +10%
    assert row["return_since_inception_pct"] == pytest.approx(10.0)
    assert out["price_date"] == "2026-11-20"
    with pytest.raises(ValueError):
        m.compare_model_portfolios(names=["yok"])
    assert m.delete_model_portfolio("Acme · Hisse") == {"deleted": "Acme · Hisse"}
    assert m.list_model_portfolios() == []


def test_model_portfolio_tools_registered():
    async def names(ro):
        return {t.name for t in await m.build_server(read_only=ro).list_tools()}

    assert {"save_model_portfolio", "compare_model_portfolios", "delete_model_portfolio"} <= asyncio.run(names(False))
    assert "save_model_portfolio" not in asyncio.run(names(True))


def test_model_portfolio_archive_rules():
    h = [{"kind": "yahoo", "symbol": "VOO", "weight": 100}]
    with pytest.raises(ValueError, match="source_url"):
        m.save_model_portfolio("X", h, as_of="2026-11-03")
    with pytest.raises(ValueError, match="source_url"):
        m.save_model_portfolio("X", h, as_of="2026-11-03", source_url="file:///etc/passwd")
    with pytest.raises(ValueError, match="280"):
        m.save_model_portfolio("X", h, as_of="2026-11-03", source_url="https://example.com", note="x" * 281)
    assert m.list_model_portfolios() == []


def test_rank_and_analyze_tools(monkeypatch):
    import numpy as np
    from portfolio_models import model_portfolios as mp

    idx = pd.bdate_range("2025-06-02", "2026-11-20")
    rng = np.random.default_rng(0)

    def market(positions, years=1):
        cols = {t: 100 * np.cumprod(1 + rng.normal(0.0004, s, len(idx)))
                for t, s in (("VOO", 0.01), ("QQQ", 0.02), ("GLD", 0.008), ("XU100.IS", 0.015))}
        cols |= {"USDTRY=X": 40.0, "EURTRY=X": 46.0}
        return pd.DataFrame(cols, index=idx), {"VOO": "USD", "QQQ": "USD", "GLD": "USD", "XU100.IS": "TRY"}

    orig = mp.market_for
    monkeypatch.setattr(mp, "market_for", lambda c, b, **k: orig(c, b, market=market, **k))
    for name, h in (("A", [("VOO", 60), ("GLD", 40)]), ("B", [("QQQ", 70), ("VOO", 30)])):
        m.save_model_portfolio(name, [{"kind": "yahoo", "symbol": s, "weight": w} for s, w in h], as_of="2026-03-02",
                               source_url="https://example.com")
    r = m.rank_model_portfolios(by="volatility", currency="USD")
    assert [x["rank"] for x in r["results"]] == [1, 2]
    assert r["results"][0]["vol_pct"] <= r["results"][1]["vol_pct"]
    a = m.analyze_model_portfolio("A", models=["equal_weighted", "min_variance"])
    assert set(a["weights_pct"]) == {"firm", "equal_weighted", "min_variance"}
    assert a["weights_pct"]["equal_weighted"] == {"VOO": 50.0, "GLD": 50.0}
    assert a["risk_profile"]["firm"]["differs_from_firm_pct"] == 0
    assert {"firm", "equal_weighted", "min_variance", "BIST100"} <= set(a["performance_since_first_revision"])
    with pytest.raises(ValueError):
        m.analyze_model_portfolio("A", revision_date="2020-01-01")
