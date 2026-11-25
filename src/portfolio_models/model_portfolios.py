"""Kurumların yayımladığı model portföyler: kayıt biçimi, doğrulama ve performans hesabı.

Bir model portföy, tarihli revizyonlardan oluşur. Her revizyon o tarihten itibaren geçerli hedef ağırlıklardır:

    {"provider": "Örnek Yatırım", "country": "TR", "source_url": "https://…", "note": "…",
     "revisions": [{"date": "2026-10-01", "holdings": [{"kind": "bist", "symbol": "THYAO", "weight": 20}, …]}, …]}

Performans: ilk revizyon tarihinde 100 ile başlar. Her revizyon tarihinde portföy yeni ağırlıklara göre yeniden
kurulur, iki revizyon arasında al-ve-tut (ağırlıklar fiyatla kayar). Fiyatlar TL'ye çevrilir; USD/EUR görünümü
endeksin kura bölünmesiyle elde edilir (benchmarks.in_currency).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .i18n import t as T
from .holdings import (
    KIND_BIST,
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    Position,
    asset_label,
    make_position,
)

STORE_KIND = "model_portfolio"
KIND_MAP = {"bist": KIND_BIST, "fund": KIND_FUND, "yahoo": KIND_YAHOO, "gold": KIND_GOLD, "cash": KIND_CASH}
KIND_NAMES = {v: k for k, v in KIND_MAP.items()}

# Kıyas serileri: tek varlıklı "portföyler" gibi hesaplanır
BENCHMARKS = {
    "BIST100": ("yahoo", "XU100.IS"),
    "S&P 500": ("yahoo", "^GSPC"),
    "DAX": ("yahoo", "^GDAXI"),
    "Gram altın": ("gold", None),
    "USD": ("cash", "USD"),
    "EUR": ("cash", "EUR"),
}

NOTE_MAX = 280  # kısa, kendi cümlemiz: raporların metni kopyalanmaz (telif)

WINDOWS = {"1G": 1, "1H": 7, "1A": 30, "3A": 91, "YB": "ytd", "1Y": 365}


# --- Doğrulama ---------------------------------------------------------------------


def _kind(k: str) -> str:
    k = str(k or "").strip()
    if k in KIND_MAP:
        return k
    if k in KIND_NAMES:  # iç (Türkçe) tür adı
        return KIND_NAMES[k]
    aliases = {"stock": "yahoo", "etf": "yahoo", "crypto": "yahoo", "tefas": "fund", "altın": "gold",
               "altin": "gold", "nakit": "cash"}
    if k.lower() in aliases:
        return aliases[k.lower()]
    raise ValueError(f"Unknown kind {k!r}; use one of {', '.join(KIND_MAP)}.")


def label_of(h: dict) -> str | None:
    return asset_label(KIND_MAP[_kind(h["kind"])], h.get("symbol"))


def validate_holdings(holdings: list[dict]) -> tuple[list[dict], list[str]]:
    """Satırları temizler: tür/sembol kontrolü, aynı varlığı birleştirir, toplamı 100'e ölçekler."""
    merged: dict[str, dict] = {}
    warnings: list[str] = []
    for h in holdings or []:
        kind = _kind(h.get("kind"))
        try:
            w = float(h.get("weight"))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid weight for {h.get('symbol')!r}.") from None
        if not math.isfinite(w) or w <= 0:
            continue
        sym = h.get("symbol")
        label = asset_label(KIND_MAP[kind], sym)
        if label is None:
            raise ValueError(f"Invalid symbol {sym!r} for kind {kind!r}.")
        if kind == "bist":
            sym = label
        elif kind == "gold":
            sym = None
        elif kind == "cash":
            sym = label.split()[-1]
        else:
            sym = label
        if label in merged:
            merged[label]["weight"] += w
        else:
            merged[label] = {"kind": kind, "symbol": sym, "weight": w}
    rows = list(merged.values())
    if not rows:
        raise ValueError("A model portfolio needs at least one holding with a positive weight.")
    total = sum(r["weight"] for r in rows)
    if abs(total - 100) > 0.5:
        warnings.append(T("Ağırlıkların toplamı %{total} idi; %100'e ölçeklendi.", total=f"{total:.2f}"))
    for r in rows:
        r["weight"] = round(r["weight"] / total * 100, 4)
    return rows, warnings


