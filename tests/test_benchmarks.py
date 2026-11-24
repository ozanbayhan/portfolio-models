import pandas as pd
import pytest

from portfolio_models.benchmarks import (
    benchmark_prices,
    compare,
    daily_cpi,
    inflows_by_day,
    parse_oecd_cpi,
    summary,
    twr_index,
)


def test_twr_ignores_deposits():
    idx = pd.bdate_range("2026-01-05", periods=4)
    # 100 TL ile başla, %10 kazan (110), 100 TL yatır (210), %10 kazan (231)
    values = pd.Series([100.0, 110.0, 210.0, 231.0], index=idx)
    inflows = pd.Series([0.0, 0.0, 100.0, 0.0], index=idx)
    t = twr_index(values, inflows)
    assert t.iloc[-1] == pytest.approx(1.10 * 1.0 * 1.10)  # yatırma günü getiri 0
    # para yatırmayı görmeyen basit oran yanıltıcı olurdu
    assert values.iloc[-1] / values.iloc[0] == pytest.approx(2.31)


def test_inflows_by_day_shifts_to_next_trading_day():
    idx = pd.bdate_range("2026-01-05", periods=5)  # Pzt-Cum
    flows = pd.DataFrame({"date": [pd.Timestamp("2026-01-04")], "label": ["Nakit TRY"], "amount": [-500.0]})
    s = inflows_by_day(flows, idx)
    assert s.iloc[0] == 500.0 and s.sum() == 500.0


def test_cpi_parse_and_daily():
    csv = "TIME_PERIOD,OBS_VALUE\n2025-01,100\n2025-02,110\n2025-03,121\n"
    cpi = parse_oecd_cpi(csv)
    assert list(cpi.index.day) == [15, 15, 15]
    idx = pd.date_range("2025-01-01", "2025-04-30")
    d = daily_cpi(cpi, idx)
    assert d.loc["2025-02-15"] == pytest.approx(110)
    assert pd.isna(d.loc["2025-04-30"]) and pd.isna(d.loc["2025-01-01"])  # kapsam dışı


def test_compare_and_summary():
    idx = pd.bdate_range("2025-01-01", "2025-12-31")
    port = pd.Series(range(len(idx)), index=idx, dtype=float) + 100
    closes = pd.DataFrame({"XU100.IS": 1000.0, "USDTRY=X": 35.0, "GC=F": 2600.0}, index=idx)
    closes.loc[idx[-1], "USDTRY=X"] = 42.0
    bench = benchmark_prices(closes)
    assert set(bench.columns) == {"BIST100", "Dolar (USD/TRY)", "Gram altın"}
    cpi = pd.Series([100.0, 130.0], index=pd.to_datetime(["2024-12-15", "2026-01-15"]))
    norm = compare(port, bench, daily_cpi(cpi, idx), idx[0])
    assert norm.iloc[0].round(6).eq(100).all()
    s = summary(norm).set_index("Seri")
    assert s.loc["Dolar (USD/TRY)", "Toplam getiri"] == pytest.approx(42 / 35 - 1)
    assert s.loc["BIST100", "Toplam getiri"] == pytest.approx(0)
    infl = s.loc["Enflasyon (TÜFE)", "Toplam getiri"]
    assert s.loc["BIST100", "Reel (TÜFE'ye göre)"] == pytest.approx(1 / (1 + infl) - 1)


def test_cpi_not_extended_beyond_coverage():
    idx = pd.bdate_range("2025-06-01", "2026-06-30")
    port = pd.Series(100.0, index=idx)
    closes = pd.DataFrame({"XU100.IS": 1000.0, "USDTRY=X": 35.0, "GC=F": 2600.0}, index=idx)
    cpi = pd.Series([100.0, 110.0], index=pd.to_datetime(["2025-05-15", "2025-12-15"]))
    norm = compare(port, benchmark_prices(closes), daily_cpi(cpi, idx), idx[0])
    assert norm["Enflasyon (TÜFE)"].last_valid_index() <= pd.Timestamp("2025-12-15")
    s = summary(norm).set_index("Seri")
    assert pd.isna(s.loc["BIST100", "Reel (TÜFE'ye göre)"])  # TÜFE dönemin sonunu kapsamıyor
