from datetime import date

import pandas as pd
import pytest

from portfolio_models.fund_prices import (
    editor_frame,
    from_editor,
    history_series,
    merge_history,
    parse_fund_file,
    parse_number,
)
from portfolio_models.holdings import (
    KIND_BIST,
    KIND_FUND,
    KIND_YAHOO,
    aggregate_trades,
    history_returns,
    invested_series,
    merge_rows_with_trades,
    parse_positions,
    parse_trades,
    quantity_timeline,
    rebalance,
    trade_cashflows,
    try_price_history,
    valuation,
    value_series,
    xirr,
)


# --- Dosya okuma ---------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [("1.234,56", 1234.56), ("3,775584", 3.775584), ("1,234.56", 1234.56), ("3.775584", 3.775584),
     ("1.234.567", 1234567), ("₺12,5", 12.5), ("", float("nan"))],
)
def test_parse_number(text, expected):
    got = parse_number(text)
    assert (got != got and expected != expected) or got == pytest.approx(expected)


def test_parse_tefas_csv_semicolon_turkish():
    csv = (
        "Tarih;Fon Kodu;Fon Adı;Fiyat;Tedavüldeki Pay Sayısı;Kişi Sayısı;Fon Toplam Değer\n"
        "22.11.2026;TTE;İŞ PORTFÖY BIST TEKNOLOJİ;2,512345;1.000.000;1.234;2.512.345,00\n"
        "23.11.2026;TTE;İŞ PORTFÖY BIST TEKNOLOJİ;2,523456;1.000.000;1.234;2.523.456,00\n"
        "23.11.2026;AFT;AK PORTFÖY YENİ TEKNOLOJİLER;0,812;5.000;10;4.060,00\n"
        "bozuk;TTE;x;abc;;;\n"
    ).encode("cp1254")
    df, warns = parse_fund_file(csv, "tefas.csv")
    assert set(df["code"]) == {"TTE", "AFT"}
    tte = df[df["code"] == "TTE"]
    assert list(tte["price"]) == pytest.approx([2.512345, 2.523456])
    assert tte["date"].iloc[0] == pd.Timestamp("2026-11-22")
    assert any("1 satır" in w for w in warns)


def test_parse_excel_without_code_column(tmp_path):
    pd.DataFrame({"Tarih": ["01.11.2026", "02.11.2026"], "Birim Pay Değeri": [1.5, 1.6]}).to_excel(
        tmp_path / "f.xlsx", index=False
    )
    data = (tmp_path / "f.xlsx").read_bytes()
    with pytest.raises(ValueError):
        parse_fund_file(data, "f.xlsx")
    df, _ = parse_fund_file(data, "f.xlsx", default_code="ttE")
    assert list(df["code"]) == ["TTE", "TTE"] and list(df["price"]) == [1.5, 1.6]


def test_parse_missing_columns():
    with pytest.raises(ValueError, match="Tarih"):
        parse_fund_file(b"a,b\n1,2\n", "x.csv")


def test_merge_and_editor_roundtrip():
    df = pd.DataFrame({"code": ["TTE", "TTE"], "date": pd.to_datetime(["2026-11-01", "2026-11-02"]),
                       "price": [1.0, 1.1]})
    h = merge_history({"TTE": {"2026-11-02": 9.9, "2026-10-01": 0.9}}, df)
    assert h["TTE"] == {"2026-10-01": 0.9, "2026-11-01": 1.0, "2026-11-02": 1.1}  # yeni değer geçerli
    back, warns = from_editor(editor_frame(h["TTE"]))
    assert back == h["TTE"] and warns == []
    assert history_series(h["TTE"]).index.is_monotonic_increasing


# --- İşlem geçmişi -------------------------------------------------------------