def add_revision(cfg: dict | None, as_of: str, holdings: list[dict], **meta) -> tuple[dict, list[str]]:
    """Yeni revizyon ekler (aynı tarihli revizyon varsa onu değiştirir) ve meta alanları günceller."""
    d = pd.Timestamp(as_of).normalize()
    if d > pd.Timestamp(date.today()):
        raise ValueError("as_of cannot be in the future.")
    rows, warnings = validate_holdings(holdings)
    url = meta.get("source_url")
    if url and not str(url).lower().startswith(("http://", "https://")):
        raise ValueError("source_url must be an http(s) link to the firm's public page.")
    if meta.get("note") and len(str(meta["note"])) > NOTE_MAX:
        raise ValueError(f"note is limited to {NOTE_MAX} characters: write a short note in your own words; "
                         "do not copy the firm's report text.")
    cfg = dict(cfg or {})
    revs = [r for r in cfg.get("revisions", []) if r["date"] != f"{d:%Y-%m-%d}"]
    revs.append({"date": f"{d:%Y-%m-%d}", "holdings": rows})
    cfg["revisions"] = sorted(revs, key=lambda r: r["date"])
    for k, v in meta.items():
        if v is not None:
            cfg[k] = v
    return cfg, warnings


def current_holdings(cfg: dict) -> list[dict]:
    revs = cfg.get("revisions", [])
    return revs[-1]["holdings"] if revs else []


# --- Fiyat ve performans -------------------------------------------------------------


def positions_for(configs: dict[str, dict], benchmarks: list[str] = ()) -> list[Position]:
    """Tüm model portföylerdeki ve kıyas serilerindeki tekil varlıklar (miktar önemsiz)."""
    seen: dict[str, Position] = {}
    pairs = [(h["kind"], h.get("symbol")) for c in configs.values() for r in c.get("revisions", [])
             for h in r["holdings"]] + [BENCHMARKS[b] for b in benchmarks]
    for kind, sym in pairs:
        p = make_position(KIND_MAP[kind], sym, 1.0)
        seen.setdefault(p.label, p)
    return list(seen.values())


def earliest_date(configs: dict[str, dict]) -> pd.Timestamp | None:
    dates = [pd.Timestamp(r["date"]) for c in configs.values() for r in c.get("revisions", [])[:1]]
    return min(dates) if dates else None


