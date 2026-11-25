"""Portföy getirisini piyasa endeksleri, döviz, altın ve enflasyonla karşılaştırma.

Portföy için zaman ağırlıklı getiri (TWR) kullanılır: para yatırma/çekme ve alımların etkisi
ayıklanır, böylece yalnızca yatırım performansı benchmark'larla kıyaslanır.

Üç referans bölgesi vardır (REGIONS):
    TR : TL cinsinden; BIST100, dolar, gram altın; TÜFE (TCMB EVDS, yoksa OECD)
    US : USD cinsinden; S&P 500, BIST100, altın; ABD TÜFE (FRED/BLS CPI-U, yoksa OECD)
    DE : EUR cinsinden; DAX, BIST100, altın; Almanya TÜFE (Bundesbank/Destatis VPI, yoksa OECD)
Yabancı para cinsinden karşılaştırmada portföyün TL endeksi o günün kuruna bölünür.
"""

from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd

from .holdings import GOLD_FUTURES, TROY_OUNCE_GRAMS

BIST100 = "XU100.IS"
USDTRY = "USDTRY=X"
EURTRY = "EURTRY=X"
SP500 = "^GSPC"
DAX = "^GDAXI"
BENCHMARK_TICKERS = [BIST100, USDTRY, GOLD_FUTURES]
CPI_KEY = "Enflasyon (TÜFE)"  # karşılaştırma tablosunda enflasyon serisinin iç adı (bölgeden bağımsız)

REGIONS: dict[str, dict] = {
    "TR": {"currency": "TRY", "fx": None, "oecd": "TUR", "cpi_label": "Enflasyon (TÜFE)",
           "tickers": [BIST100, USDTRY, GOLD_FUTURES]},
    "US": {"currency": "USD", "fx": USDTRY, "oecd": "USA", "cpi_label": "Enflasyon (ABD TÜFE)",
           "tickers": [SP500, BIST100, USDTRY, GOLD_FUTURES]},
    "DE": {"currency": "EUR", "fx": EURTRY, "oecd": "DEU", "cpi_label": "Enflasyon (Almanya TÜFE)",
           "tickers": [DAX, BIST100, USDTRY, EURTRY, GOLD_FUTURES]},
}

OECD_CPI_URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
    "{country}.M.N.CPI.IX._T.N._Z?startPeriod={start}&format=csvfile"
)
# ABD: BLS CPI-U (tüm kentsel tüketiciler, mevsimsellikten arındırılmamış), FRED üzerinden; anahtar gerekmez
FRED_CPI_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS&cosd={start}-01"
BLS_CPI_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"
# Almanya: Destatis tüketici fiyat endeksi (VPI, 2020=100), Bundesbank açık veri API'si; anahtar gerekmez
BBK_CPI_URL = ("https://api.statistiken.bundesbank.de/rest/data/BBDP1/"
               "M.DE.N.VPI.C.A00000.I20.A?startPeriod={start}")


def benchmark_tickers(region: str = "TR") -> list[str]:
    return list(REGIONS.get(region, REGIONS["TR"])["tickers"])


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


USER_AGENT = "portfolio-models (+https://github.com/ozanbayhan/portfolio-models)"  # FRED kısa UA'ları reddediyor


def _get(url: str, accept: str | None = None) -> str:
    import urllib.request

    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - sabit, güvenilir adresler
        return resp.read().decode("utf-8-sig")


def fetch_cpi(start: str = "2015-01", country: str = "TUR") -> pd.Series:
    """TÜFE endeksi, OECD açık veri (country: TUR, USA, DEU …). Bağlantı yoksa boş seri döner."""
    try:
        return parse_oecd_cpi(_get(OECD_CPI_URL.format(country=country, start=start)))
    except Exception:  # noqa: BLE001
        return pd.Series(dtype=float)


