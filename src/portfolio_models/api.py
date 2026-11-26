"""Herkese açık, salt okunur JSON API: model portföy arşivi, sıralama ve optimizasyon analizi.

    portfolio-models api --port 8770 --data-dir /data

Ayrı bir arayüz (ör. Lovable ile yapılmış React sitesi) bu uç noktaları okur. Veri, MCP ve web arayüzüyle aynı
veritabanındaki **arşiv kullanıcısının** model portföyleridir (PM_ARCHIVE_USER, varsayılan yerel kullanıcı). Kayıt
yoksa uydurma kurum adlı örnekler `example: true` ile döner.

Fiyatlar bellekte tutulur ve her gün BIST ile ABD kapanışlarından sonra (15:45 ve 21:45 UTC), ayrıca arşiv
değiştiğinde (5 dakikada bir kontrol) yenilenir. Hesaplanan yanıtlar bir sonraki yenilemeye kadar önbellekte kalır.

Oranlar 0–1 arası kesirdir (0.123 = %12,3). Tarihler YYYY-MM-DD. Tüm uç noktalar `lang=tr|en` alır.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
from datetime import date, datetime, timezone
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import model_analysis as ma
from . import model_portfolios as mp
from . import store
from .holdings import display_label
from .i18n import set_lang
from .i18n import t as T

log = logging.getLogger("portfolio_models.api")

LOCAL_USER = "yerel@localhost"
CURRENCIES = ("TRY", "USD", "EUR")
WINDOWS = {"since_inception": None, "ytd": "ytd", "1y": 365, "3m": 91}
REFRESH_UTC = ((15, 45), (21, 45))  # BIST kapanışı (18:10 TR) ve ABD kapanışı (00:00 TR) sonrası
CHECK_EVERY = 300  # sn: arşiv değişti mi?

RANKING_TEXT = {  # anahtar -> (sayfadaki Türkçe etiket, açıklama) — çevirileri locales.py'de
    "return": ("En yüksek getiri", "Seçilen dönemdeki toplam getiri."),
    "risk_adjusted": ("Riske göre getiri (Sharpe)",
                      "Günlük getirilerin ortalamasının oynaklığa oranı, yıllık. Risksiz faiz düşülmez."),
    "alpha": ("Kıyasa göre fark (alfa)",
              "Yıllık getirinin, aynı dönemde kıyas serisinin yıllık getirisinden farkı (en az 90 gün)."),
    "hit_rate": ("İsabet oranı",
                 "Her revizyonda seçilen varlıklardan (nakit hariç), tutuldukları dönemde kıyası geçenlerin oranı."),
    "consistency": ("Tutarlılık (aylık)",
                    "Ayların yüzde kaçında portföyün kıyas serisinin üstünde kaldığı (en az 3 ay)."),
    "drawdown": ("En küçük düşüş", "Zirveden en büyük düşüş; küçük olan üstte."),
    "volatility": ("En düşük oynaklık", "Yıllık oynaklık; düşük olan üstte."),
}
WINDOW_TEXT = {"since_inception": "Başlangıçtan", "ytd": "Yılbaşından", "1y": "1 yıl", "3m": "3 ay"}
DISCLAIMER = ("Bu sayfa, kurumların kamuya açık olarak yayımladığı model portföylerin bir arşivi ve matematiksel "
              "analizidir. Yalnızca varlık, ağırlık ve tarih bilgisi saklanır; raporların metni, grafikleri ve "
              "dosyaları kopyalanmaz, kaynak bağlantısı verilir. Performans bu uygulama tarafından geçmiş kapanış "
              "fiyatlarıyla hesaplanır (işlem maliyeti, vergi ve temettü hariç) ve kurumun açıkladığı rakamlardan "
              "farklı olabilir. Sıralamalar geçmiş verinin istatistiksel bir özetidir. Burada yer alan bilgiler "
              "yatırım danışmanlığı kapsamında değildir; yatırım tavsiyesi değildir.")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# --- JSON yardımcıları ---------------------------------------------------------------------------


def clean(v: Any) -> Any:
    """JSON'a uygun değer: NaN/inf → None, numpy → Python, tarih → 'YYYY-MM-DD'."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float):
        return None if not math.isfinite(v) else round(v, 6)
    return v


