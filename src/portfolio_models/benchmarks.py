"""Portföy getirisini BIST100, dolar, gram altın ve enflasyon (TÜFE) ile karşılaştırma.

Portföy için zaman ağırlıklı getiri (TWR) kullanılır: para yatırma/çekme ve alımların etkisi
ayıklanır, böylece yalnızca yatırım performansı benchmark'larla kıyaslanır.
"""

from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd

from .holdings import GOLD_FUTURES, TROY_OUNCE_GRAMS

BIST100 = "XU100.IS"
USDTRY = "USDTRY=X"
BENCHMARK_TICKERS = [BIST100, USDTRY, GOLD_FUTURES]

OECD_CPI_URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
    "TUR.M.N.CPI.IX._T.N._Z?startPeriod={start}&format=csvfile"
)


def twr_index(values: pd.Series, inflows: pd.Series | None = None) -> pd.Series:
    """Zaman ağırlıklı getiri endeksi (başlangıç = 1).

    values : gün sonu portföy değeri (TL)
    inflows: o gün portföye giren net para (TL; çıkış negatif). Gün içinde girip gün sonu değere
             yansıdığı varsayılır: r_t = (V_t - I_t) / V_{t-1} - 1
    """
    v = values.dropna().astype(float)
    if v.empty:
        return v
    inflow = (inflows.groupby(level=0).sum().reindex(v.index, fill_value=0.0)
              if inflows is not None and len(inflows) else pd.Series(0.0, index=v.index))
    prev = v.shift(1)
    r = (v - inflow) / prev - 1
    r[(prev <= 0) | prev.isna()] = 0.0  # ilk gün ya da portföy boşken getiri yok
    r = r.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return (1 + r).cumprod()


