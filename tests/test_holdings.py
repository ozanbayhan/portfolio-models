import pandas as pd
import pytest

from portfolio_models.holdings import (
    KIND_BIST,
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    TROY_OUNCE_GRAMS,
    parse_positions,
    rebalance,
    required_tickers,
    try_price_history,
    valuation,
    value_history,
)
from portfolio_models.store import delete_portfolio, list_portfolios, load_portfolio, make_engine, save_portfolio

ROWS = [
    {"Tür": KIND_BIST, "Sembol": "thyao", "Miktar": 100, "Ort. maliyet": 250},
    {"Tür": KIND_YAHOO, "Sembol": "AAPL", "Miktar": 10, "Ort. maliyet": 200},
    {"Tür": KIND_GOLD, "Sembol": "", "Miktar": 50, "Ort. maliyet": None},
    {"Tür": KIND_CASH, "Sembol": "USD", "Miktar": 1000, "Ort. maliyet": None},
    {"Tür": KIND_CASH, "Sembol": "", "Miktar": 5000, "Ort. maliyet": None},
]


@pytest.fixture
def market():
    idx = pd.bdate_range("2026-01-01", periods=3)
    closes = pd.DataFrame(
        {
            "THYAO.IS": [290.0, 295.0, 300.0],
            "AAPL": [210.0, 215.0, 220.0],
            "GC=F": [2000.0, 2000.0, 2100.0],
            "USDTRY=X": [40.0, 40.0, 40.0],
        },
        index=idx,
    )
    currencies = {"THYAO.IS": "TRY", "AAPL": "USD", "GC=F": "USD", "USDTRY=X": "TRY"}
    return closes, currencies


def test_parse_positions():
    pos, warns = parse_positions(ROWS + [{"Tür": KIND_BIST, "Sembol": "THYAO.IS", "Miktar": 5}, {"Tür": KIND_BIST, "Sembol": "X", "Miktar": -1}])
    assert [p.label for p in pos] == ["THYAO", "AAPL", "Gram altın", "Nakit USD", "Nakit TRY"]
    assert pos[0].ticker == "THYAO.IS"
    assert len(warns) == 2  # tekrar eden THYAO + negatif miktar
    assert set(required_tickers(pos)) == {"THYAO.IS", "AAPL", "GC=F", "USDTRY=X"}


def test_valuation_in_try(market):
    closes, cur = market
    pos, _ = parse_positions(ROWS)
    table, missing = valuation(pos, closes, cur)
    assert missing == []
    t = table.set_index("Varlık")
    assert t.loc["THYAO", "Değer (TL)"] == pytest.approx(100 * 300)
    assert t.loc["AAPL", "Değer (TL)"] == pytest.approx(10 * 220 * 40)
    assert t.loc["Gram altın", "Değer (TL)"] == pytest.approx(50 * 2100 * 40 / TROY_OUNCE_GRAMS)
    assert t.loc["Nakit USD", "Değer (TL)"] == pytest.approx(40_000)
    assert t.loc["Nakit TRY", "Değer (TL)"] == pytest.approx(5_000)
    assert t.loc["THYAO", "K/Z %"] == pytest.approx(300 / 250 - 1)
    assert t.loc["AAPL", "K/Z (TL)"] == pytest.approx((220 - 200) * 10 * 40)
    assert t["Ağırlık"].sum() == pytest.approx(1.0)
    assert t.loc["THYAO", "Günlük %"] == pytest.approx(300 / 295 - 1)


def test_value_history(market):
    closes, cur = market
    pos, _ = parse_positions(ROWS)
    hist = value_history(pos, try_price_history(pos, closes, cur))
    assert len(hist) == 3
    table, _ = valuation(pos, closes, cur)
    assert hist.iloc[-1] == pytest.approx(table["Değer (TL)"].sum())


def test_rebalance(market):
    closes, cur = market
    pos, _ = parse_positions(ROWS)
    prices = try_price_history(pos, closes, cur)
    table, _ = valuation(pos, closes, cur, prices)
    targets = pd.Series({"THYAO": 0.5, "AAPL": 0.3, "Gram altın": 0.2})
    out = rebalance(table, targets, prices.iloc[-1], include_cash=True, whole_units={"THYAO"})
    o = out.set_index("Varlık")
    assert o["Hedef ağırlık"].sum() == pytest.approx(1.0)
    assert float(o.loc["THYAO", "Adet"]).is_integer()
    total = table["Değer (TL)"].sum()
    assert o["Hedef (TL)"].sum() == pytest.approx(total)
    signed = (o["Tutar (TL)"] * o["İşlem"].map({"Al": 1, "Sat": -1, "—": 0})).sum()
    cash = table[table["Tür"] == KIND_CASH]["Değer (TL)"].sum()
    assert out.attrs["cash_after"] == pytest.approx(cash - signed)

    kept = rebalance(table, targets, prices.iloc[-1], include_cash=False)
    assert kept["Hedef (TL)"].sum() == pytest.approx(total - cash)


def test_holdings_store_isolated(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'h.db'}")
    save_portfolio(eng, "ali@example.com", "Ana", ROWS, kind="holdings")
    assert load_portfolio(eng, "ali@example.com", "Ana", kind="holdings")[0]["Sembol"] == "thyao"
    assert load_portfolio(eng, "ayse@example.com", "Ana", kind="holdings") is None
    assert list_portfolios(eng, "ali@example.com") == []  # ayar kayıtları ayrı tabloda
    assert delete_portfolio(eng, "ayse@example.com", "Ana", kind="holdings") is False
    assert delete_portfolio(eng, "ali@example.com", "Ana", kind="holdings") is True


def test_tefas_fund_manual_price(market):
    closes, cur = market
    rows = ROWS + [
        {"Tür": KIND_FUND, "Sembol": "tte", "Miktar": 1000, "Ort. maliyet": 2.0, "Güncel fiyat": 2.5},
        {"Tür": KIND_FUND, "Sembol": "AFT", "Miktar": 10, "Güncel fiyat": None},
    ]
    pos, warns = parse_positions(rows)
    assert any("AFT" in w for w in warns)  # fiyatsız fon uyarı verir
    fund = [p for p in pos if p.kind == KIND_FUND]
    assert [p.label for p in fund] == ["TTE"] and fund[0].is_fixed
    prices = try_price_history(pos, closes, cur)
    table, missing = valuation(pos, closes, cur, prices)
    t = table.set_index("Varlık")
    assert missing == []
    assert t.loc["TTE", "Değer (TL)"] == pytest.approx(2500)
    assert t.loc["TTE", "K/Z (TL)"] == pytest.approx(500)
    assert t.loc["TTE", "K/Z %"] == pytest.approx(0.25)
    # yeniden dengeleme: fon olduğu gibi kalır
    targets = pd.Series({"THYAO": 0.5, "AAPL": 0.3, "Gram altın": 0.2})
    out = rebalance(table, targets, prices.iloc[-1], include_cash=True)
    assert "TTE" not in set(out["Varlık"])
    fixed = t.loc["TTE", "Değer (TL)"]
    assert out["Hedef (TL)"].sum() == pytest.approx(t["Değer (TL)"].sum() - fixed)


def test_only_funds_and_try_cash():
    pos, _ = parse_positions([
        {"Tür": KIND_FUND, "Sembol": "TTE", "Miktar": 100, "Güncel fiyat": 3.0},
        {"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 50},
    ])
    closes = pd.DataFrame()
    prices = try_price_history(pos, closes, {})
    table, missing = valuation(pos, closes, {}, prices)
    assert missing == [] and table["Değer (TL)"].sum() == pytest.approx(350)