def index_series(cfg: dict, try_prices: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Model portföyün TL getiri endeksi (ilk revizyon = 100) ve fiyatı olmayan varlıklar için uyarılar."""
    revs = cfg.get("revisions", [])
    if not revs or try_prices.empty:
        return pd.Series(dtype=float), []
    prices = try_prices.sort_index().ffill()
    warnings: list[str] = []
    pieces: list[pd.Series] = []
    value = 100.0
    for i, rev in enumerate(revs):
        start = pd.Timestamp(rev["date"])
        end = pd.Timestamp(revs[i + 1]["date"]) if i + 1 < len(revs) else None
        seg = prices[prices.index >= start]
        if end is not None:
            seg = seg[seg.index <= end]
        if seg.empty:
            continue
        t0 = seg.index[0]
        units, used = {}, 0.0
        for h in rev["holdings"]:
            lab = label_of(h)
            p0 = prices[lab].loc[t0] if lab in prices else np.nan
            if pd.isna(p0) or p0 <= 0:
                warnings.append(T("{asset}: {d} tarihinde fiyat yok, hesaba katılmadı; ağırlığı diğerlerine dağıtıldı.",
                                  asset=lab, d=f"{t0:%Y-%m-%d}"))
                continue
            units[lab] = h["weight"] / 100 / p0
            used += h["weight"] / 100
        if not units or used <= 0:
            continue
        units = {k: v / used for k, v in units.items()}  # eksik varlık varsa kalanlara orantılı dağıt
        path = sum(seg[k] * u for k, u in units.items()) * value
        pieces.append(path if not pieces else path.iloc[1:] if path.index[0] == pieces[-1].index[-1] else path)
        value = float(path.iloc[-1])
    if not pieces:
        return pd.Series(dtype=float), warnings
    out = pd.concat(pieces)
    return out[~out.index.duplicated(keep="last")], sorted(set(warnings))


def benchmark_series(name: str, try_prices: pd.DataFrame, start: pd.Timestamp) -> pd.Series:
    kind, sym = BENCHMARKS[name]
    lab = asset_label(KIND_MAP[kind], sym)
    if lab not in try_prices:
        return pd.Series(dtype=float)
    s = try_prices[lab].dropna()
    s = s[s.index >= start]
    return s / s.iloc[0] * 100 if not s.empty else s


def window_start(idx: pd.DatetimeIndex, window) -> pd.Timestamp:
    last = idx.max()
    if window == "ytd":
        return pd.Timestamp(last.year, 1, 1)
    if window is None:
        return idx.min()
    return last - pd.Timedelta(days=int(window))


def period_return(s: pd.Series, window) -> float | None:
    s = s.dropna()
    if len(s) < 2:
        return None
    start = window_start(s.index, window)
    if window is not None and start < s.index[0] - pd.Timedelta(days=3):
        return None  # seri bu dönem kadar eski değil
    base = s[s.index <= start]
    base_v = float(base.iloc[-1]) if not base.empty else float(s.iloc[0])
    if window == 1:  # günlük: bir önceki işlem günü
        base_v = float(s.iloc[-2])
    return float(s.iloc[-1]) / base_v - 1


def metrics(s: pd.Series) -> dict:
    """Dönem getirileri, başlangıçtan beri getiri, yıllık volatilite, maks. düşüş."""
    s = s.dropna()
    out = {k: period_return(s, w) for k, w in WINDOWS.items()}
    if len(s) < 2:
        return out | {"total": None, "annual": None, "vol": None, "max_dd": None, "since": None, "last": None}
    days = (s.index[-1] - s.index[0]).days
    total = float(s.iloc[-1] / s.iloc[0] - 1)
    rets = s.pct_change().dropna()
    return out | {
        "total": total,
        "annual": (1 + total) ** (365 / days) - 1 if days >= 90 else None,
        "vol": float(rets.std() * np.sqrt(252)) if len(rets) > 5 else None,
        "max_dd": float((s / s.cummax() - 1).min()),
        "since": s.index[0].date(),
        "last": s.index[-1].date(),
    }


@dataclass
class Comparison:
    indices: dict[str, pd.Series]  # ad -> endeks (görüntü para biriminde)
    table: list[dict]  # ad, sağlayıcı, metrikler
    warnings: dict[str, list[str]]
    price_date: date | None


def compare_models(configs: dict[str, dict], try_prices: pd.DataFrame, closes: pd.DataFrame,
                   currency: str = "TRY", benchmarks: list[str] = ()) -> Comparison:
    """Model portföyleri (ve isteğe bağlı kıyas serilerini) aynı para biriminde karşılaştırır."""
    from .benchmarks import in_currency

    region = {"TRY": "TR", "USD": "US", "EUR": "DE"}[currency]
    indices, rows, warns = {}, [], {}
    for name, cfg in configs.items():
        s, w = index_series(cfg, try_prices)
        if w:
            warns[name] = w
        if s.empty:
            continue
        s = in_currency(s, closes, region) if currency != "TRY" else s
        if s.empty:
            continue
        indices[name] = s / s.iloc[0] * 100
        rows.append({"name": name, "provider": cfg.get("provider"), "country": cfg.get("country"),
                     "updated": cfg["revisions"][-1]["date"], "is_benchmark": False} | metrics(indices[name]))
    start = min((s.index[0] for s in indices.values()), default=None)
    for b in benchmarks:
        if start is None:
            break
        s = benchmark_series(b, try_prices, start)
        s = in_currency(s, closes, region) if currency != "TRY" and not s.empty else s
        if s.empty:
            continue
        indices[b] = s / s.iloc[0] * 100
        rows.append({"name": b, "provider": None, "country": None, "updated": None,
                     "is_benchmark": True} | metrics(indices[b]))
    last = max((s.index[-1] for s in indices.values()), default=None)
    return Comparison(indices, rows, warns, last.date() if last is not None else None)


def rebase(indices: dict[str, pd.Series], window) -> pd.DataFrame:
    """Grafik için: seçili dönemin başında (ya da serinin başladığı ilk gün) 100."""
    df = pd.DataFrame(indices).sort_index().ffill()
    if df.empty:
        return df
    start = window_start(df.index, window)
    df = df[df.index >= start]
    return df.apply(lambda c: c / c.dropna().iloc[0] * 100 if c.notna().any() else c)


def load_all(engine, email: str) -> dict[str, dict]:
    from . import store

    return {p["name"]: store.load_portfolio(engine, email, p["name"], kind=STORE_KIND) or {}
            for p in store.list_portfolios(engine, email, kind=STORE_KIND)}


def market_for(configs: dict[str, dict], benchmarks: list[str] = (), market=None, fund_history=None):
    """(TL fiyatları, kapanışlar) — tüm model portföy varlıkları, kıyaslar ve USD/EUR kurları için."""
    from .holdings import fetch_market_data, try_price_history

    market = market or fetch_market_data
    positions = positions_for(configs, benchmarks)
    fx = [make_position(KIND_CASH, c, 1.0) for c in ("USD", "EUR")]
    first = earliest_date(configs) or pd.Timestamp(date.today())
    years = max(1, math.ceil((pd.Timestamp(date.today()) - first).days / 365) + 1)
    closes, currencies = market([p for p in positions + fx if p.kind != KIND_FUND], years=years)
    return try_price_history(positions, closes, currencies, fund_history), closes


# --- Örnekler (giriş yapmamış ziyaretçiler ve boş kurulumlar için) ------------------------


def examples(today: date | None = None) -> dict[str, dict]:
    """Uydurma kurum adlarıyla örnek model portföyler (gerçek bir kurumun önerisi değildir)."""
    today = pd.Timestamp(today or date.today())
    d0 = f"{today - pd.Timedelta(days=365):%Y-%m-%d}"
    d1 = f"{today - pd.Timedelta(days=120):%Y-%m-%d}"
    note = "Example only — not a real institution's recommendation."
    return {
        "Örnek · Dengeli TL": {
            "provider": "Örnek Yatırım A", "country": "TR", "note": note,
            "revisions": [
                {"date": d0, "holdings": [{"kind": "bist", "symbol": "THYAO", "weight": 20},
                                          {"kind": "bist", "symbol": "BIMAS", "weight": 20},
                                          {"kind": "bist", "symbol": "ASELS", "weight": 20},
                                          {"kind": "gold", "symbol": None, "weight": 25},
                                          {"kind": "cash", "symbol": "USD", "weight": 15}]},
                {"date": d1, "holdings": [{"kind": "bist", "symbol": "THYAO", "weight": 15},
                                          {"kind": "bist", "symbol": "BIMAS", "weight": 25},
                                          {"kind": "bist", "symbol": "TUPRS", "weight": 20},
                                          {"kind": "gold", "symbol": None, "weight": 30},
                                          {"kind": "cash", "symbol": "USD", "weight": 10}]},
            ],
        },
        "Örnek · Global ETF 60/40": {
            "provider": "Örnek Asset Management B", "country": "US", "note": note,
            "revisions": [{"date": d0, "holdings": [{"kind": "yahoo", "symbol": "VTI", "weight": 40},
                                                    {"kind": "yahoo", "symbol": "VXUS", "weight": 20},
                                                    {"kind": "yahoo", "symbol": "BND", "weight": 30},
                                                    {"kind": "yahoo", "symbol": "GLD", "weight": 10}]}],
        },
        "Örnek · Avrupa temettü": {
            "provider": "Örnek Vermögensverwaltung C", "country": "DE", "note": note,
            "revisions": [{"date": d0, "holdings": [{"kind": "yahoo", "symbol": "ALV.DE", "weight": 25},
                                                    {"kind": "yahoo", "symbol": "SIE.DE", "weight": 25},
                                                    {"kind": "yahoo", "symbol": "MUV2.DE", "weight": 25},
                                                    {"kind": "yahoo", "symbol": "DTE.DE", "weight": 25}]}],
        },
    }