TXNS = [
    {"Tarih": date(2026, 1, 5), "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 100, "Fiyat": 200},
    {"Tarih": date(2026, 1, 7), "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "thyao", "Adet": 100, "Fiyat": 300},
    {"Tarih": date(2026, 1, 8), "İşlem": "Sat", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 50, "Fiyat": 400},
    {"Tarih": date(2026, 1, 6), "İşlem": "Al", "Tür": KIND_YAHOO, "Sembol": "AAPL", "Adet": 2, "Fiyat": 100},
    {"Tarih": date(2026, 1, 6), "İşlem": "Al", "Tür": KIND_FUND, "Sembol": "TTE", "Adet": 1000, "Fiyat": 2.0},
]


def test_aggregate_average_cost():
    trades, warns = parse_trades(TXNS + [{"Tarih": date(2099, 1, 1), "İşlem": "Al", "Tür": KIND_BIST,
                                          "Sembol": "X", "Adet": 1, "Fiyat": 1}])
    assert len(warns) == 1  # ileri tarih
    summ, w2 = aggregate_trades(trades)
    t = summ["THYAO"]
    assert t.qty == 150
    assert t.avg_cost == pytest.approx(250)  # (100*200 + 100*300) / 200
    assert t.realized == pytest.approx((400 - 250) * 50)
    assert w2 == []


def test_oversell_warns():
    trades, _ = parse_trades([
        {"Tarih": date(2026, 1, 5), "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "A", "Adet": 10, "Fiyat": 1},
        {"Tarih": date(2026, 1, 6), "İşlem": "Sat", "Tür": KIND_BIST, "Sembol": "A", "Adet": 15, "Fiyat": 2},
    ])
    summ, warns = aggregate_trades(trades)
    assert summ["A"].qty == 0 and len(warns) == 1


def test_merge_rows_with_trades():
    trades, _ = parse_trades(TXNS)
    summ, _ = aggregate_trades(trades)
    rows = [{"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 50, "Ort. maliyet": 100, "Güncel fiyat": None}]
    merged = merge_rows_with_trades(rows, summ)
    m = {r["Sembol"].upper(): r for r in merged}
    assert m["THYAO"]["Miktar"] == 200
    assert m["THYAO"]["Ort. maliyet"] == pytest.approx((50 * 100 + 150 * 250) / 200)
    assert m["AAPL"]["Miktar"] == 2 and m["TTE"]["Miktar"] == 1000


@pytest.fixture
def market():
    idx = pd.bdate_range("2026-01-05", "2026-01-12")
    closes = pd.DataFrame(
        {"THYAO.IS": [200, 250, 300, 400, 410, 420], "AAPL": [100] * 6, "USDTRY=X": [40.0] * 6},
        index=idx, dtype=float,
    )
    return closes, {"THYAO.IS": "TRY", "AAPL": "USD", "USDTRY=X": "TRY"}


def test_timeline_value_invested_and_xirr(market):
    closes, cur = market
    trades, _ = parse_trades(TXNS)
    fund_hist = {"TTE": history_series({"2026-01-06": 2.0, "2026-01-09": 2.2})}
    summ, _ = aggregate_trades(trades)
    positions, warns = parse_positions(merge_rows_with_trades([], summ), funds_with_history={"TTE"})
    assert warns == []
    prices = try_price_history(positions, closes, cur, fund_hist)
    qty = quantity_timeline({}, trades, prices.index)
    assert qty.loc["2026-01-05", "THYAO"] == 100
    assert qty.loc["2026-01-08", "THYAO"] == 150
    assert qty.loc["2026-01-05", "AAPL"] == 0
    vals = value_series(qty, prices)
    assert vals.loc["2026-01-05"] == pytest.approx(100 * 200)
    flows = trade_cashflows(trades, closes, cur)
    aapl = flows[flows["label"] == "AAPL"]["amount"].iloc[0]
    assert aapl == pytest.approx(-2 * 100 * 40)  # işlem günü kuruyla TL
    inv = invested_series(flows, prices.index)
    assert inv.iloc[-1] == pytest.approx(-flows["amount"].sum())
    table, _ = valuation(positions, closes, cur, prices, fund_hist)
    t = table.set_index("Varlık")
    assert t.loc["TTE", "Son fiyat"] == pytest.approx(2.2)
    assert t.loc["TTE", "Fiyat tarihi"] == date(2026, 1, 9)
    final = table["Değer (TL)"].sum()
    r = xirr([(d, a) for d, a in zip(flows["date"], flows["amount"])] + [(prices.index[-1], final)])
    assert r is None or r > 0  # 1 haftalık veride yıllıklandırma anlamsız derecede büyük olabilir


def test_fund_with_history_joins_rebalance():
    idx = pd.bdate_range("2025-01-01", periods=300)
    closes = pd.DataFrame({"THYAO.IS": pd.Series(range(300), index=idx, dtype=float) + 100,
                           "ASELS.IS": 50 + (pd.Series(range(300), index=idx, dtype=float) % 7)}, index=idx)
    fund = pd.Series(1 + (pd.Series(range(300), index=idx) % 5) / 100, index=idx)
    positions, _ = parse_positions(
        [{"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 10}, {"Tür": KIND_BIST, "Sembol": "ASELS", "Miktar": 10},
         {"Tür": KIND_FUND, "Sembol": "TTE", "Miktar": 100}],
        funds_with_history={"TTE"},
    )
    fund_pos = [p for p in positions if p.label == "TTE"][0]
    assert fund_pos.has_history and not fund_pos.is_fixed
    prices = try_price_history(positions, closes, {"THYAO.IS": "TRY", "ASELS.IS": "TRY"}, {"TTE": fund})
    rets = history_returns(prices, positions)
    assert "TTE" in rets.columns and len(rets) > 200
    table, _ = valuation(positions, closes, {"THYAO.IS": "TRY", "ASELS.IS": "TRY"}, prices, {"TTE": fund})
    out = rebalance(table, pd.Series({"THYAO": 0.4, "ASELS": 0.3, "TTE": 0.3}), prices.iloc[-1],
                    fixed={p.label for p in positions if p.is_fixed})
    assert set(out["Varlık"]) == {"THYAO", "ASELS", "TTE"}
    assert out["Hedef (TL)"].sum() == pytest.approx(table["Değer (TL)"].sum())


def test_xirr_simple():
    r = xirr([(pd.Timestamp("2025-01-01"), -100), (pd.Timestamp("2026-01-01"), 110)])
    assert r == pytest.approx(0.10, abs=1e-3)
    assert xirr([(pd.Timestamp("2025-01-01"), -100)]) is None


def test_fund_prices_store(tmp_path):
    from portfolio_models.store import list_portfolios, load_portfolio, make_engine, save_portfolio

    eng = make_engine(f"sqlite:///{tmp_path / 'f.db'}")
    save_portfolio(eng, "ali@example.com", "TTE", {"2026-11-01": 2.5}, kind="fund_prices")
    assert load_portfolio(eng, "ali@example.com", "TTE", kind="fund_prices") == {"2026-11-01": 2.5}
    assert list_portfolios(eng, "ayse@example.com", kind="fund_prices") == []


def test_dividends_and_cash_tracking():
    from portfolio_models.holdings import (
        KIND_CASH, cash_balances, cash_tracking, dividends_tl, trade_cashflows as tcf,
    )
    rows = [
        {"Tarih": date(2026, 1, 2), "İşlem": "Para yatır", "Tür": KIND_CASH, "Sembol": "TRY", "Tutar": 50000},
        {"Tarih": date(2026, 1, 5), "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 100, "Fiyat": 200},
        {"Tarih": date(2026, 1, 6), "İşlem": "Al", "Tür": KIND_YAHOO, "Sembol": "AAPL", "Adet": 2, "Fiyat": 100},
        {"Tarih": date(2026, 1, 8), "İşlem": "Temettü", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 100,
         "Fiyat": 2.5},  # adet × hisse başı temettü
        {"Tarih": date(2026, 1, 9), "İşlem": "Temettü", "Tür": KIND_YAHOO, "Sembol": "AAPL", "Tutar": 1},
        {"Tarih": date(2026, 1, 9), "İşlem": "Sat", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 50, "Fiyat": 400},
        {"Tarih": date(2026, 1, 12), "İşlem": "Para çek", "Tür": KIND_CASH, "Sembol": "TRY", "Tutar": 1000},
        {"Tarih": date(2026, 1, 12), "İşlem": "Al", "Tür": KIND_CASH, "Sembol": "USD", "Adet": 1, "Fiyat": 1},
    ]
    trades, warns = parse_trades(rows)
    assert len(warns) == 1 and "Nakit" in warns[0]  # nakit 'Al' kabul edilmez
    assert cash_tracking(trades)
    summ, _ = aggregate_trades(trades)
    assert summ["THYAO"].dividends == pytest.approx(250) and summ["AAPL"].dividends == pytest.approx(1)
    cur = {"AAPL": "USD", "USDTRY=X": "TRY", "THYAO.IS": "TRY"}
    bal = cash_balances(trades, cur)
    assert bal["Nakit TRY"] == pytest.approx(50000 - 20000 + 250 + 20000 - 1000)
    assert bal["Nakit USD"] == pytest.approx(-200 + 1)  # dolar yatırılmadan alım: eksi bakiye
    idx = pd.bdate_range("2026-01-02", "2026-01-12")
    closes = pd.DataFrame({"THYAO.IS": 200.0, "AAPL": 100.0, "USDTRY=X": 40.0}, index=idx)
    flows = tcf(trades, closes, cur)
    assert list(flows["amount"]) == [-50000, 1000]  # yalnızca dış akışlar
    assert dividends_tl(trades, closes, cur) == pytest.approx(250 + 40)
    merged = merge_rows_with_trades([{"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 500}], summ, bal)
    m = {r["Sembol"]: r["Miktar"] for r in merged}
    assert m["TRY"] == pytest.approx(500 + bal["Nakit TRY"])
    assert "USD" not in m  # eksi bakiye pozisyona eklenmez


def test_without_cash_tracking_dividend_is_inflow():
    from portfolio_models.holdings import trade_cashflows as tcf

    trades, _ = parse_trades([
        {"Tarih": date(2026, 1, 5), "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "A", "Adet": 10, "Fiyat": 10},
        {"Tarih": date(2026, 1, 6), "İşlem": "Temettü", "Tür": KIND_BIST, "Sembol": "A", "Tutar": 5},
    ])
    flows = tcf(trades, pd.DataFrame(), {})
    assert list(flows["amount"]) == [-100, 5]