def slugify(name: str) -> str:
    tr = str.maketrans("ıİşŞğĞçÇöÖüÜ", "iIsSgGcCoOuU")
    s = unicodedata.normalize("NFKD", name.translate(tr)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "portfolio"


def series_points(s: pd.Series, every: int = 1) -> list[list]:
    s = s.dropna()
    if every > 1 and len(s) > every:
        s = pd.concat([s.iloc[::every], s.iloc[-1:]])
        s = s[~s.index.duplicated(keep="last")]
    return [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in s.items()]


def model_label(key: str) -> str:
    if key == ma.ACTUAL:
        return T("Kurumun portföyü")
    if ma.model_desc(key):
        return T(ma.model_desc(key))
    if key in mp.BENCHMARKS:
        return display_label(key)
    return key


# --- Arşiv durumu (fiyatlar ve önbellek) ------------------------------------------------------------


def _engine():
    url = os.environ.get("PM_DATABASE_URL") or os.environ.get("DB_URL")
    if not url:
        data_dir = Path(os.environ.get("PM_DATA_DIR", "~/.portfolio-models")).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{data_dir / 'portfolios.db'}"
    return store.make_engine(url)


class Archive:
    """Model portföyler, fiyatlar ve hesaplanmış yanıtların önbelleği. İş parçacığı güvenli."""

    def __init__(self, engine=None, user: str | None = None, market=None):
        self.engine = engine
        self.user = user or os.environ.get("PM_ARCHIVE_USER", LOCAL_USER)
        self.market = market  # testlerde sahte piyasa verisi
        self.lock = threading.RLock()
        self.refresh_lock = threading.Lock()  # aynı anda tek indirme
        self.configs: dict[str, dict] = {}
        self.slugs: dict[str, str] = {}  # slug -> ad
        self.example = False
        self.try_prices = pd.DataFrame()
        self.closes = pd.DataFrame()
        self.digest = ""
        self.version = 0
        self.refreshed_at: datetime | None = None
        self.cache: dict[tuple, Any] = {}

    # Veri yükleme
    def _load_configs(self) -> tuple[dict[str, dict], dict[str, dict], bool]:
        engine = self.engine or _engine()
        configs = mp.load_all(engine, self.user)
        funds = {f["name"]: store.load_portfolio(engine, self.user, f["name"], kind="fund_prices") or {}
                 for f in store.list_portfolios(engine, self.user, kind="fund_prices")}
        configs = {k: v for k, v in configs.items() if v.get("revisions")}
        if not configs:
            return mp.examples(), {}, True
        return configs, funds, False

    def refresh(self, force: bool = False) -> bool:
        """Arşiv değiştiyse ya da `force` ise fiyatları yeniden çeker. Yenilendiyse True."""
        with self.refresh_lock:
            return self._refresh(force)

    def _refresh(self, force: bool) -> bool:
        from .fund_prices import history_series

        configs, funds, example = self._load_configs()
        digest = hashlib.sha256(json.dumps([configs, funds], sort_keys=True, default=str).encode()).hexdigest()
        if not force and digest == self.digest and not self.try_prices.empty:
            return False
        fund_hist = {k: history_series(v) for k, v in funds.items() if v}
        kw = {"market": self.market} if self.market else {}
        try_prices, closes = mp.market_for(configs, list(mp.BENCHMARKS), fund_history=fund_hist, **kw)
        slugs: dict[str, str] = {}
        for name in sorted(configs):
            s, i = slugify(name), 2
            while s in slugs:
                s, i = f"{slugify(name)}-{i}", i + 1
            slugs[s] = name
        with self.lock:
            self.configs, self.slugs, self.example = configs, slugs, example
            self.try_prices, self.closes = try_prices, closes
            self.digest, self.version = digest, self.version + 1
            self.refreshed_at = datetime.now(timezone.utc)
            self.cache.clear()
        log.info("refreshed: %d model portfolios, prices to %s", len(configs),
                 try_prices.index.max().date() if not try_prices.empty else "—")
        return True

    def ensure(self) -> None:
        if self.version == 0:
            with self.refresh_lock:
                if self.version == 0:
                    self._refresh(True)

    def cached(self, key: tuple, fn):
        with self.lock:
            k = (self.version,) + key
            if k in self.cache:
                return self.cache[k]
        out = fn()
        with self.lock:
            self.cache[(self.version,) + key] = out
        return out

    # Yardımcılar
    def prices(self, currency: str) -> pd.DataFrame:
        if currency not in CURRENCIES:
            raise ApiError(400, f"currency must be one of {', '.join(CURRENCIES)}")
        return self.cached(("prices", currency), lambda: ma.in_ccy(self.try_prices, self.closes, currency))

    def name_of(self, slug: str) -> str:
        if slug not in self.slugs:
            raise ApiError(404, f"No model portfolio {slug!r}.")
        return self.slugs[slug]

    def slug_of(self, name: str) -> str:
        return next(s for s, n in self.slugs.items() if n == name)

    @property
    def price_date(self) -> str | None:
        return None if self.try_prices.empty else self.try_prices.index.max().strftime("%Y-%m-%d")

    def base(self) -> dict:
        return {"example": self.example, "price_date": self.price_date,
                "refreshed_at": self.refreshed_at.isoformat(timespec="seconds") if self.refreshed_at else None}


# --- Yanıtlar ----------------------------------------------------------------------------------------


def _benchmark(b: str | None) -> str | None:
    if b in (None, "", "none"):
        return None
    if b not in mp.BENCHMARKS:
        raise ApiError(400, f"benchmark must be one of {', '.join(mp.BENCHMARKS)} or none")
    return b


def _summary(a: Archive, name: str, cfg: dict, prices: pd.DataFrame) -> dict:
    s, warnings = mp.index_series(cfg, prices)
    m = mp.metrics(s) if not s.empty else {}
    sc = ma.scorecard(s) if not s.empty else {}
    last = s[s.index >= s.index.max() - pd.Timedelta(days=365)] if not s.empty else s
    revs = cfg["revisions"]
    return {
        "slug": a.slug_of(name), "name": name, "provider": cfg.get("provider"), "country": cfg.get("country"),
        "source_url": cfg.get("source_url"), "updated": revs[-1]["date"], "since": revs[0]["date"],
        "revision_count": len(revs), "asset_count": len(revs[-1]["holdings"]),
        "returns": {"1d": m.get("1G"), "1w": m.get("1H"), "1m": m.get("1A"), "3m": m.get("3A"), "ytd": m.get("YB"),
                    "1y": m.get("1Y"), "since_inception": m.get("total")},
        "annual_return": m.get("annual"), "volatility": m.get("vol"), "max_drawdown": m.get("max_dd"),
        "sharpe": sc.get("sharpe"),
        "sparkline": [v for _, v in series_points(last / last.iloc[0] * 100, every=5)] if not last.empty else [],
        "warnings": warnings,
    }


def meta(a: Archive) -> dict:
    return a.base() | {
        "currencies": list(CURRENCIES),
        "benchmarks": [{"key": b, "label": display_label(b)} for b in mp.BENCHMARKS],
        "rankings": [{"key": k, "label": T(lbl), "help": T(hlp), "higher_is_better": ma.RANKINGS[k][1],
                      "field": ma.RANKINGS[k][0]} for k, (lbl, hlp) in RANKING_TEXT.items()],
        "windows": [{"key": k, "label": T(v)} for k, v in WINDOW_TEXT.items()],
        "analysis_models": [{"key": k, "label": T(ma.model_desc(k))} for k in ma.ANALYSIS_MODELS],
        "countries": sorted({c.get("country") for c in a.configs.values() if c.get("country")}),
        "count": len(a.configs),
        "disclaimer": T(DISCLAIMER),
    }


def portfolios(a: Archive, currency: str = "TRY") -> dict:
    prices = a.prices(currency)
    items = [_summary(a, n, c, prices) for n, c in sorted(a.configs.items())]
    return a.base() | {"currency": currency, "items": items}


def leaderboard(a: Archive, by: str = "risk_adjusted", window: str = "since_inception", currency: str = "TRY",
                benchmark: str | None = "BIST100") -> dict:
    if by not in ma.RANKINGS:
        raise ApiError(400, f"by must be one of {', '.join(ma.RANKINGS)}")
    if window not in WINDOWS:
        raise ApiError(400, f"window must be one of {', '.join(WINDOWS)}")
    bench = _benchmark(benchmark)
    lb = ma.rank(ma.leaderboard(a.configs, a.prices(currency), bench, WINDOWS[window]), by)
    field = ma.RANKINGS[by][0]
    rows = []
    for i, (name, r) in enumerate(lb.iterrows(), 1):
        rows.append({
            "rank": i if pd.notna(r.get(field)) else None, "slug": a.slug_of(name), "name": name,
            "provider": r["provider"], "country": r["country"], "updated": r["updated"],
            "revision_count": int(r["revisions"]), "asset_count": int(r["n_assets"]), "since": r["since"],
            "value": r.get(field),
            "metrics": {k: r.get(k) for k in ("total", "annual", "vol", "max_dd", "sharpe", "sortino", "alpha", "beta",
                                              "tracking_error", "info_ratio", "hit_rate", "monthly_win",
                                              "bench_total")},
        })
    return a.base() | {"by": by, "field": field, "higher_is_better": ma.RANKINGS[by][1], "window": window,
                       "currency": currency, "benchmark": bench, "items": rows}


def detail(a: Archive, slug: str, currency: str = "TRY", benchmark: str | None = "BIST100") -> dict:
    name = a.name_of(slug)
    cfg = a.configs[name]
    prices = a.prices(currency)
    bench = _benchmark(benchmark)
    s, _ = mp.index_series(cfg, prices)
    out = _summary(a, name, cfg, prices)
    out.pop("sparkline")
    bs = pd.Series(dtype=float)
    if bench and not s.empty:
        lab = ma.bench_label_of(bench)
        if lab in prices:
            bs = prices[lab].dropna()
            bs = bs[bs.index >= s.index[0]]
            bs = bs / bs.iloc[0] * 100 if not bs.empty else bs
    sc = ma.scorecard(s, bs if not bs.empty else None, cfg, prices, ma.bench_label_of(bench) if bench else None)

    def holdings(rev):
        return [{"asset": mp.label_of(h), "label": display_label(mp.label_of(h)), "kind": h["kind"],
                 "symbol": h.get("symbol"), "weight": h["weight"] / 100}
                for h in sorted(rev["holdings"], key=lambda h: -h["weight"])]

    revs = cfg["revisions"]
    return a.base() | out | {
        "currency": currency, "benchmark": bench, "note": cfg.get("note"),
        "holdings": holdings(revs[-1]),
        "revisions": [{"date": r["date"], "holdings": holdings(r)} for r in reversed(revs)],
        "series": {"portfolio": series_points(s), "benchmark": series_points(bs) if not bs.empty else []},
        "scorecard": sc,
    }


def _analyze(a: Archive, name: str, currency: str, bench: str | None, idx: int = -1) -> ma.Analysis:
    """Analiz nesnesi (dilden bağımsız sayılar) önbellekte tutulur; tekil ve toplu analiz aynı sonucu kullanır."""
    return a.cached(("_analyze", name, currency, bench, idx),
                    lambda: ma.analyze(a.configs[name], a.prices(currency), bench, revision=idx))


def analysis_overview(a: Archive, currency: str = "TRY", benchmark: str | None = "BIST100") -> dict:
    """Tüm model portföylerin optimizasyon analizi tek tabloda, ayrıca model bazında özet.

    Her portföy için son revizyon incelenir; performans ilk revizyondan bugüne (modeller kurumun revizyon
    takviminde yeniden ağırlıklandırılır). Modeller: kurumun portföyünü Sharpe ve getiride kaç portföyde geçtiği,
    ortalamaları ve kaç portföyde kuruma en yakın model olduğu.
    """
    bench = _benchmark(benchmark)
    items, per_model, failed = [], {}, []
    for name in sorted(a.configs):
        try:
            res = _analyze(a, name, currency, bench)
        except Exception as e:  # noqa: BLE001 - bir portföy hesaplanamazsa diğerleri sürsün
            failed.append({"name": name, "error": str(e)})
            continue
        firm = res.scores.get(ma.ACTUAL, {})
        models = [k for k in res.scores if k not in (ma.ACTUAL, bench)]
        rows = [{"key": k, "label": model_label(k), "total": res.scores[k].get("total"),
                 "sharpe": res.scores[k].get("sharpe"), "vol": res.scores[k].get("vol"),
                 "max_dd": res.scores[k].get("max_dd"),
                 "distance": res.profiles[k].distance if k in res.profiles else None} for k in models]
        ranked = sorted([r for r in rows if r["sharpe"] is not None], key=lambda r: -r["sharpe"])
        fs, ft = firm.get("sharpe"), firm.get("total")
        firm_rank = (1 + sum(r["sharpe"] > fs for r in ranked)) if fs is not None else None
        p = res.profiles[ma.ACTUAL]
        items.append({
            "slug": a.slug_of(name), "name": name, "provider": a.configs[name].get("provider"),
            "country": a.configs[name].get("country"), "revision": res.as_of, "since": a.configs[name]["revisions"][0]["date"],
            "firm": {"total": ft, "sharpe": fs, "vol": firm.get("vol"), "max_dd": firm.get("max_dd"),
                     "alpha": firm.get("alpha"), "effective_assets": p.eff_n, "diversification_ratio": p.div_ratio,
                     "annual_volatility": p.ann_vol, "top_risk_asset": p.top_risk, "top_risk_share": p.top_risk_share},
            "firm_rank_by_sharpe": firm_rank, "ranked_out_of": len(ranked) + (1 if fs is not None else 0),
            "closest_model": {"key": res.closest, "label": model_label(res.closest),
                              "distance": res.profiles[res.closest].distance} if res.closest else None,
            "best_model": {"key": ranked[0]["key"], "label": ranked[0]["label"], "sharpe": ranked[0]["sharpe"],
                           "total": ranked[0]["total"]} if ranked else None,
            "models": rows,
            "decomposition": res.decomposition,
        })
        for r in rows:
            m = per_model.setdefault(r["key"], {"key": r["key"], "label": r["label"], "n": 0, "beat_sharpe": 0,
                                               "beat_return": 0, "closest": 0, "_tot": [], "_sh": [], "_dist": []})
            m["n"] += 1
            m["beat_sharpe"] += int(r["sharpe"] is not None and fs is not None and r["sharpe"] > fs)
            m["beat_return"] += int(r["total"] is not None and ft is not None and r["total"] > ft)
            m["closest"] += int(res.closest == r["key"])
            for k, v in (("_tot", r["total"]), ("_sh", r["sharpe"]), ("_dist", r["distance"])):
                if v is not None:
                    m[k].append(v)
    summary = []
    for m in per_model.values():
        summary.append({"key": m["key"], "label": m["label"], "portfolios": m["n"],
                        "beat_firm_sharpe": m["beat_sharpe"] / m["n"], "beat_firm_return": m["beat_return"] / m["n"],
                        "closest_count": m["closest"],
                        "avg_total": float(np.mean(m["_tot"])) if m["_tot"] else None,
                        "avg_sharpe": float(np.mean(m["_sh"])) if m["_sh"] else None,
                        "avg_distance": float(np.mean(m["_dist"])) if m["_dist"] else None})
    summary.sort(key=lambda r: -(r["avg_sharpe"] if r["avg_sharpe"] is not None else -99))
    dec = [i["decomposition"] for i in items]
    sel = [d["selection"] for d in dec if d["selection"] is not None]
    wgt = [d["weighting"] for d in dec if d["weighting"] is not None]
    return a.base() | {
        "currency": currency, "benchmark": bench, "items": items, "models": summary, "failed": failed,
        "firms": {"portfolios": len(items),
                  "selection_positive": sum(x > 0 for x in sel) / len(sel) if sel else None,
                  "weighting_positive": sum(x > 0 for x in wgt) / len(wgt) if wgt else None,
                  "beat_all_models_sharpe": sum(i["firm_rank_by_sharpe"] == 1 for i in items) / len(items)
                  if items else None},
        "note": T("Modeller yalnızca revizyon tarihinden önceki fiyatları görür."),
    }


def _chart_payload(res: ma.Analysis, key) -> dict:
    """Grafik verileri: etkin sınır, portföylerin ve varlıkların risk/getiri konumu, risk katkıları, korelasyon,
    kurumun ima ettiği getiriler ve Black-Litterman beklentileri. Hepsi revizyon öncesi veriyle, yıllık."""
    out: dict = {"frontier": [], "points": [], "assets": [], "risk_contributions": [], "correlation": None}
    if res.frontier is not None:
        out["frontier"] = [[float(v), float(r)] for v, r in zip(res.frontier["vol"], res.frontier["ret"])]
    for k, p in res.profiles.items():
        if p.ann_vol is not None:
            out["points"].append({"key": key(k), "label": model_label(k), "is_firm": k == ma.ACTUAL,
                                  "vol": p.ann_vol, "ret": p.ann_ret})
    if res.assets is not None:
        for asset, row in res.assets.iterrows():
            out["assets"].append({"asset": asset, "label": display_label(asset), "vol": row.get("vol"),
                                  "past_return": row.get("past_return"),
                                  "implied_return": row.get("implied_return"), "bl_return": row.get("bl_return"),
                                  "firm_weight": float(res.weights.loc[asset, ma.ACTUAL])})
    if res.risk_contrib_all is not None:
        rc = res.risk_contrib_all
        out["risk_contributions"] = [{"asset": asset, "label": display_label(asset),
                                      **{key(c): float(rc.loc[asset, c]) for c in rc.columns}} for asset in rc.index]
    if res.correlation is not None:
        c = res.correlation
        out["correlation"] = {"assets": [display_label(x) for x in c.index],
                              "matrix": [[round(float(v), 4) for v in row] for row in c.values]}
    return out


def analysis(a: Archive, slug: str, currency: str = "TRY", benchmark: str | None = "BIST100",
             revision: str | None = None) -> dict:
    name = a.name_of(slug)
    cfg = a.configs[name]
    bench = _benchmark(benchmark)
    dates = [r["date"] for r in cfg["revisions"]]
    idx = -1
    if revision:
        if revision not in dates:
            raise ApiError(400, f"No revision on {revision}; revisions: {', '.join(dates)}")
        idx = dates.index(revision) - len(dates)
    res = _analyze(a, name, currency, bench, idx)
    key = lambda k: "firm" if k == ma.ACTUAL else k  # noqa: E731
    cols = list(res.weights.columns)
    return a.base() | {
        "slug": slug, "name": name, "currency": currency, "benchmark": bench, "revision": res.as_of,
        "revisions": dates[::-1],
        "portfolios": [{"key": key(c), "label": model_label(c), "is_firm": c == ma.ACTUAL} for c in cols],
        "weights": [{"asset": asset, "label": display_label(asset), **{key(c): float(res.weights.loc[asset, c])
                                                                       for c in cols}}
                    for asset in res.weights.index],
        "risk_profile": [{"key": key(k), "label": model_label(k), "annual_volatility": p.ann_vol,
                          "past_return": p.ann_ret, "return_to_risk": p.ratio, "effective_assets": p.eff_n,
                          "diversification_ratio": p.div_ratio, "top_risk_asset": p.top_risk,
                          "top_risk_share": p.top_risk_share, "distance_from_firm": p.distance}
                         for k, p in res.profiles.items()],
        "risk_contributions": [{"asset": k, "label": display_label(k), "share": float(v)}
                               for k, v in res.risk_contrib.sort_values(ascending=False).items()],
        "closest_model": {"key": res.closest, "label": model_label(res.closest),
                          "distance": res.profiles[res.closest].distance} if res.closest else None,
        "paths": [{"key": key(k), "label": model_label(k), "is_firm": k == ma.ACTUAL, "is_benchmark": k == bench,
                   "points": series_points(s)} for k, s in res.paths.items()],
        "performance": [{"key": key(k), "label": model_label(k), "is_benchmark": k == bench,
                         **{f: sc.get(f) for f in ("total", "annual", "vol", "max_dd", "sharpe", "sortino", "alpha")}}
                        for k, sc in res.scores.items()],
        "decomposition": res.decomposition,
        "notes": res.notes,
        "charts": _chart_payload(res, key),
    }


def compare(a: Archive, slugs: list[str], currency: str = "TRY", benchmark: str | None = "BIST100") -> dict:
    if not 1 <= len(slugs) <= 8:
        raise ApiError(400, "Give 1–8 slugs.")
    names = [a.name_of(s) for s in slugs]
    bench = _benchmark(benchmark)
    comp = mp.compare_models({n: a.configs[n] for n in names}, a.try_prices, a.closes, currency,
                             [bench] if bench else [])
    rows = {r["name"]: r for r in comp.table}
    return a.base() | {"currency": currency, "benchmark": bench, "items": [
        {"slug": a.slug_of(n) if n in names else None, "name": n, "label": display_label(n),
         "is_benchmark": rows[n]["is_benchmark"], "provider": rows[n]["provider"],
         "metrics": {k: rows[n].get(k) for k in ("1G", "1H", "1A", "3A", "YB", "1Y", "total", "annual", "vol",
                                                  "max_dd")},
         "points": series_points(s)} for n, s in comp.indices.items()],
        "warnings": comp.warnings}


# --- Model analizi laboratuvarı (istek üzerine hesap) -------------------------------------------------------

LAB_SLOTS = threading.BoundedSemaphore(int(os.environ.get("PM_LAB_CONCURRENCY", "2")))
LAB_WAIT = 30  # sn: boş hesap yuvası beklenir, sonra 503
_lab_cache: dict[str, Any] = {}
_lab_lock = threading.Lock()
LAB_CACHE_SIZE = 64


def _lab_cached(key: str, fn):
    with _lab_lock:
        if key in _lab_cache:
            _lab_cache[key] = _lab_cache.pop(key)  # LRU: en sona taşı
            return _lab_cache[key]
    out = fn()
    with _lab_lock:
        _lab_cache[key] = out
        while len(_lab_cache) > LAB_CACHE_SIZE:
            _lab_cache.pop(next(iter(_lab_cache)))
    return out


def _lab_inputs(body: dict):
    from . import lab

    start = body.get("start") or f"{pd.Timestamp(date.today()) - pd.DateOffset(years=3):%Y-%m-%d}"
    end = body.get("end") or None
    key = json.dumps([sorted(body.get("symbols") or []), sorted(body.get("bist_symbols") or []), start, end,
                      f"{date.today()}"])
    prices, returns, missing = _lab_cached("data:" + key, lambda: lab.load(body.get("symbols"), body.get("bist_symbols"),
                                                                           start, end))
    mw = body.get("max_weight_pct")
    max_weight = None if mw in (None, "", 100) else float(mw) / 100
    if max_weight is not None and not 0.05 <= max_weight <= 1:
        raise ApiError(400, "max_weight_pct must be between 5 and 100.")
    return prices, returns, missing, max_weight


def lab_models(body: dict) -> dict:
    from . import lab, model_guide

    return {"models": lab.model_list(), "defaults": lab.DEFAULT_MODELS, "max_symbols": lab.MAX_SYMBOLS,
            "metrics_guide": model_guide.metrics_markdown()}


def lab_optimize(body: dict) -> dict:
    from . import lab

    prices, returns, missing, max_weight = _lab_inputs(body)
    models = lab.check_models(body.get("models"))
    return {"missing_symbols": missing, "data": lab.data_view(prices, returns),
            "result": lab.optimize(returns, models, max_weight)}


def lab_backtest(body: dict) -> dict:
    from . import lab

    _, returns, missing, max_weight = _lab_inputs(body)
    models = lab.check_models(body.get("models"))
    return {"missing_symbols": missing, "result": lab.run_backtest(returns, models, int(body.get("train", 252)),
                                                                   int(body.get("test", 21)), max_weight)}


def lab_black_litterman(body: dict) -> dict:
    from . import lab

    _, returns, missing, _ = _lab_inputs(body)
    return {"missing_symbols": missing,
            "result": lab.black_litterman(returns, body.get("views") or [], float(body.get("tau", 0.05)))}


# --- Starlette uygulaması ---------------------------------------------------------------------------------


def create_app(archive: Archive | None = None, background: bool = True):
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.middleware.gzip import GZipMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    arc = archive or Archive()
    try:
        app_version = _pkg_version("portfolio-models")
    except Exception:  # noqa: BLE001
        app_version = "dev"

    def endpoint(fn, *path_args, cacheable=True):
        def handler(request: Request):
            q = dict(request.query_params)
            lang = q.pop("lang", "tr")
            set_lang(lang if lang in ("tr", "en", "de") else "tr")
            try:
                arc.ensure()
                kwargs = {p: request.path_params[p] for p in path_args} | q
                if "slugs" in kwargs:
                    kwargs["slugs"] = [s for s in kwargs["slugs"].split(",") if s]
                key = (fn.__name__, lang, tuple(sorted((k, str(v)) for k, v in kwargs.items())))
                body = arc.cached(key, lambda: clean(fn(arc, **kwargs))) if cacheable else clean(fn(arc, **kwargs))
            except ApiError as e:
                return JSONResponse({"error": str(e)}, status_code=e.status)
            except TypeError as e:
                return JSONResponse({"error": f"Bad parameters: {e}"}, status_code=400)
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            except Exception:  # noqa: BLE001
                log.exception("API error")
                return JSONResponse({"error": "Internal error"}, status_code=500)
            return JSONResponse(body, headers={"Cache-Control": "public, max-age=300"})

        return handler

    def lab_endpoint(fn, heavy=True):
        from starlette.concurrency import run_in_threadpool

        async def handler(request: Request):
            lang = request.query_params.get("lang", "tr")
            lang = lang if lang in ("tr", "en", "de") else "tr"
            if request.method == "POST":
                raw = await request.body()
                if len(raw) > 20_000:
                    return JSONResponse({"error": "Request too large."}, status_code=413)
                try:
                    body = json.loads(raw or b"{}")
                    assert isinstance(body, dict)
                except Exception:  # noqa: BLE001
                    return JSONResponse({"error": "Body must be a JSON object."}, status_code=400)
            else:
                body = {}

            def work():
                set_lang(lang)
                key = f"{fn.__name__}:{lang}:" + json.dumps(body, sort_keys=True, default=str) + f":{date.today()}"
                if not heavy:
                    return _lab_cached(key, lambda: clean(fn(body)))
                with _lab_lock:
                    hit = _lab_cache.get(key)
                if hit is not None:
                    return hit
                if not LAB_SLOTS.acquire(timeout=LAB_WAIT):
                    raise ApiError(503, "Busy, try again in a moment.")
                try:
                    return _lab_cached(key, lambda: clean(fn(body)))
                finally:
                    LAB_SLOTS.release()

            try:
                out = await run_in_threadpool(work)
            except ApiError as e:
                return JSONResponse({"error": str(e)}, status_code=e.status)
            except (ValueError, TypeError, KeyError) as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            except Exception:  # noqa: BLE001
                log.exception("lab error")
                return JSONResponse({"error": "Internal error"}, status_code=500)
            return JSONResponse(out)

        return handler

    def health(request: Request):
        return JSONResponse(clean({"ok": True, "version": app_version, "data_version": arc.version} | arc.base()))

    def index(request: Request):
        return JSONResponse({
            "name": "Portfolio Models API", "version": app_version,
            "docs": "https://ozanbayhan.github.io/portfolio-models/api/",
            "endpoints": ["/api/health", "/api/meta", "/api/portfolios", "/api/leaderboard",
                          "/api/portfolios/{slug}", "/api/portfolios/{slug}/analysis", "/api/analysis",
                          "/api/lab/models", "POST /api/lab/optimize", "POST /api/lab/backtest",
                          "POST /api/lab/black-litterman", "/api/compare?slugs=a,b"],
        })

    routes = [
        Route("/", index), Route("/api", index), Route("/api/health", health),
        Route("/api/meta", endpoint(meta)),
        Route("/api/portfolios", endpoint(portfolios)),
        Route("/api/leaderboard", endpoint(leaderboard)),
        Route("/api/compare", endpoint(compare)),
        Route("/api/analysis", endpoint(analysis_overview)),
        Route("/api/lab/models", lab_endpoint(lab_models, heavy=False)),
        Route("/api/lab/optimize", lab_endpoint(lab_optimize), methods=["POST"]),
        Route("/api/lab/backtest", lab_endpoint(lab_backtest), methods=["POST"]),
        Route("/api/lab/black-litterman", lab_endpoint(lab_black_litterman), methods=["POST"]),
        Route("/api/portfolios/{slug}", endpoint(detail, "slug")),
        Route("/api/portfolios/{slug}/analysis", endpoint(analysis, "slug")),
    ]
    origins = [o.strip() for o in os.environ.get("PM_API_CORS", "*").split(",") if o.strip()]
    middleware = [Middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"]),
                  Middleware(GZipMiddleware, minimum_size=1000)]

    def startup():
        if background:
            threading.Thread(target=_refresher, args=(arc,), daemon=True, name="pm-refresher").start()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        startup()
        yield

    app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
    app.state.archive = arc
    return app


def _next_refresh(now: datetime) -> datetime:
    today = [now.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in REFRESH_UTC]
    future = [t for t in today if t > now]
    if future:
        return future[0]
    h, m = REFRESH_UTC[0]
    return (now + pd.Timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)


def _warm(arc: Archive) -> None:
    """Sık istenen yanıtları önceden hesaplar (ilk ziyaretçi beklemesin)."""
    set_lang("tr")
    for cur in CURRENCIES:
        for fn, kw in ((portfolios, {"currency": cur}), (leaderboard, {"currency": cur})):
            key = (fn.__name__, "tr", tuple(sorted((k, str(v)) for k, v in kw.items())))
            arc.cached(key, lambda fn=fn, kw=kw: clean(fn(arc, **kw)))
    for cur in CURRENCIES:
        key = ("analysis_overview", "tr", (("currency", cur),))
        try:
            arc.cached(key, lambda cur=cur: clean(analysis_overview(arc, currency=cur)))
        except Exception:  # noqa: BLE001
            log.exception("warm-up failed for overview %s", cur)
    for slug in list(arc.slugs):
        key = ("analysis", "tr", (("slug", slug),))
        try:
            arc.cached(key, lambda slug=slug: clean(analysis(arc, slug)))
        except Exception:  # noqa: BLE001
            log.exception("warm-up failed for %s", slug)


def _refresher(arc: Archive) -> None:
    set_lang("tr")
    nxt = _next_refresh(datetime.now(timezone.utc))
    first = True
    while True:
        try:
            now = datetime.now(timezone.utc)
            due = now >= nxt
            if arc.refresh(force=due or first) or first:
                _warm(arc)
            if due:
                nxt = _next_refresh(now)
            first = False
        except Exception:  # noqa: BLE001
            log.exception("refresh failed; retrying later")
        time.sleep(CHECK_EVERY)


def run(host: str = "127.0.0.1", port: int = 8770) -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    set_lang("tr")
    uvicorn.run(create_app(), host=host, port=port, proxy_headers=True, forwarded_allow_ips="*",
                log_level="info")
