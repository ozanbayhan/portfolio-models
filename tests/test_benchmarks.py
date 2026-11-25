import pandas as pd
import pytest

from portfolio_models.benchmarks import (
    benchmark_prices,
    compare,
    daily_cpi,
    inflows_by_day,
    parse_evds_cpi,
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


def test_parse_evds_formats():
    payload = {"items": [
        {"Tarih": "2025-11", "TP_FG_J0": "3100.5", "UNIXTIME": {"$numberLong": "1"}},
        {"Tarih": "2025-12", "TP_FG_J0": "3150.25"},
        {"Tarih": "01-2026", "TP_FG_J0": "3300"},
        {"Tarih": "2026-2", "TP_FG_J0": None},  # henüz yayımlanmadı
    ]}
    s = parse_evds_cpi(payload, "TP.FG.J0")
    assert list(s.index.strftime("%Y-%m-%d")) == ["2025-11-15", "2025-12-15", "2026-01-15"]
    assert s.iloc[-1] == 3300.0


# --- ABD ve Almanya ----------------------------------------------------------------------

from portfolio_models import benchmarks as bm  # noqa: E402


def test_parse_fred_cpi():
    csv = "observation_date,CPIAUCNS\n2026-08-01,334.980\n2026-09-01,.\n2026-10-01,337.511\n"
    s = bm.parse_fred_cpi(csv)
    assert list(s.index.strftime("%Y-%m-%d")) == ["2026-08-15", "2026-10-15"]  # "." eksik ay atlanır
    assert s.iloc[-1] == pytest.approx(337.511)


def test_parse_bls_cpi_skips_annual_average():
    payload = {"Results": {"series": [{"data": [
        {"year": "2026", "period": "M10", "value": "337.511"},
        {"year": "2025", "period": "M13", "value": "320.0"},
        {"year": "2025", "period": "M12", "value": "324.1"},
    ]}]}}
    s = bm.parse_bls_cpi(payload)
    assert list(s.index.strftime("%Y-%m")) == ["2025-12", "2026-10"]


def test_parse_bbk_cpi():
    text = ("DATAFLOW;BBK_STD_FREQ;TIME_PERIOD;OBS_VALUE;BBK_UNIT\n"
            "BBK:BBDP1(1.0);M;2026-09;126.6;2020=100\n"
            "BBK:BBDP1(1.0);M;2026-10;126.5;2020=100\n")
    s = bm.parse_bbk_cpi(text)
    assert list(s.index.strftime("%Y-%m-%d")) == ["2026-09-15", "2026-10-15"]
    assert s.iloc[0] == pytest.approx(126.6)


def test_fetch_cpi_best_region_fallbacks(monkeypatch):
    good = pd.Series([1.0], index=pd.to_datetime(["2026-10-15"]))

    def boom(*a, **k):
        raise OSError("down")

    monkeypatch.setattr(bm, "fetch_cpi_fred", boom)
    monkeypatch.setattr(bm, "fetch_cpi_bls", lambda start: good)
    assert bm.fetch_cpi_best(None, "2025-01", "US")[1] == "BLS CPI-U"

    monkeypatch.setattr(bm, "fetch_cpi_bundesbank", boom)
    seen = {}
    monkeypatch.setattr(bm, "fetch_cpi", lambda start, country="TUR": seen.setdefault("c", country) and good)
    assert bm.fetch_cpi_best(None, "2025-01", "DE")[1] == "OECD" and seen["c"] == "DEU"


def test_benchmarks_in_usd_and_eur():
    idx = pd.bdate_range("2026-01-05", periods=3)
    closes = pd.DataFrame({"XU100.IS": [10000.0, 10000, 11000], "USDTRY=X": [40.0, 40, 44],
                           "EURTRY=X": [50.0, 50, 50], "GC=F": [3000.0, 3000, 3300],
                           "^GSPC": [6000.0, 6000, 6600], "^GDAXI": [20000.0, 20000, 20000]}, index=idx)
    us = bm.benchmark_prices(closes, "US")
    assert set(us.columns) == {"S&P 500", "BIST100 (USD)", "Altın (USD)"}
    assert us["BIST100 (USD)"].iloc[-1] == pytest.approx(11000 / 44)
    de = bm.benchmark_prices(closes, "DE")
    assert set(de.columns) == {"DAX", "BIST100 (EUR)", "Altın (EUR)", "Dolar (USD/EUR)"}
    assert de["Altın (EUR)"].iloc[-1] == pytest.approx(3300 * 44 / 50)
    assert bm.benchmark_tickers("DE")[0] == "^GDAXI" and "EURTRY=X" in bm.benchmark_tickers("DE")


def test_in_currency_removes_lira_depreciation():
    idx = pd.bdate_range("2026-01-05", periods=3)
    closes = pd.DataFrame({"USDTRY=X": [40.0, 42, 44]}, index=idx)
    # TL'de %10 kazanan ama TL de %10 değer kaybettiyse dolar bazında getiri sıfırdır
    twr = pd.Series([1.0, 1.05, 1.10], index=idx)
    usd = bm.in_currency(twr, closes, "US")
    assert usd.iloc[-1] / usd.iloc[0] == pytest.approx(1.0)
    assert bm.in_currency(twr, closes, "TR") is twr