def parse_fred_cpi(text: str) -> pd.Series:
    """FRED CSV (observation_date,CPIAUCNS) -> aylık endeks (index: ayın 15'i)."""
    df = pd.read_csv(io.StringIO(text))
    if df.shape[1] < 2:
        return pd.Series(dtype=float)
    vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")  # eksik aylar "." olarak gelir
    idx = pd.to_datetime(df.iloc[:, 0]).dt.to_period("M").dt.to_timestamp() + pd.Timedelta(days=14)
    s = pd.Series(vals.values, index=idx).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def fetch_cpi_fred(start: str = "2015-01") -> pd.Series:
    """ABD TÜFE (BLS CPI-U, 1982-84=100), FRED."""
    return parse_fred_cpi(_get(FRED_CPI_URL.format(start=start)))


def parse_bls_cpi(payload: dict) -> pd.Series:
    """BLS API v2 JSON -> aylık endeks. 'M13' (yıllık ortalama) atlanır."""
    rows = {}
    for series in payload.get("Results", {}).get("series", []):
        for d in series.get("data", []):
            period = str(d.get("period", ""))
            if not period.startswith("M") or period == "M13":
                continue
            try:
                rows[pd.Timestamp(f"{d['year']}-{period[1:]}-15")] = float(d["value"])
            except (KeyError, ValueError):
                continue
    return pd.Series(rows, dtype=float).sort_index()


def fetch_cpi_bls(start: str = "2015-01") -> pd.Series:
    """ABD TÜFE doğrudan BLS'ten (anahtarsız: istek başına en çok 10 yıl)."""
    import json

    y0 = max(int(start[:4]), date.today().year - 9)
    url = f"{BLS_CPI_URL}?startyear={y0}&endyear={date.today().year}"
    return parse_bls_cpi(json.loads(_get(url)))


def parse_bbk_cpi(text: str) -> pd.Series:
    """Bundesbank SDMX CSV (';' ayraçlı, TIME_PERIOD ve OBS_VALUE sütunları) -> aylık endeks."""
    df = pd.read_csv(io.StringIO(text), sep=";")
    if "TIME_PERIOD" not in df or "OBS_VALUE" not in df:
        return pd.Series(dtype=float)
    vals = pd.to_numeric(df["OBS_VALUE"].astype(str).str.replace(",", "."), errors="coerce")
    s = pd.Series(vals.values, index=pd.to_datetime(df["TIME_PERIOD"].astype(str) + "-15")).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def fetch_cpi_bundesbank(start: str = "2015-01") -> pd.Series:
    """Almanya TÜFE (Destatis VPI, 2020=100), Bundesbank."""
    return parse_bbk_cpi(_get(BBK_CPI_URL.format(start=start), accept="application/vnd.sdmx.data+csv;version=1.0.0"))


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


def fetch_cpi_best(evds_key: str | None = None, start: str = "2015-01",
                   region: str = "TR") -> tuple[pd.Series, str]:
    """Bölgenin resmî kaynağı, olmazsa OECD. Döner: (seri, kaynak adı).

    TR: TCMB EVDS (anahtar gerekir) · US: FRED, sonra BLS (CPI-U) · DE: Bundesbank (Destatis VPI)
    """
    sources = {
        "TR": [(lambda: fetch_cpi_evds(evds_key, start), "TCMB EVDS")] if evds_key else [],
        "US": [(lambda: fetch_cpi_fred(start), "FRED (BLS CPI-U)"), (lambda: fetch_cpi_bls(start), "BLS CPI-U")],
        "DE": [(lambda: fetch_cpi_bundesbank(start), "Bundesbank (Destatis VPI)")],
    }.get(region, [])
    for fn, name in sources:
        try:
            s = fn()
            if not s.empty:
                return s, name
        except Exception:  # noqa: BLE001 - kaynak erişilemezse sıradakine, en son OECD'ye düş
            continue
    return fetch_cpi(start, REGIONS.get(region, REGIONS["TR"])["oecd"]), "OECD"