def inflows_by_day(flows: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """trade_cashflows çıktısını (portföye giren para negatif) günlük giriş serisine çevirir,
    işlem günü fiyat günü değilse sonraki ilk fiyat gününe kaydırır."""
    if flows is None or flows.empty:
        return pd.Series(0.0, index=index)
    s = pd.Series(0.0, index=index)
    for d, amount in zip(flows["date"], flows["amount"]):
        pos = index.searchsorted(pd.Timestamp(d))
        if pos < len(index):
            s.iloc[pos] += -float(amount)
    return s


def parse_oecd_cpi(text: str) -> pd.Series:
    """OECD SDMX CSV -> aylık TÜFE endeksi (index: ayın 15'i)."""
    df = pd.read_csv(io.StringIO(text))
    if "TIME_PERIOD" not in df or "OBS_VALUE" not in df:
        return pd.Series(dtype=float)
    s = pd.Series(df["OBS_VALUE"].astype(float).values,
                  index=pd.to_datetime(df["TIME_PERIOD"] + "-15")).sort_index()
    return s[~s.index.duplicated(keep="last")]


def fetch_cpi(start: str = "2015-01") -> pd.Series:
    """Türkiye TÜFE (2015=100), OECD açık veri. Bağlantı yoksa boş seri döner."""
    import urllib.request

    try:
        req = urllib.request.Request(OECD_CPI_URL.format(start=start), headers={"User-Agent": "portfolio-models"})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - sabit, güvenilir adres
            return parse_oecd_cpi(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return pd.Series(dtype=float)


EVDS_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"  # evds2 2026da evds3e taşındı
EVDS_CPI_SERIES = "TP.TUKFIY2025.GENEL"  # TÜFE genel endeks (2025=100), aylık; eski TP.FG.J0 Ocak 2026da arşivlendi


def parse_evds_cpi(payload: dict, series: str = EVDS_CPI_SERIES) -> pd.Series:
    """EVDS JSON yanıtı -> aylık TÜFE (index: ayın 15'i). Tarih biçimi '2025-1' ya da '01-2025' olabilir."""
    col = series.replace(".", "_")
    out = {}
    for item in payload.get("items", []):
        raw, val = str(item.get("Tarih", "")), item.get(col)
        if val in (None, "", "null"):
            continue
        parts = raw.replace("/", "-").split("-")
        try:
            if len(parts[0]) == 4:
                y, m = int(parts[0]), int(parts[1])
            else:
                m, y = int(parts[-2]), int(parts[-1])
            out[pd.Timestamp(year=y, month=m, day=15)] = float(val)
        except (ValueError, IndexError):
            continue
    return pd.Series(out, dtype=float).sort_index()


def fetch_cpi_evds(api_key: str, start: str = "2015-01") -> pd.Series:
    """TCMB EVDS'ten TÜFE. Anahtar HTTP başlığında gönderilir (URL'ye yazılmaz)."""
    import json
    import urllib.request

    y, m = start.split("-")
    today = date.today()
    url = (f"{EVDS_URL}series={EVDS_CPI_SERIES}&startDate=01-{m}-{y}"
           f"&endDate={today:%d-%m-%Y}&type=json&frequency=5")
    req = urllib.request.Request(url, headers={"key": api_key, "User-Agent": "portfolio-models"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - sabit, güvenilir adres
        return parse_evds_cpi(json.loads(resp.read().decode("utf-8")))


def fetch_cpi_best(evds_key: str | None = None, start: str = "2015-01") -> tuple[pd.Series, str]:
    """Önce EVDS (anahtar varsa), olmazsa OECD. Döner: (seri, kaynak adı)."""
    if evds_key:
        try:
            s = fetch_cpi_evds(evds_key, start)
            if len(s) >= 12:
                return s, "TCMB EVDS"
        except Exception:  # noqa: BLE001 - EVDS erişilemezse OECD'ye düş
            pass
    return fetch_cpi(start), "OECD"


def daily_cpi(cpi: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Aylık TÜFE'yi günlük seriye çevirir (ay ortaları arasında doğrusal). Kapsam dışı günler NaN."""
    if cpi.empty:
        return pd.Series(np.nan, index=index)
    full = cpi.reindex(cpi.index.union(index)).interpolate(method="time", limit_area="inside")
    return full.reindex(index)


def benchmark_prices(closes: pd.DataFrame) -> pd.DataFrame:
    """TL cinsinden benchmark fiyatları."""
    out = {}
    if BIST100 in closes:
        out["BIST100"] = closes[BIST100]
    if USDTRY in closes:
        out["Dolar (USD/TRY)"] = closes[USDTRY]
    if GOLD_FUTURES in closes and USDTRY in closes:
        out["Gram altın"] = closes[GOLD_FUTURES] * closes[USDTRY] / TROY_OUNCE_GRAMS
    return pd.DataFrame(out).ffill()


def compare(portfolio: pd.Series, bench: pd.DataFrame, cpi_daily: pd.Series | None,
            start: pd.Timestamp, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Başlangıç = 100 olacak şekilde normalize edilmiş seriler (portföy, benchmark'lar, TÜFE)."""
    end = end or pd.Timestamp(date.today())
    frames = {"Portföyüm": portfolio}
    for c in bench.columns:
        frames[c] = bench[c]
    if cpi_daily is not None and cpi_daily.notna().any():
        frames["Enflasyon (TÜFE)"] = cpi_daily
    df = pd.DataFrame(frames).sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    # Piyasa serilerinde tatil boşlukları doldurulur; TÜFE ise yayımlanan son ayın ötesine taşınmaz
    market = [c for c in df.columns if c != "Enflasyon (TÜFE)"]
    df[market] = df[market].ffill()
    df = df.dropna(subset=["Portföyüm"])
    if df.empty:
        return df
    out = {}
    for c in df.columns:
        s = df[c]
        first = s.first_valid_index()
        if first is None or first > df.index[0] + pd.Timedelta(days=45):
            continue  # serinin başlangıçta verisi yok
        base = s.loc[first]
        out[c] = s / base * 100
    return pd.DataFrame(out)


def summary(norm: pd.DataFrame) -> pd.DataFrame:
    """Her seri için toplam ve yıllık getiri; TÜFE varsa reel getiri."""
    if norm.empty:
        return pd.DataFrame()
    rows = []
    cpi = norm.get("Enflasyon (TÜFE)")
    for c in norm.columns:
        s = norm[c].dropna()
        if len(s) < 2:
            continue
        days = (s.index[-1] - s.index[0]).days
        total = s.iloc[-1] / s.iloc[0] - 1
        annual = (1 + total) ** (365 / days) - 1 if days >= 30 else np.nan
        real = np.nan
        if cpi is not None and c != "Enflasyon (TÜFE)":
            cs = cpi.reindex(s.index).dropna()
            if len(cs) >= 2 and cs.index[-1] >= s.index[-1] - pd.Timedelta(days=45):
                infl = cs.iloc[-1] / cs.iloc[0] - 1
                real = (1 + total) / (1 + infl) - 1
        rows.append({"Seri": c, "Toplam getiri": total, "Yıllık": annual, "Reel (TÜFE'ye göre)": real,
                     "Başlangıç": s.index[0].date(), "Bitiş": s.index[-1].date()})
    return pd.DataFrame(rows)
