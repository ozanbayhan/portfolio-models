"""Model sonuçları için veriye dayalı yorumlar (TR / EN / DE).

Yorumlar kural tabanlıdır: her cümle ekrandaki sayılardan (ağırlıklar, getiriler, kovaryans,
backtest özeti) hesaplanan bir ölçüye dayanır. Dış servis ya da yapay zekâ çağrısı yoktur.
Model açıklamaları ve uyarıları `model_guide` modülünden gelir.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import model_guide
from .holdings import display_label
from .i18n import get_lang, t

TRADING_DAYS = 252

# Geçmiş getiri tahminine güçlü biçimde dayanan modeller
RETURN_SENSITIVE = {"max_sharpe", "max_sortino", "riskfolio_max_sharpe_cvar", "pypfopt_max_sharpe"}


def _dec(s: str) -> str:
    return s if get_lang() == "en" else s.replace(".", ",")


def pct(x: float, digits: int = 1, sign: bool = False) -> str:
    """Dile göre yüzde: TR '%12,3', EN '12.3%', DE '12,3 %'."""
    if x is None or not np.isfinite(x):
        return "—"
    body = _dec(f"{abs(x) * 100:.{digits}f}")
    prefix = ("+" if x >= 0 else "−") if sign else ("−" if x < 0 else "")
    lang = get_lang()
    if lang == "tr":
        return f"{prefix}%{body}"
    if lang == "de":
        return f"{prefix}{body} %"
    return f"{prefix}{body}%"


def num(x: float, digits: int = 2) -> str:
    """Dile göre ondalık: TR/DE '1,92', EN '1.92'."""
    if x is None or not np.isfinite(x):
        return "—"
    return _dec(f"{x:.{digits}f}")


def pp(x: float) -> str:
    """Yüzde puan farkı: '+3,5 puan' / '+3.5 pp' / '+3,5 Prozentpunkte'."""
    if x is None or not np.isfinite(x):
        return "—"
    return f"{'+' if x >= 0 else '−'}{_dec(f'{abs(x) * 100:.1f}')} " + t("puan")


def _join(items: list[str]) -> str:
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + t(" ve ") + items[-1]


@dataclass
class WeightMetrics:
    top: str
    top_w: float
    top3_w: float
    eff_n: float  # etkin varlık sayısı: 1 / Σw²
    n_used: int  # %1'den fazla pay alan varlık sayısı
    excluded: list[str]
    ann_ret: float
    ann_vol: float
    sharpe: float
    top_risk: str
    top_risk_share: float
    div_ratio: float


def weight_metrics(w: pd.Series, returns: pd.DataFrame) -> WeightMetrics:
    w = w.reindex(returns.columns).fillna(0.0)
    w = w / w.sum() if w.sum() else w
    mu = returns.mean() * TRADING_DAYS
    cov = returns.cov() * TRADING_DAYS
    var = float(w @ cov @ w)
    vol = float(np.sqrt(max(var, 0.0)))
    rc = (w * (cov @ w)) / var if var > 0 else w * 0
    sigma = np.sqrt(np.diag(cov))
    ranked = w.sort_values(ascending=False)
    return WeightMetrics(
        top=str(ranked.index[0]), top_w=float(ranked.iloc[0]), top3_w=float(ranked.iloc[:3].sum()),
        eff_n=float(1 / (w ** 2).sum()) if (w ** 2).sum() else 0.0,
        n_used=int((w > 0.01).sum()), excluded=[str(a) for a in w[w < 0.005].index],
        ann_ret=float(w @ mu), ann_vol=vol, sharpe=float(w @ mu) / vol if vol else float("nan"),
        top_risk=str(rc.idxmax()), top_risk_share=float(rc.max()),
        div_ratio=float((w * sigma).sum() / vol) if vol else float("nan"),
    )


def _concentration_label(eff_n: float, n: int) -> str:
    ratio = eff_n / n if n else 0
    if ratio >= 0.75:
        return t("yüksek (dengeli dağılım)")
    if ratio >= 0.45:
        return t("orta")
    return t("düşük (birkaç varlığa yoğunlaşmış)")


def model_comment(name: str, w: pd.Series, returns: pd.DataFrame, baseline: WeightMetrics | None = None) -> str:
    """Tek bir modelin ağırlıkları için madde madde yorum (Markdown)."""
    n = returns.shape[1]
    m = weight_metrics(w, returns)
    what = model_guide.info(name, "idea")
    caution = model_guide.info(name, "caution")
    lines = []
    if what:
        lines.append(t("**Ne yapar:** {what}", what=what))
    lines.append(t(
        "**Dağılım:** En büyük pay **{top}** ({w}); ilk 3 varlığın toplam payı {top3}. "
        "Etkin varlık sayısı **{eff}** / {n} → çeşitlendirme {label}.",
        top=m.top, w=pct(m.top_w), top3=pct(m.top3_w), eff=num(m.eff_n, 1), n=n,
        label=_concentration_label(m.eff_n, n),
    ))
    if m.excluded:
        lines.append(t("**Dışarıda bıraktığı:** {assets} (payı {limit} altında).",
                       assets=_join(m.excluded), limit=pct(0.005)))
    risk_line = t("**Risk kaynağı:** Toplam riskin {share} kadarı **{asset}** varlığından geliyor.",
                  share=pct(m.top_risk_share), asset=m.top_risk)
    if m.top_risk != m.top and m.top_risk_share > m.top_w + 0.05:
        risk_line += " " + t("Sermaye payından daha fazla risk taşıyor; oynaklığı yüksek.")
    lines.append(risk_line)
    perf = t("**Geçmiş veriye göre:** yıllık beklenen getiri ~{ret}, oynaklık ~{vol} (getiri/risk {sr}).",
             ret=pct(m.ann_ret), vol=pct(m.ann_vol), sr=num(m.sharpe))
    if baseline is not None and name != "equal_weighted":
        dv = m.ann_vol - baseline.ann_vol
        dr = m.ann_ret - baseline.ann_ret
        if dv < 0 and dr > 0:
            verdict = t("daha az riskle daha fazla getiri.")
        elif dv < 0:
            verdict = t("daha az risk, daha az getiri.")
        elif dr > 0:
            verdict = t("daha fazla riskle daha fazla getiri.")
        else:
            verdict = t("daha fazla risk, daha az getiri; bu dönemde verimsiz.")
        perf += " " + t("Eşit ağırlığa göre oynaklık {dv}, getiri {dr} — {verdict}", dv=pp(dv), dr=pp(dr),
                        verdict=verdict)
    lines.append(perf)
    warn = []
    if m.top_w > 0.5:
        warn.append(t("Portföyün yarısından fazlası tek varlıkta ({asset}); o varlıktaki bir düşüş portföyü sert etkiler.",
                      asset=m.top))
    if caution:
        warn.append(caution)
    if warn:
        lines.append(t("**Dikkat:** ") + " ".join(warn))
    return "\n\n".join(lines)


def asset_facts(returns: pd.DataFrame) -> list[str]:
    """Varlık düzeyinde, model davranışını açıklayan gözlemler."""
    vol = returns.std() * np.sqrt(TRADING_DAYS)
    ret = returns.mean() * TRADING_DAYS
    facts = [
        t("En sakin varlık **{calm}** (yıllık oynaklık {v1}), en oynak varlık **{wild}** ({v2}). Riski azaltmaya "
          "çalışan modeller (min. varyans, risk paritesi, HRP) sakin varlığa yönelir.",
          calm=vol.idxmin(), v1=pct(vol.min()), wild=vol.idxmax(), v2=pct(vol.max())),
        t("Dönemin en yüksek ortalama getirisi: **{best}** ({r1}/yıl); en düşüğü: **{worst}** ({r2}/yıl). "
          "Getiri odaklı modeller (maks. Sharpe/Sortino) ilkine yüklenir.",
          best=ret.idxmax(), r1=pct(ret.max()), worst=ret.idxmin(), r2=pct(ret.min())),
    ]
    if returns.shape[1] >= 2:
        corr = returns.corr()
        mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
        pairs = corr.where(mask).stack()
        hi, lo = pairs.idxmax(), pairs.idxmin()
        facts.append(t(
            "En çok birlikte hareket eden ikili **{a} – {b}** (korelasyon {c1}); en bağımsız ikili **{d} – {e}** ({c2}). "
            "Düşük korelasyonlu varlıklar çeşitlendirmenin asıl kaynağıdır.",
            a=hi[0], b=hi[1], c1=num(pairs.max()), d=lo[0], e=lo[1], c2=num(pairs.min()),
        ))
    return facts


def consensus(weights: pd.DataFrame) -> list[str]:
    """Modellerin ortak görüşü: çoğunun fazla/az ağırlık verdiği varlıklar ve en çok ayrıştıkları varlık."""
    if weights.empty or weights.shape[1] < 2:
        return []
    n = weights.shape[0]
    eq = 1 / n
    over = (weights > eq * 1.2).sum(axis=1)
    under = (weights < eq * 0.5).sum(axis=1)
    k = weights.shape[1]
    need = max(2, int(np.ceil(k * 0.6)))
    out = []
    fav = over[over >= need].sort_values(ascending=False)
    if len(fav):
        out.append(t("Modellerin çoğu şu varlıklara eşit ağırlıktan ({eq}) fazla pay öneriyor: **{assets}** "
                     "({k} modelden {counts}).",
                     eq=pct(eq), assets=_join(list(fav.index)), k=k, counts=_join([str(int(v)) for v in fav.values])))
    avoid = under[under >= need].sort_values(ascending=False)
    if len(avoid):
        out.append(t("Çoğunluk şu varlıklara düşük pay veriyor: **{assets}**.", assets=_join(list(avoid.index))))
    spread = weights.max(axis=1) - weights.min(axis=1)
    a = spread.idxmax()
    out.append(t("Modeller en çok **{asset}** konusunda ayrışıyor: payı {lo} ile {hi} arasında değişiyor. "
                 "Bu varlık için seçtiğiniz model sonucu belirler.",
                 asset=a, lo=pct(weights.loc[a].min()), hi=pct(weights.loc[a].max())))
    avg = weights.mean(axis=1).sort_values(ascending=False)
    out.append(t("Tüm modellerin ortalaması: {items}.", items=", ".join(f"{i} {pct(v)}" for i, v in avg.items())))
    return out


def backtest_comment(table: pd.DataFrame) -> list[str]:
    """summarize() çıktısı (satır: model) için yorum. Sütun adları dile göre değişebilir."""
    if table is None or table.empty:
        return []
    cols = {c: c for c in table.columns}
    sharpe_c = next((c for c in cols if c in ("Sharpe",)), None)
    ret_c = next((c for c in cols if c in (t("Yıllık getiri"), "Yıllık getiri")), None)
    dd_c = next((c for c in cols if c in (t("Maks. düşüş"), "Maks. düşüş")), None)
    if sharpe_c is None:
        return []
    tb = table.dropna(subset=[sharpe_c])
    if tb.empty:
        return []
    out = []
    best, worst = tb[sharpe_c].idxmax(), tb[sharpe_c].idxmin()
    out.append(t("Risk ayarlı en iyi sonuç **{best}** (Sharpe {s1}); en zayıf **{worst}** ({s2}).",
                 best=best, s1=num(tb.loc[best, sharpe_c]), worst=worst, s2=num(tb.loc[worst, sharpe_c])))
    if ret_c:
        top_r = tb[ret_c].idxmax()
        line = t("En yüksek yıllık getiri: **{model}** ({r}).", model=top_r, r=pct(tb.loc[top_r, ret_c]))
        if dd_c:
            line += " " + t("Bu modelde en derin düşüş {dd} oldu.", dd=pct(tb.loc[top_r, dd_c]))
        out.append(line)
    if dd_c:
        safe = tb[dd_c].idxmin()
        line = t("En sığ düşüş: **{model}** ({dd}).", model=safe, dd=pct(tb.loc[safe, dd_c]))
        if ret_c:
            line += " " + t("Karşılığında yıllık getiri {r}.", r=pct(tb.loc[safe, ret_c]))
        out.append(line)
    if "equal_weighted" in tb.index:
        ew = tb.loc["equal_weighted", sharpe_c]
        beat = [m for m in tb.index if m != "equal_weighted" and tb.loc[m, sharpe_c] > ew]
        others = len(tb) - 1
        if others:
            if not beat:
                out.append(t("Hiçbir model basit eşit ağırlığı (1/N) risk ayarlı olarak geçemedi; bu varlık setinde "
                             "optimizasyon ek değer katmıyor."))
            else:
                line = t("{others} modelden {n} tanesi eşit ağırlığı (Sharpe {ew}) geçti.", others=others, n=len(beat),
                         ew=num(ew))
                if tb.loc[best, sharpe_c] - ew < 0.1:
                    line += " " + t("Fark küçük (0,10'dan az); basit 1/N kadar iyi sayılabilir.")
                out.append(line)
    if len(tb) >= 3 and tb[sharpe_c].max() - tb[sharpe_c].min() < 0.15:
        out.append(t("Modellerin sonuçları birbirine çok yakın; model seçimi bu varlıklarda kritik değil."))
    if best in RETURN_SENSITIVE:
        out.append(t("Not: {model} geçmiş getiriye duyarlı bir model; bu dönemdeki başarısı bir sonraki dönemde "
                     "tekrar etmeyebilir. Farklı başlangıç tarihleriyle tekrar deneyin.", model=best))
    out.append(t("Backtest geçmiş veriye dayanır; komisyon, vergi ve kaymayı içermez. Gelecek performansı garanti etmez."))
    return out


def black_litterman_comment(base: pd.Series, bl: pd.Series, views: list[str]) -> list[str]:
    diff = (bl - base).sort_values()
    out = []
    up = diff[diff > 0.01].sort_values(ascending=False)
    down = diff[diff < -0.01]
    if len(up):
        out.append(t("Görüşleriniz şu varlıkların payını artırdı: {items}.",
                     items=", ".join(f"**{a}** ({pct(base[a])} → {pct(bl[a])})" for a in up.index[:4])))
    if len(down):
        out.append(t("Payı azalanlar: {items}.",
                     items=", ".join(f"**{a}** ({pct(base[a])} → {pct(bl[a])})" for a in down.index[:4])))
    if not len(up) and not len(down):
        out.append(t("Görüşleriniz ağırlıkları kayda değer biçimde değiştirmedi; ya geçmiş veriyle uyumlu ya da güven "
                     "(tau) düşük. Güveni artırarak etkisini görebilirsiniz."))
    turnover = float((bl - base).abs().sum() / 2)
    out.append(t("Görüşlerin portföyde yol açtığı toplam değişim: {x}.", x=pct(turnover)))
    return out


def rebalance_comment(reb: pd.DataFrame, model: str, cols: dict | None = None) -> list[str]:
    """Portföyüm sayfasındaki yeniden dengeleme tablosu için yorum.

    cols: tablo sütun adları çevrildiyse eşleme (varsayılan Türkçe adlar).
    """
    if reb is None or reb.empty:
        return []
    c = {"asset": "Varlık", "cur": "Mevcut ağırlık", "tgt": "Hedef ağırlık", "side": "İşlem"} | (cols or {})
    out = []
    what = model_guide.info(model, "idea")
    if what:
        out.append(f"**{model}:** {what}")
    gap = reb[c["tgt"]] - reb[c["cur"]]
    buys = reb[gap > 0].assign(g=gap).sort_values("g", ascending=False)
    sells = reb[gap < 0].assign(g=gap).sort_values("g")
    if len(buys):
        b = buys.iloc[0]
        out.append(t("En büyük açık: **{asset}** — şu an {cur}, model {tgt} öneriyor.",
                     asset=display_label(b[c["asset"]]), cur=pct(b[c["cur"]]), tgt=pct(b[c["tgt"]])))
    if len(sells):
        s = sells.iloc[0]
        out.append(t("En fazla azaltılması önerilen: **{asset}** ({cur} → {tgt}).",
                     asset=display_label(s[c["asset"]]), cur=pct(s[c["cur"]]), tgt=pct(s[c["tgt"]])))
    drift = float(gap.abs().sum() / 2)
    if drift < 0.05:
        out.append(t("Portföyünüz bu modele zaten çok yakın (sapma {d}); işlem yapmaya değmeyebilir.", d=pct(drift)))
    elif drift < 0.15:
        out.append(t("Orta düzey sapma ({d}). Küçük işlemleri komisyon maliyetine göre atlamayı düşünebilirsiniz.",
                     d=pct(drift)))
    else:
        out.append(t("Sapma yüksek ({d}). Önerinin tamamını tek seferde uygulamak yerine kademeli geçiş daha az "
                     "maliyetli ve daha az riskli olabilir.", d=pct(drift)))
    return out
