"""Model portföylerin matematiksel analizi: optimizasyon modelleriyle karşılaştırma ve sıralama ölçütleri.

İki soru yanıtlanır:

1. **Bu portföy optimizasyon modellerinin gözünden nasıl görünüyor?** Her revizyon tarihinde, o güne kadarki
   (en çok 1 yıllık) getirilerle aynı varlıklara modeller uygulanır. Kurumun ağırlıkları ile modellerin ağırlıkları
   risk profili (oynaklık, çeşitlendirme, etkin varlık sayısı, risk katkıları) ve ağırlık farkı açısından
   karşılaştırılır. Sonra her modelin ağırlıkları, kurumun revizyon takvimiyle aynı şekilde ileriye doğru tutulur
   (al-ve-tut, revizyonda yeniden kurulur); böylece "aynı hisseleri model ağırlıklandırsaydı ne olurdu" görülür.
   Geleceğe bakış yoktur: model yalnızca revizyon tarihinden önceki veriyi görür.

2. **Sıralama ölçütleri:** getiri, riske göre getiri (Sharpe, Sortino), kıyasa göre fark (alfa, beta, takip hatası,
   bilgi oranı), isabet (revizyonlarda seçilen varlıkların kıyası geçme oranı) ve tutarlılık (ayların kaçında kıyasın
   üstünde kalındığı).

Nakit ve yeterli fiyat geçmişi olmayan varlıklar "sabit dilim"dir: modeller bunların payına dokunmaz, yalnızca
kalan riskli varlıkları yeniden ağırlıklandırır. Sharpe/Sortino risksiz faiz düşülmeden hesaplanır.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .i18n import t as T
from .model_portfolios import BENCHMARKS, KIND_MAP, index_series, label_of, metrics
from .holdings import asset_label

TRADING_DAYS = 252
LOOKBACK_DAYS = 365
MIN_OBS = 60  # model uydurmak için gereken en az günlük getiri
ANALYSIS_MODELS = ["equal_weighted", "inverse_volatility", "min_variance", "max_sharpe_shrunk", "risk_parity",
                   "hrp", "max_diversification"]
ACTUAL = "__actual__"  # sonuç tablolarında kurumun kendi portföyünü gösteren satır anahtarı


# --- Para birimi ------------------------------------------------------------------------


def in_ccy(try_prices: pd.DataFrame, closes: pd.DataFrame, currency: str) -> pd.DataFrame:
    """TL fiyat tablosunu USD/EUR'ya çevirir (her sütun kura bölünür)."""
    if currency == "TRY" or try_prices.empty:
        return try_prices
    fx = closes.get(f"{currency}TRY=X")
    if fx is None or fx.dropna().empty:
        raise ValueError(f"No {currency}TRY rate available.")
    fx = fx.reindex(try_prices.index).ffill()
    return try_prices.div(fx, axis=0)


# --- Ağırlıklar ve risk profili --------------------------------------------------------------


def _weights(holdings: list[dict]) -> pd.Series:
    return pd.Series({label_of(h): h["weight"] / 100 for h in holdings}, dtype=float)


def _window_returns(prices: pd.DataFrame, labels: list[str], as_of: pd.Timestamp,
                    lookback: int = LOOKBACK_DAYS) -> pd.DataFrame:
    cols = [c for c in labels if c in prices]
    p = prices.loc[(prices.index < as_of) & (prices.index >= as_of - pd.Timedelta(days=lookback)), cols]
    return p.ffill().pct_change(fill_method=None).iloc[1:]


def _split(w: pd.Series, rets: pd.DataFrame) -> tuple[list[str], list[str]]:
    """(modellenebilir varlıklar, sabit dilim): sabit = nakit, fiyatsız ya da yetersiz geçmişli, oynaklığı sıfır."""
    free, fixed = [], []
    for a in w.index:
        s = rets[a].dropna() if a in rets else pd.Series(dtype=float)
        (free if len(s) >= MIN_OBS and s.std() > 1e-10 else fixed).append(a)
    return free, fixed


