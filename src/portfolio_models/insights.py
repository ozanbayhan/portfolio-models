"""Model sonuçları için veriye dayalı Türkçe yorumlar.

Yorumlar kural tabanlıdır: her cümle ekrandaki sayılardan (ağırlıklar, getiriler, kovaryans,
backtest özeti) hesaplanan bir ölçüye dayanır. Dış servis ya da yapay zekâ çağrısı yoktur.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# Her modelin ne yaptığı ve neye dikkat etmek gerektiği
MODEL_INFO: dict[str, tuple[str, str]] = {
    "equal_weighted": ("Her varlığa eşit pay verir; tahmin yapmaz.",
                       "Basit ama güçlü bir kıyas noktasıdır; diğer modeller bunu geçemiyorsa karmaşıklık değer katmıyor."),
    "inverse_volatility": ("Oynaklığı düşük varlığa daha çok pay verir.",
                           "Korelasyonları hesaba katmaz; birbirine çok benzeyen varlıklar birlikte fazla ağırlık alabilir."),
    "min_variance": ("Toplam oynaklığı en aza indiren dağılımı arar (Markowitz).",
                     "Getiri tahmini kullanmaz, bu yüzden görece sağlamdır; ama düşük oynaklıklı birkaç varlığa yığılabilir."),
    "max_sharpe": ("Birim risk başına getiriyi (Sharpe) en yükseğe çıkarır.",
                   "Geçmiş ortalama getirilere çok duyarlıdır; dönem değişince ağırlıklar sert değişebilir (aşırı uyum riski)."),
    "max_sharpe_shrunk": ("Maks. Sharpe'ın büzülmüş (shrinkage) tahminlerle daha temkinli sürümü.",
                          "Uç tahminleri yumuşattığı için klasik maks. Sharpe'tan genellikle daha dengeli dağılır."),
    "max_sortino": ("Yalnızca aşağı yönlü oynaklığı risk sayarak getiri/risk oranını en yükseğe çıkarır.",
                    "Yükseliş dalgalanmasını cezalandırmaz; maks. Sharpe gibi geçmiş getiriye duyarlıdır."),
    "min_cvar": ("En kötü %5'lik günlerin ortalama kaybını (CVaR) en aza indirir.",
                 "Kuyruk riskine odaklanır; sakin dönemlerde min. varyansa benzer sonuç verir."),
    "min_cdar": ("Uzun süren düşüşlerin (drawdown) ortalama derinliğini en aza indirir.",
                 "Toparlanma süresine önem verenler için uygundur; geçmişteki düşüş dönemlerine bağımlıdır."),
    "min_max_drawdown": ("Geçmişteki en derin düşüşü en aza indirir.",
                         "Tek bir en kötü olaya göre ayarlandığı için gelecekte aynı koruma garanti değildir."),
    "max_diversification": ("Çeşitlendirme oranını (tekil riskler toplamı / portföy riski) en yükseğe çıkarır.",
                            "Birbirine az benzeyen varlıklara pay verir; getiri tahmini kullanmaz."),
    "dro_cvar": ("Dağılımsal olarak dayanıklı CVaR: veri biraz farklı olsa bile kötü senaryoya karşı korur.",
                 "Belirsizliğe karşı temkinlidir; belirsizlik payı büyüdükçe eşit ağırlığa yaklaşır."),
    "risk_parity": ("Her varlığın toplam riske katkısını eşitler.",
                    "Düşük oynaklıklı varlıklara daha çok sermaye ayırır; getiri tahmini kullanmaz."),
    "risk_parity_cvar": ("Her varlığın kuyruk riskine (CVaR) katkısını eşitler.",
                         "Sert düşüşleri olan varlıkların payını kısar."),
    "hrp": ("Hiyerarşik risk paritesi: varlıkları benzerliğe göre kümeler, riski kümeler arasında böler.",
            "Kovaryans tahmin hatalarına karşı sağlamdır; ama varlıkların oynaklıkları çok farklıysa sakin "
            "varlığa yoğunlaşabilir."),
    "hrp_cdar": ("HRP'nin düşüş (CDaR) riskine göre bölüştüren sürümü.",
                 "Uzun düşüşleri olan kümelerin payını azaltır."),
    "herc": ("Hiyerarşik eşit risk katkısı: kümelere eşit risk payı verir.",
             "Küme yapısına bağlıdır; az varlıkla sonuçları sert değişebilir."),
    "nco": ("İç içe kümeler optimizasyonu: önce küme içinde, sonra kümeler arasında optimize eder.",
            "Büyük varlık listelerinde tahmin hatasını azaltır; az varlıkta ek fayda sınırlıdır."),
    "schur": ("Schur tamamlayıcı tahsis: HRP ile min. varyans arasında bir yol izler.",
              "Hem kümeleme hem korelasyon bilgisini kullanır."),
    "stacking": ("Birkaç modelin sonucunu birleştiren topluluk (stacking) modeli.",
                 "Tek modelin hatalarını dengelemeyi hedefler; bileşenlerine bağlıdır."),
    "riskfolio_hrp": ("Riskfolio-Lib ile HRP (ward bağlantısı).", "HRP ile benzer; farklı kümeleme yöntemi kullanır."),
    "riskfolio_max_sharpe_cvar": ("Getiri / CVaR oranını en yükseğe çıkarır (Riskfolio-Lib).",
                                  "Geçmiş getiriye duyarlıdır; kuyruk riskini de hesaba katar."),
    "riskfolio_min_cdar": ("Riskfolio-Lib ile minimum CDaR.", "Uzun düşüşlere karşı korumaya odaklanır."),
    "pypfopt_max_sharpe": ("PyPortfolioOpt ile maks. Sharpe (Ledoit-Wolf kovaryans).",
                           "Kovaryansı büzerek klasik maks. Sharpe'tan biraz daha kararlıdır."),
    "pypfopt_cla_min_vol": ("Critical Line Algorithm ile minimum oynaklık.", "Min. varyansa denk sonuç verir."),
}

# Geçmiş getiri tahminine güçlü biçimde dayanan modeller
RETURN_SENSITIVE = {"max_sharpe", "max_sortino", "riskfolio_max_sharpe_cvar", "pypfopt_max_sharpe"}


def pct(x: float, digits: int = 1, sign: bool = False) -> str:
    """Türkçe yüzde: 0.123 -> '%12,3' (işaretli: '+%12,3')."""
    if x is None or not np.isfinite(x):
        return "—"
    s = f"{abs(x) * 100:.{digits}f}".replace(".", ",")
    prefix = ("+" if x >= 0 else "−") if sign else ("−" if x < 0 else "")
    return f"{prefix}%{s}"


def num(x: float, digits: int = 2) -> str:
    """Türkçe ondalık: 1.92 -> '1,92'."""
    if x is None or not np.isfinite(x):
        return "—"
    return f"{x:.{digits}f}".replace(".", ",")


def pp(x: float) -> str:
    """Yüzde puan farkı: 0.035 -> '+3,5 puan'."""
    if x is None or not np.isfinite(x):
        return "—"
    return f"{'+' if x >= 0 else '−'}{abs(x) * 100:.1f}".replace(".", ",") + " puan"


def _join(items: list[str]) -> str:
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " ve " + items[-1]


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
        return "yüksek (dengeli dağılım)"
    if ratio >= 0.45:
        return "orta"
    return "düşük (birkaç varlığa yoğunlaşmış)"


def model_comment(name: str, w: pd.Series, returns: pd.DataFrame, baseline: WeightMetrics | None = None) -> str:
    """Tek bir modelin ağırlıkları için madde madde yorum (Markdown)."""
    n = returns.shape[1]
    m = weight_metrics(w, returns)
    what, caution = MODEL_INFO.get(name, ("", ""))
    lines = []
    if what:
        lines.append(f"**Ne yapar:** {what}")
    lines.append(
        f"**Dağılım:** En büyük pay **{m.top}** ({pct(m.top_w)}); ilk 3 varlık toplamın {pct(m.top3_w)}'ini alıyor. "
        f"Etkin varlık sayısı **{num(m.eff_n, 1)}** / {n} → çeşitlendirme {_concentration_label(m.eff_n, n)}."
    )
    if m.excluded:
        lines.append(f"**Dışarıda bıraktığı:** {_join(m.excluded)} (pay %0,5'in altında).")
    risk_line = f"**Risk kaynağı:** Toplam riskin {pct(m.top_risk_share)}'i **{m.top_risk}**'dan geliyor."
    if m.top_risk != m.top and m.top_risk_share > m.top_w + 0.05:
        risk_line += " Sermaye payından daha fazla risk taşıyor; oynaklığı yüksek."
    lines.append(risk_line)
    perf = (f"**Geçmiş veriye göre:** yıllık beklenen getiri ~{pct(m.ann_ret)}, oynaklık ~{pct(m.ann_vol)} "
            f"(getiri/risk {num(m.sharpe)}).")
    if baseline is not None and name != "equal_weighted":
        dv = m.ann_vol - baseline.ann_vol
        dr = m.ann_ret - baseline.ann_ret
        perf += (f" Eşit ağırlığa göre oynaklık {pp(dv)}, getiri {pp(dr)} "
                 + ("— daha az riskle daha fazla getiri." if dv < 0 and dr > 0 else
                    "— daha az risk, daha az getiri." if dv < 0 else
                    "— daha fazla riskle daha fazla getiri." if dr > 0 else
                    "— daha fazla risk, daha az getiri; bu dönemde verimsiz." ))
    lines.append(perf)
    warn = []
    if m.top_w > 0.5:
        warn.append(f"Portföyün yarısından fazlası tek varlıkta ({m.top}); o varlıktaki bir düşüş portföyü sert etkiler.")
    if caution:
        warn.append(caution)
    if warn:
        lines.append("**Dikkat:** " + " ".join(warn))
    return "\n\n".join(lines)


def asset_facts(returns: pd.DataFrame) -> list[str]:
    """Varlık düzeyinde, model davranışını açıklayan gözlemler."""
    vol = returns.std() * np.sqrt(TRADING_DAYS)
    ret = returns.mean() * TRADING_DAYS
    facts = [
        f"En sakin varlık **{vol.idxmin()}** (yıllık oynaklık {pct(vol.min())}), en oynak **{vol.idxmax()}** "
        f"({pct(vol.max())}). Riski azaltmaya çalışan modeller (min. varyans, risk paritesi, HRP) sakin varlığa yönelir.",
        f"Dönemin en yüksek ortalama getirisi **{ret.idxmax()}**'da ({pct(ret.max())}/yıl), en düşüğü "
        f"**{ret.idxmin()}**'da ({pct(ret.min())}/yıl). Getiri odaklı modeller (maks. Sharpe/Sortino) öncekine yüklenir.",
    ]
    if returns.shape[1] >= 2:
        corr = returns.corr()
        mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
        pairs = corr.where(mask).stack()
        hi, lo = pairs.idxmax(), pairs.idxmin()
        facts.append(
            f"En çok birlikte hareket edenler **{hi[0]} – {hi[1]}** (korelasyon {num(pairs.max())}); "
            f"en bağımsız ikili **{lo[0]} – {lo[1]}** ({num(pairs.min())}). Düşük korelasyonlu varlıklar "
            "çeşitlendirmenin asıl kaynağıdır."
        )
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
    out = []
    fav = over[over >= max(2, int(np.ceil(k * 0.6)))].sort_values(ascending=False)
    if len(fav):
        out.append(f"Modellerin çoğu **{_join(list(fav.index))}** için eşit ağırlıktan ({pct(eq)}) fazla pay öneriyor "
                   f"({k} modelden {_join([str(int(v)) for v in fav.values])}).")
    avoid = under[under >= max(2, int(np.ceil(k * 0.6)))].sort_values(ascending=False)
    if len(avoid):
        out.append(f"Çoğunluk **{_join(list(avoid.index))}** için düşük pay veriyor.")
    spread = weights.max(axis=1) - weights.min(axis=1)
    a = spread.idxmax()
    out.append(f"Modeller en çok **{a}** konusunda ayrışıyor: payı {pct(weights.loc[a].min())} ile "
               f"{pct(weights.loc[a].max())} arasında değişiyor. Bu varlık için seçtiğiniz model sonucu belirler.")
    avg = weights.mean(axis=1).sort_values(ascending=False)
    out.append("Tüm modellerin ortalaması: " + ", ".join(f"{i} {pct(v)}" for i, v in avg.items()) + ".")
    return out


def backtest_comment(table: pd.DataFrame) -> list[str]:
    """summarize() çıktısı (satır: model) için yorum."""
    if table is None or table.empty or "Sharpe" not in table:
        return []
    t = table.dropna(subset=["Sharpe"])
    if t.empty:
        return []
    out = []
    best = t["Sharpe"].idxmax()
    worst = t["Sharpe"].idxmin()
    out.append(f"Risk ayarlı en iyi sonuç **{best}** (Sharpe {num(t.loc[best, 'Sharpe'])}); en zayıf "
               f"**{worst}** ({num(t.loc[worst, 'Sharpe'])}).")
    if "Yıllık getiri" in t:
        top_r = t["Yıllık getiri"].idxmax()
        line = f"En yüksek yıllık getiri **{top_r}**'da ({pct(t.loc[top_r, 'Yıllık getiri'])})"
        if "Maks. düşüş" in t:
            line += f"; bu modelde en derin düşüş {pct(t.loc[top_r, 'Maks. düşüş'])} oldu."
        out.append(line)
    if "Maks. düşüş" in t:
        safe = t["Maks. düşüş"].idxmin()
        line = f"En sığ düşüş **{safe}**'da ({pct(t.loc[safe, 'Maks. düşüş'])})"
        if "Yıllık getiri" in t:
            line += f"; karşılığında yıllık getiri {pct(t.loc[safe, 'Yıllık getiri'])}."
        out.append(line)
    if "equal_weighted" in t.index:
        ew = t.loc["equal_weighted", "Sharpe"]
        beat = [m for m in t.index if m != "equal_weighted" and t.loc[m, "Sharpe"] > ew]
        others = len(t) - 1
        if others:
            if not beat:
                out.append("Hiçbir model basit eşit ağırlığı (1/N) risk ayarlı olarak geçemedi; bu varlık setinde "
                           "optimizasyon ek değer katmıyor.")
            else:
                gap = t.loc[best, "Sharpe"] - ew
                out.append(f"{others} modelden {len(beat)} tanesi eşit ağırlığı (Sharpe {num(ew)}) geçti."
                           + (" Fark küçük (0,10'dan az); basit 1/N kadar iyi sayılabilir." if gap < 0.1 else ""))
    if len(t) >= 3 and t["Sharpe"].max() - t["Sharpe"].min() < 0.15:
        out.append("Modellerin sonuçları birbirine çok yakın; model seçimi bu varlıklarda kritik değil.")
    if best in RETURN_SENSITIVE:
        out.append(f"Not: {best} geçmiş getiriye duyarlı bir model; bu dönemdeki başarısı bir sonraki dönemde "
                   "tekrar etmeyebilir. Farklı başlangıç tarihleriyle tekrar deneyin.")
    out.append("Backtest geçmiş veriye dayanır; komisyon, vergi ve kaymayı içermez. Gelecek performansı garanti etmez.")
    return out


def black_litterman_comment(base: pd.Series, bl: pd.Series, views: list[str]) -> list[str]:
    diff = (bl - base).sort_values()
    out = []
    up = diff[diff > 0.01].sort_values(ascending=False)
    down = diff[diff < -0.01]
    if len(up):
        out.append("Görüşleriniz şu varlıkların payını artırdı: "
                   + ", ".join(f"**{a}** ({pct(base[a])} → {pct(bl[a])})" for a in up.index[:4]) + ".")
    if len(down):
        out.append("Payı azalanlar: " + ", ".join(f"**{a}** ({pct(base[a])} → {pct(bl[a])})" for a in down.index[:4]) + ".")
    if not len(up) and not len(down):
        out.append("Görüşleriniz ağırlıkları kayda değer biçimde değiştirmedi; ya geçmiş veriyle uyumlu ya da güven "
                   "(tau) düşük. Güveni artırarak etkisini görebilirsiniz.")
    turnover = float((bl - base).abs().sum() / 2)
    out.append(f"Görüşlerin portföyde yol açtığı toplam değişim: {pct(turnover)}.")
    return out


def rebalance_comment(reb: pd.DataFrame, model: str) -> list[str]:
    """Portföyüm sayfasındaki yeniden dengeleme tablosu için yorum."""
    if reb is None or reb.empty:
        return []
    out = []
    what = MODEL_INFO.get(model, ("", ""))[0]
    if what:
        out.append(f"**{model}:** {what}")
    gap = (reb["Hedef ağırlık"] - reb["Mevcut ağırlık"])
    buys = reb[(reb["İşlem"] == "Al")].assign(g=gap).sort_values("g", ascending=False)
    sells = reb[(reb["İşlem"] == "Sat")].assign(g=gap).sort_values("g")
    if len(buys):
        b = buys.iloc[0]
        out.append(f"En büyük açık **{b['Varlık']}**'da: şu an {pct(b['Mevcut ağırlık'])}, model "
                   f"{pct(b['Hedef ağırlık'])} öneriyor.")
    if len(sells):
        s = sells.iloc[0]
        out.append(f"En fazla azaltılması önerilen **{s['Varlık']}**: {pct(s['Mevcut ağırlık'])} → "
                   f"{pct(s['Hedef ağırlık'])}.")
    drift = float(gap.abs().sum() / 2)
    if drift < 0.05:
        out.append(f"Portföyünüz bu modele zaten çok yakın (sapma {pct(drift)}); işlem yapmaya değmeyebilir.")
    elif drift < 0.15:
        out.append(f"Orta düzey sapma ({pct(drift)}). Küçük işlemleri komisyon maliyetine göre atlamayı düşünebilirsiniz.")
    else:
        out.append(f"Sapma yüksek ({pct(drift)}). Önerinin tamamını tek seferde uygulamak yerine kademeli geçiş "
                   "daha az maliyetli ve daha az riskli olabilir.")
    return out