def daily_cpi(cpi: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Aylık TÜFE'yi günlük seriye çevirir (ay ortaları arasında doğrusal). Kapsam dışı günler NaN."""
    if cpi.empty:
        return pd.Series(np.nan, index=index)
    full = cpi.reindex(cpi.index.union(index)).interpolate(method="time", limit_area="inside")
    return full.reindex(index)


def benchmark_prices(closes: pd.DataFrame, region: str = "TR") -> pd.DataFrame:
    """Bölgenin para birimi cinsinden benchmark fiyatları (TR: TL, US: USD, DE: EUR)."""
    out = {}
    c = closes
    if region == "US":
        if SP500 in c:
            out["S&P 500"] = c[SP500]
        if BIST100 in c and USDTRY in c:
            out["BIST100 (USD)"] = c[BIST100] / c[USDTRY]
        if GOLD_FUTURES in c:
            out["Altın (USD)"] = c[GOLD_FUTURES]
    elif region == "DE":
        if DAX in c:
            out["DAX"] = c[DAX]
        if BIST100 in c and EURTRY in c:
            out["BIST100 (EUR)"] = c[BIST100] / c[EURTRY]
        if GOLD_FUTURES in c and USDTRY in c and EURTRY in c:
            out["Altın (EUR)"] = c[GOLD_FUTURES] * c[USDTRY] / c[EURTRY]
        if USDTRY in c and EURTRY in c:
            out["Dolar (USD/EUR)"] = c[USDTRY] / c[EURTRY]
    else:
        if BIST100 in c:
            out["BIST100"] = c[BIST100]
        if USDTRY in c:
            out["Dolar (USD/TRY)"] = c[USDTRY]
        if GOLD_FUTURES in c and USDTRY in c:
            out["Gram altın"] = c[GOLD_FUTURES] * c[USDTRY] / TROY_OUNCE_GRAMS
    return pd.DataFrame(out).ffill()


def in_currency(index_try: pd.Series, closes: pd.DataFrame, region: str = "TR") -> pd.Series:
    """TL cinsinden getiri endeksini bölgenin para birimine çevirir (endeks / kur).

    Günlük değerlemede yabancı para getirisi (1 + r_TL) · kur_{t-1} / kur_t - 1 olduğundan
    birikimli endeks TL endeksinin kura bölünmesine eşittir (taban sonra 100'e normalize edilir).
    """
    fx = REGIONS.get(region, REGIONS["TR"])["fx"]
    if fx is None:
        return index_try
    if fx not in closes:
        return pd.Series(dtype=float)
    rate = closes[fx].reindex(closes.index.union(index_try.index)).ffill().reindex(index_try.index)
    return (index_try / rate).dropna()


def compare(portfolio: pd.Series, bench: pd.DataFrame, cpi_daily: pd.Series | None,
            start: pd.Timestamp, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Başlangıç = 100 olacak şekilde normalize edilmiş seriler (portföy, benchmark'lar, TÜFE)."""
    end = end or pd.Timestamp(date.today())
    frames = {"Portföyüm": portfolio}
    for c in bench.columns:
        frames[c] = bench[c]
    if cpi_daily is not None and cpi_daily.notna().any():
        frames[CPI_KEY] = cpi_daily
    df = pd.DataFrame(frames).sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    # Piyasa serilerinde tatil boşlukları doldurulur; TÜFE ise yayımlanan son ayın ötesine taşınmaz
    market = [c for c in df.columns if c != CPI_KEY]
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
    cpi = norm.get(CPI_KEY)
    for c in norm.columns:
        s = norm[c].dropna()
        if len(s) < 2:
            continue
        days = (s.index[-1] - s.index[0]).days
        total = s.iloc[-1] / s.iloc[0] - 1
        annual = (1 + total) ** (365 / days) - 1 if days >= 30 else np.nan
        real = np.nan
        if cpi is not None and c != CPI_KEY:
            cs = cpi.reindex(s.index).dropna()
            if len(cs) >= 2 and cs.index[-1] >= s.index[-1] - pd.Timedelta(days=45):
                infl = cs.iloc[-1] / cs.iloc[0] - 1
                real = (1 + total) / (1 + infl) - 1
        rows.append({"Seri": c, "Toplam getiri": total, "Yıllık": annual, "Reel (TÜFE'ye göre)": real,
                     "Başlangıç": s.index[0].date(), "Bitiş": s.index[-1].date()})
    return pd.DataFrame(rows)