def fit_models(w: pd.Series, rets: pd.DataFrame, models: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Kurumun ağırlıkları (ACTUAL sütunu) ve her modelin aynı varlıklar için ağırlıkları (satır = varlık)."""
    from .backtest import fit_weights

    free, fixed = _split(w, rets)
    out = pd.DataFrame({ACTUAL: w})
    notes: list[str] = []
    if fixed:
        notes.append(T("Modeller şu varlıkların payına dokunmadı (nakit ya da yetersiz fiyat geçmişi): {a}.",
                       a=", ".join(fixed)))
    if len(free) < 2:
        notes.append(T("Modellenebilir en az iki varlık gerekli; model karşılaştırması yapılamadı."))
        return out, notes
    free_share = float(w[free].sum())
    errors: dict[str, str] = {}
    fitted = fit_weights(rets[free].dropna(), models, on_error=lambda n, e: errors.__setitem__(n, str(e)))
    for m in fitted.columns:
        col = pd.Series(0.0, index=w.index)
        col[free] = fitted[m].clip(lower=0) / fitted[m].clip(lower=0).sum() * free_share
        col[fixed] = w[fixed]
        out[m] = col
    if errors:
        notes.append(T("Çalışmayan modeller: {m}.", m=", ".join(errors)))
    return out, notes


@dataclass
class RiskProfile:
    ann_ret: float | None  # geçmiş ortalama getiri (yıllık) — tahmin değil
    ann_vol: float | None
    ratio: float | None  # getiri / oynaklık
    eff_n: float  # etkin varlık sayısı 1/Σw²
    div_ratio: float | None  # çeşitlendirme oranı Σwσ / σp
    top_risk: str | None
    top_risk_share: float | None
    distance: float  # kurumun ağırlıklarından farkı: ½Σ|w−a| (portföyün yüzde kaçı farklı)


def risk_profile(w: pd.Series, rets: pd.DataFrame, actual: pd.Series) -> RiskProfile:
    dist = float(0.5 * (w.reindex(actual.index).fillna(0) - actual).abs().sum())
    eff_n = float(1 / (w ** 2).sum()) if (w ** 2).sum() else 0.0
    r = rets.reindex(columns=w.index).fillna(0.0)
    if len(r) < MIN_OBS:
        return RiskProfile(None, None, None, eff_n, None, None, None, dist)
    mu = r.mean() * TRADING_DAYS
    cov = r.cov() * TRADING_DAYS
    var = float(w @ cov @ w)
    vol = math.sqrt(max(var, 0.0))
    rc = (w * (cov @ w)) / var if var > 0 else w * 0
    sigma = np.sqrt(np.diag(cov))
    ret = float(w @ mu)
    return RiskProfile(ret, vol, ret / vol if vol else None, eff_n,
                       float((w * sigma).sum() / vol) if vol else None,
                       str(rc.idxmax()) if var > 0 else None, float(rc.max()) if var > 0 else None, dist)


def risk_contributions(w: pd.Series, rets: pd.DataFrame) -> pd.Series:
    """Her varlığın toplam portföy varyansına katkı payı (toplam = 1)."""
    r = rets.reindex(columns=w.index).fillna(0.0)
    cov = r.cov()
    var = float(w @ cov @ w)
    return (w * (cov @ w)) / var if var > 0 else w * 0


# --- Karşı-olgusal yollar: "aynı varlıkları model ağırlıklandırsaydı" ------------------------------


def counterfactual_configs(cfg: dict, prices: pd.DataFrame, models: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Her model için, kurumun revizyon tarihlerinde o tarihe kadarki veriyle yeniden ağırlıklandırılmış config."""
    revs = cfg.get("revisions", [])
    out = {m: {"revisions": []} for m in models}
    notes: list[str] = []
    for rev in revs:
        d = pd.Timestamp(rev["date"])
        w = _weights(rev["holdings"])
        by_label = {label_of(h): h for h in rev["holdings"]}
        rets = _window_returns(prices, list(w.index), d)
        table, n = fit_models(w, rets, models)
        notes += [f"{rev['date']}: {x}" for x in n]
        for m in models:
            if m not in table:
                continue
            hs = [by_label[a] | {"weight": float(v) * 100} for a, v in table[m].items() if v > 1e-6]
            out[m]["revisions"].append({"date": rev["date"], "holdings": hs})
    return {m: c for m, c in out.items() if c["revisions"]}, notes


# --- Sıralama ölçütleri ----------------------------------------------------------------------


def _ann(x: float, days: int) -> float | None:
    return (1 + x) ** (365 / days) - 1 if days >= 90 and x > -1 else None


def scorecard(s: pd.Series, bench: pd.Series | None = None, cfg: dict | None = None,
              prices: pd.DataFrame | None = None, bench_label: str | None = None) -> dict:
    """Bir endeks serisi için sıralamada kullanılan tüm ölçütler (oranlar 0–1, yüzde değil)."""
    s = s.dropna()
    out = metrics(s) | {k: None for k in ("sharpe", "sortino", "alpha", "beta", "tracking_error", "info_ratio",
                                          "hit_rate", "monthly_win", "bench_total")}
    if len(s) < 2:
        return out
    r = s.pct_change().dropna()
    if len(r) >= 20:
        sd = r.std()
        down = r[r < 0].std()
        out["sharpe"] = float(r.mean() / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else None
        out["sortino"] = float(r.mean() / down * math.sqrt(TRADING_DAYS)) if down and down > 0 else None
    if bench is None or bench.dropna().empty:
        return out
    b = bench.dropna().reindex(s.index).ffill().dropna()
    s2 = s.reindex(b.index)
    if len(b) < 2:
        return out
    days = (b.index[-1] - b.index[0]).days
    tp, tb = float(s2.iloc[-1] / s2.iloc[0] - 1), float(b.iloc[-1] / b.iloc[0] - 1)
    out["bench_total"] = tb
    ap, ab = _ann(tp, days), _ann(tb, days)
    out["alpha"] = ap - ab if ap is not None and ab is not None else None
    rp, rb = s2.pct_change().dropna(), b.pct_change().dropna()
    if len(rp) >= 20 and rb.var() > 0:
        out["beta"] = float(rp.cov(rb) / rb.var())
        diff = rp - rb
        te = float(diff.std() * math.sqrt(TRADING_DAYS))
        out["tracking_error"] = te
        out["info_ratio"] = float(diff.mean() * TRADING_DAYS / te) if te > 0 else None
    mp, mb = s2.resample("ME").last().pct_change().dropna(), b.resample("ME").last().pct_change().dropna()
    if len(mp) >= 3:
        out["monthly_win"] = float((mp > mb.reindex(mp.index)).mean())
    if cfg is not None and prices is not None and bench_label in prices:
        out["hit_rate"] = hit_rate(cfg, prices, bench_label)
    return out


def hit_rate(cfg: dict, prices: pd.DataFrame, bench_label: str) -> float | None:
    """Revizyonlarda seçilen (nakit dışı) varlıkların, tutuldukları dönemde kıyası geçme oranı."""
    revs = cfg.get("revisions", [])
    p = prices.sort_index().ffill()
    hits = total = 0
    for i, rev in enumerate(revs):
        start = pd.Timestamp(rev["date"])
        end = pd.Timestamp(revs[i + 1]["date"]) if i + 1 < len(revs) else p.index[-1]
        seg = p[(p.index >= start) & (p.index <= end)]
        if len(seg) < 2 or (seg.index[-1] - seg.index[0]).days < 7:
            continue
        rb = seg[bench_label].iloc[-1] / seg[bench_label].iloc[0] - 1
        for h in rev["holdings"]:
            if h["kind"] == "cash":
                continue
            lab = label_of(h)
            if lab not in seg or seg[lab].isna().iloc[0]:
                continue
            total += 1
            hits += int(seg[lab].iloc[-1] / seg[lab].iloc[0] - 1 > rb)
    return hits / total if total else None


def bench_label_of(name: str) -> str:
    kind, sym = BENCHMARKS[name]
    return asset_label(KIND_MAP[kind], sym)


# --- Tek portföy analizi ---------------------------------------------------------------------


@dataclass
class Analysis:
    as_of: str  # incelenen revizyonun tarihi
    weights: pd.DataFrame  # satır = varlık, sütun = ACTUAL + modeller (0–1)
    profiles: dict[str, RiskProfile]  # ACTUAL + modeller
    risk_contrib: pd.Series  # kurumun portföyünde varlıkların risk payı
    closest: str | None  # ağırlıkça en yakın model
    paths: dict[str, pd.Series]  # ACTUAL + modeller + kıyas: ilk revizyondan bu yana endeks (100)
    scores: dict[str, dict]  # aynı anahtarlar: scorecard
    decomposition: dict[str, float | None]  # seçim etkisi / ağırlık etkisi
    notes: list[str] = field(default_factory=list)


def analyze(cfg: dict, prices: pd.DataFrame, benchmark: str | None = "BIST100",
            models: list[str] | None = None, revision: int = -1) -> Analysis:
    """`prices`: görüntü para birimindeki fiyatlar (in_ccy ile çevrilmiş), sütun = varlık etiketi.

    Ağırlık/risk karşılaştırması seçilen revizyon için (varsayılan son), performans ilk revizyondan bugüne.
    """
    models = models or ANALYSIS_MODELS
    revs = cfg.get("revisions", [])
    if not revs:
        raise ValueError("Model portfolio has no revisions.")
    rev = revs[revision]
    d = pd.Timestamp(rev["date"])
    actual = _weights(rev["holdings"])
    rets = _window_returns(prices, list(actual.index), d)
    notes: list[str] = []
    if len(rets) < MIN_OBS:  # revizyon tarihinden önce yeterli veri yoksa, analiz bugüne kadarki son 1 yılla yapılır
        rets = _window_returns(prices, list(actual.index), prices.index.max() + pd.Timedelta(days=1))
        notes.append(T("{d} öncesinde yeterli fiyat yok; risk profili son 1 yılın verisiyle hesaplandı.", d=rev["date"]))
    table, n = fit_models(actual, rets, models)
    notes += n
    profiles = {c: risk_profile(table[c], rets, actual) for c in table.columns}
    model_cols = [c for c in table.columns if c != ACTUAL]
    closest = min(model_cols, key=lambda c: profiles[c].distance) if model_cols else None

    s, w = index_series(cfg, prices)
    notes += w
    paths: dict[str, pd.Series] = {ACTUAL: s}
    cf, n = counterfactual_configs(cfg, prices, [c for c in model_cols])
    notes += [x for x in n if x not in notes]
    for m, c in cf.items():
        ms, _ = index_series(c, prices)
        if not ms.empty:
            paths[m] = ms
    blabel = bench_label_of(benchmark) if benchmark else None
    bench = None
    if blabel and blabel in prices and not s.empty:
        b = prices[blabel].dropna()
        b = b[b.index >= s.index[0]]
        if not b.empty:
            bench = b / b.iloc[0] * 100
            paths[benchmark] = bench
    scores = {k: scorecard(v, bench, cfg if k == ACTUAL else None, prices, blabel)
              for k, v in paths.items() if k != benchmark}
    if bench is not None:
        scores[benchmark] = scorecard(bench)

    act = scores[ACTUAL].get("total")
    ew = scores.get("equal_weighted", {}).get("total")
    bt = scores[ACTUAL].get("bench_total")
    decomposition = {
        "selection": ew - bt if ew is not None and bt is not None else None,  # aynı varlıklar eşit ağırlıkla − kıyas
        "weighting": act - ew if act is not None and ew is not None else None,  # kurumun ağırlıkları − eşit ağırlık
        "total_vs_benchmark": act - bt if act is not None and bt is not None else None,
    }
    return Analysis(rev["date"], table, profiles, risk_contributions(actual, rets), closest, paths, scores,
                    decomposition, sorted(set(notes), key=notes.index))


# --- Sıralama (keşfet / lider tablosu) ---------------------------------------------------------

RANKINGS = {
    # anahtar: (ölçüt, büyük daha iyi mi)
    "return": ("total", True),
    "risk_adjusted": ("sharpe", True),
    "alpha": ("alpha", True),
    "hit_rate": ("hit_rate", True),
    "consistency": ("monthly_win", True),
    "drawdown": ("max_dd", True),  # düşüş negatif; en küçük düşüş = en büyük değer
    "volatility": ("vol", False),
}


def leaderboard(configs: dict[str, dict], prices: pd.DataFrame, benchmark: str | None = "BIST100",
                window=None) -> pd.DataFrame:
    """Her model portföy için scorecard; satır = portföy. `window`: None (başlangıçtan beri) ya da gün sayısı / 'ytd'.

    Pencere verilirse tüm portföyler aynı tarihten başlatılır (adil kıyas); o tarihten sonra başlayanlar dışarıda kalır.
    """
    from .model_portfolios import window_start

    blabel = bench_label_of(benchmark) if benchmark else None
    rows = []
    for name, cfg in configs.items():
        s, _ = index_series(cfg, prices)
        if s.empty:
            continue
        if window is not None:
            start = window_start(prices.index, window)
            if s.index[0] > start + pd.Timedelta(days=3):
                continue
            s = s[s.index >= start]
        bench = None
        if blabel and blabel in prices:
            b = prices[blabel].dropna()
            bench = b[b.index >= s.index[0]]
        sc = scorecard(s, bench, cfg, prices, blabel)
        rows.append({"name": name, "provider": cfg.get("provider"), "country": cfg.get("country"),
                     "updated": cfg["revisions"][-1]["date"], "revisions": len(cfg["revisions"]),
                     "n_assets": len(cfg["revisions"][-1]["holdings"])} | sc)
    return pd.DataFrame(rows).set_index("name") if rows else pd.DataFrame()


def rank(table: pd.DataFrame, by: str) -> pd.DataFrame:
    """Lider tablosunu bir sıralamaya göre dizer; değeri olmayanlar sona."""
    col, higher = RANKINGS[by]
    if table.empty or col not in table:
        return table
    return table.sort_values(col, ascending=not higher, na_position="last")
