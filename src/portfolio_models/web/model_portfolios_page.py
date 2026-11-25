"""🏛️ Model portföyler: kurumların yayımladığı model portföyleri gün sonu fiyatlarıyla karşılaştırma (TR / EN / DE).

Kayıtlar MCP üzerinden yapay zekâ asistanıyla ya da bu sayfadaki formla eklenir/güncellenir. Her güncelleme tarihli bir
revizyon olarak saklanır; performans her revizyonu kendi tarihinde uygular.
"""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio_models import model_analysis as ma
from portfolio_models import model_portfolios as mp
from portfolio_models import store
from portfolio_models.fund_prices import history_series
from portfolio_models.holdings import KINDS, display_label
from portfolio_models.i18n import t
from portfolio_models.insights import num, pct

DOCS = "https://ozanbayhan.github.io/portfolio-models/model-portfolios/"
CURRENCIES = {"TRY": "₺ TRY", "USD": "$ USD", "EUR": "€ EUR"}
PERIOD_KEYS = {"1 ay": 30, "3 ay": 91, "Yılbaşından": "ytd", "1 yıl": 365, "Tümü": None}
COLS = [("1G", "1 gün"), ("1H", "1 hafta"), ("1A", "1 ay"), ("3A", "3 ay"), ("YB", "Yılbaşından"),
        ("1Y", "1 yıl"), ("total", "Başlangıçtan"), ("annual", "Yıllık"), ("vol", "Volatilite"),
        ("max_dd", "Maks. düşüş")]
GREY = "#9CA3AF"


def DISCLAIMER() -> str:  # noqa: N802 - dil değişince yeniden çevrilsin diye fonksiyon
    return t("Bu sayfa, kurumların kamuya açık olarak yayımladığı model portföylerin bir arşivi ve matematiksel "
             "analizidir. Yalnızca varlık, ağırlık ve tarih bilgisi saklanır; raporların metni, grafikleri ve "
             "dosyaları kopyalanmaz, kaynak bağlantısı verilir. Performans bu uygulama tarafından geçmiş kapanış "
             "fiyatlarıyla hesaplanır (işlem maliyeti, vergi ve temettü hariç) ve kurumun açıkladığı rakamlardan "
             "farklı olabilir. Sıralamalar geçmiş verinin istatistiksel bir özetidir. Burada yer alan bilgiler "
             "yatırım danışmanlığı kapsamında değildir; yatırım tavsiyesi değildir.")


PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#84CC16"]


@st.cache_data(ttl=900, show_spinner=False)
def _market(configs_json: str, benchmarks: tuple[str, ...], funds_json: str):
    """Fiyatlar 15 dakikada bir yenilenir; gün içinde son fiyat, gün sonunda kapanış kullanılır."""
    funds = {k: history_series(v) for k, v in json.loads(funds_json).items() if v}
    return mp.market_for(json.loads(configs_json), list(benchmarks), fund_history=funds)


def _fmt(v) -> str:
    return "—" if v is None or pd.isna(v) else pct(v, 1)


def _kind_options() -> dict[str, str]:
    """Ekranda gösterilen tür adı -> kısa tür anahtarı (bist, yahoo …)."""
    return {t(k): mp.KIND_NAMES[k] for k in KINDS}


def _editor(engine, email, configs: dict[str, dict], show_flash) -> None:
    ss = st.session_state
    ss.setdefault("mp_ver", 0)
    show_flash("mp_flash")
    names = list(configs)
    new_label = t("➕ Yeni model portföy")
    pick = st.selectbox(t("Model portföy"), [new_label] + names, key="mp_pick")
    cfg = configs.get(pick, {})
    c1, c2, c3 = st.columns([3, 2, 1])
    name = c1.text_input(t("Ad"), value="" if pick == new_label else pick, max_chars=120,
                         placeholder=t("örn. Kurum adı · Hisse model portföyü"), key=f"mp_name_{pick}",
                         disabled=pick != new_label)
    provider = c2.text_input(t("Kurum"), value=cfg.get("provider", ""), key=f"mp_prov_{pick}")
    country = c3.text_input(t("Ülke"), value=cfg.get("country", ""), max_chars=2, placeholder="TR",
                            key=f"mp_cty_{pick}")
    c4, c5 = st.columns([3, 1])
    source = c4.text_input(t("Kaynak bağlantısı"), value=cfg.get("source_url", ""), key=f"mp_src_{pick}")
    as_of = c5.date_input(t("Geçerlilik tarihi"), value=date.today(), max_value=date.today(), key=f"mp_date_{pick}",
                          help=t("Kurumun bu dağılımı açıkladığı / uygulamaya başladığı gün. Yeni tarih yeni bir "
                                 "revizyon ekler; geçmiş korunur."))
    kinds = _kind_options()
    rev = {v: k for k, v in kinds.items()}
    rows = [{"Tür": rev[h["kind"]], "Sembol": h.get("symbol") or "", "Ağırlık %": h["weight"]}
            for h in mp.current_holdings(cfg)] or [{"Tür": rev["bist"], "Sembol": "", "Ağırlık %": None}]
    edited = st.data_editor(
        pd.DataFrame(rows), num_rows="dynamic", hide_index=True, width="stretch",
        column_config={
            "Tür": st.column_config.SelectboxColumn(t("Tür"), options=list(kinds), required=True),
            "Sembol": st.column_config.TextColumn(t("Sembol")),
            "Ağırlık %": st.column_config.NumberColumn(t("Ağırlık %"), min_value=0.0, max_value=100.0,
                                                      format="%.2f"),
        },
        key=f"mp_ed_{pick}_{ss.mp_ver}",
    )
    total = pd.to_numeric(edited["Ağırlık %"], errors="coerce").fillna(0).sum()
    st.caption(t("Toplam ağırlık: {w}", w=f"{total:.2f}%") + " · "
               + t("BIST: THYAO · Yahoo: AAPL, VOO, ALV.DE · TEFAS: fon kodu (fiyat geçmişi Portföyüm'de) · "
                   "Gram altın: sembol boş · Nakit: TRY/USD/EUR"))
    b1, b2 = st.columns([1, 1])
    if b1.button(t("Revizyonu kaydet"), type="primary", width="stretch"):
        final = name.strip() if pick == new_label else pick
        holdings = [{"kind": kinds.get(r["Tür"], r["Tür"]), "symbol": (r["Sembol"] or "").strip() or None,
                     "weight": r["Ağırlık %"]} for r in edited.to_dict("records")
                    if r.get("Ağırlık %") and not pd.isna(r["Ağırlık %"])]
        try:
            if not final:
                raise ValueError(t("Model portföy adı girin."))
            new_cfg, warns = mp.add_revision(cfg or None, f"{as_of:%Y-%m-%d}", holdings,
                                             provider=provider.strip() or None,
                                             country=country.strip().upper() or None,
                                             source_url=source.strip() or None)
            store.save_portfolio(engine, email, final, new_cfg, kind=mp.STORE_KIND)
        except Exception as exc:  # noqa: BLE001
            ss.mp_flash = ("error", t("Kaydedilemedi: {err}", err=exc))
        else:
            ss.mp_flash = ("success", t("“{name}” kaydedildi ({d}).", name=final, d=f"{as_of:%d.%m.%Y}")
                           + (" " + " ".join(warns) if warns else ""))
            ss.mp_ver += 1
            ss.pop("mp_pick", None)
        st.rerun()
    if pick != new_label:
        sure = b2.checkbox(t("Silmeyi onaylıyorum (geri alınamaz)"), key=f"mp_sure_{pick}")
        if b2.button(t("Sil"), disabled=not sure, width="stretch", key=f"mp_del_{pick}"):
            store.delete_portfolio(engine, email, pick, kind=mp.STORE_KIND)
            ss.mp_flash = ("success", t("“{name}” silindi.", name=pick))
            ss.pop("mp_pick", None)
            st.rerun()


def model_portfolios_page(user_store, show_flash) -> None:
    from portfolio_models.web import ui

    ui.hero(t("🏛️ Model portföyler"),
            t("Aracı kurum, banka ve portföy yönetim şirketlerinin yayımladığı model portföyleri gün sonu fiyatlarıyla "
              "karşılaştırın. Her güncelleme kendi tarihinde uygulanır. Eklemek ve güncellemek için yapay zekâ "
              "asistanınızı bağlayabilir ya da aşağıdaki formu kullanabilirsiniz."),
            [t("Her ülkeden kurum"), t("Tarihli revizyonlar"), "TRY · USD · EUR", t("Yapay zekâ ile güncelleme (MCP)")])

    engine, email = user_store()
    configs: dict[str, dict] = {}
    funds: dict[str, dict] = {}
    if engine is not None:
        try:
            configs = mp.load_all(engine, email)
            funds = {f["name"]: store.load_portfolio(engine, email, f["name"], kind="fund_prices") or {}
                     for f in store.list_portfolios(engine, email, kind="fund_prices")}
        except Exception as exc:  # noqa: BLE001
            st.error(t("Kayıtlar okunamadı: {err}", err=exc.__class__.__name__))
    example = not configs
    if example:
        configs = mp.examples()
        st.info(t("Henüz kayıtlı model portföy yok; **uydurma kurum adlarıyla örnekler** gösteriliyor. Kendi takip "
                  "ettiğiniz kurumları aşağıdan ya da yapay zekâ asistanınızla ekleyin."))

    # --- Seçimler
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        chosen = c1.multiselect(t("Karşılaştırılacak model portföyler"), list(configs), default=list(configs),
                                key=f"mp_sel_{example}")
        benches = c2.multiselect(t("Kıyas serileri"), list(mp.BENCHMARKS), default=["BIST100"], key="mp_bench",
                                 format_func=lambda b: display_label(b))
        c3, c4 = st.columns([1, 2])
        currency = c3.segmented_control(t("Para birimi"), list(CURRENCIES), default="TRY", key="mp_cur",
                                        format_func=CURRENCIES.get) or "TRY"
        period = c4.segmented_control(t("Grafik dönemi"), list(PERIOD_KEYS), default="Tümü", key="mp_period",
                                      format_func=t) or "Tümü"
    if not chosen:
        st.warning(t("En az bir model portföy seçin."))
    else:
        sel = {n: configs[n] for n in chosen}
        with st.spinner(t("Fiyatlar indiriliyor…")):
            try:
                try_prices, closes = _market(json.dumps(sel, sort_keys=True, default=str), tuple(benches),
                                             json.dumps(funds, sort_keys=True))
                comp = mp.compare_models(sel, try_prices, closes, currency, benches)
            except Exception as exc:  # noqa: BLE001
                st.error(t("Hesaplanamadı: {err}", err=exc))
                comp = None
        if comp is not None and comp.indices:
            tab_cmp, tab_rank, tab_an = st.tabs([t("📈 Karşılaştırma"), t("🏆 Sıralama"), t("📐 Optimizasyon analizi")])
            with tab_cmp:
                _results(comp, period, currency)
            prices = None
            try:
                prices = ma.in_ccy(try_prices, closes, currency)
            except ValueError as exc:
                st.error(t("Hesaplanamadı: {err}", err=exc))
            if prices is not None:
                bench = benches[0] if benches else None
                with tab_rank:
                    _ranking(sel, prices, bench, currency)
                with tab_an:
                    _analysis_tab(sel, try_prices, closes, currency, bench)
        elif comp is not None:
            st.warning(t("Seçili model portföyler için fiyat bulunamadı."))

    # --- Ayrıntılar
    st.subheader(t("Dağılımlar ve geçmiş"))
    for name, cfg in configs.items():
        revs = cfg.get("revisions", [])
        head = f"{name} · {cfg.get('provider') or '—'}" + (f" · {cfg['country']}" if cfg.get("country") else "")
        with st.expander(head):
            meta = [t("Son güncelleme: {d}", d=pd.Timestamp(revs[-1]["date"]).strftime("%d.%m.%Y"))] if revs else []
            meta.append(t("{n} revizyon", n=len(revs)))
            if cfg.get("source_url"):
                meta.append(f"[{t('Kaynak')}]({cfg['source_url']})")
            st.caption(" · ".join(meta) + (f"  \n{cfg['note']}" if cfg.get("note") else ""))
            frames = {pd.Timestamp(r["date"]).strftime("%d.%m.%Y"):
                      {display_label(mp.label_of(h)): h["weight"] / 100 for h in r["holdings"]} for r in revs}
            hist = pd.DataFrame(frames).iloc[:, ::-1]  # en yeni revizyon solda
            st.dataframe(hist.map(lambda v: "" if pd.isna(v) else pct(v, 1)), width="stretch")

    # --- Ekle / güncelle
    st.subheader(t("Ekle veya güncelle"))
    tab_ai, tab_form = st.tabs([t("🤖 Yapay zekâ ile"), t("✍️ Elle")])
    with tab_ai:
        st.markdown(t(
            "Claude, ChatGPT ya da Cursor'u bu uygulamaya **MCP** ile bağlayın ([kurulum]({docs})). Sonra örneğin "
            "şunu yazın:\n\n"
            "> *“Şu kurumun aylık model portföyünü kendi sitesinden bul ve kaydet: …”*\n\n"
            "> *“Kayıtlı model portföylerin kaynak sayfalarını kontrol et; değişen varsa yeni tarihle güncelle.”*\n\n"
            "> *“Model portföyleri dolar bazında karşılaştır; son 3 ayda en iyisi hangisi?”*\n\n"
            "Asistan ağırlıkları kurumun yayımladığı sayfadan okur, kaynağı ve tarihi kaydeder; tahmin etmez. "
            "Düzenli güncelleme için asistanınızın zamanlanmış görev özelliğini kullanabilirsiniz (ör. her pazartesi).",
            docs=DOCS))
    with tab_form:
        if engine is None:
            st.caption(email)
        else:
            _editor(engine, email, {} if example else configs, show_flash)
    st.caption(DISCLAIMER())
    ui.footer()


def _results(comp: mp.Comparison, period: str, currency: str) -> None:
    df = mp.rebase(comp.indices, PERIOD_KEYS[period])
    fig = go.Figure()
    bench = {r["name"] for r in comp.table if r["is_benchmark"]}
    i = 0
    for c in df.columns:
        is_b = c in bench
        color = "#9CA3AF" if is_b else PALETTE[i % len(PALETTE)]
        i += 0 if is_b else 1
        fig.add_trace(go.Scatter(x=df.index, y=df[c], name=display_label(c), mode="lines",
                                 line={"color": color, "width": 1.5 if is_b else 2.4,
                                       "dash": "dot" if is_b else "solid"}))
    fig.update_layout(height=430, legend={"orientation": "h", "y": -0.15}, hovermode="x unified",
                      yaxis_title=t("Başlangıç = 100 ({cur})", cur=currency), margin={"t": 10})
    st.plotly_chart(fig, width="stretch")

    rows = []
    for r in sorted(comp.table, key=lambda r: (r["is_benchmark"], -(r["total"] if r["total"] is not None else -9))):
        row = {t("Model portföy"): display_label(r["name"]) + (" ⓑ" if r["is_benchmark"] else ""),
               t("Kurum"): r["provider"] or "—",
               t("Güncelleme"): pd.Timestamp(r["updated"]).strftime("%d.%m.%Y") if r["updated"] else "—"}
        row |= {t(label): _fmt(r.get(key)) for key, label in COLS}
        row[t("Başlangıç")] = r["since"].strftime("%d.%m.%Y") if r.get("since") else "—"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    notes = [t("Gün sonu kapanış fiyatları (Yahoo Finance), 15 dakikada bir yenilenir; son fiyat günü {d}.",
               d=comp.price_date.strftime("%d.%m.%Y") if comp.price_date else "—"),
             t("ⓑ kıyas serisi; en eski model portföyün başladığı günden itibaren.")]
    if currency != "TRY":
        notes.append(t("Tüm seriler {cur} cinsindendir; TL değerler günlük kurla çevrilir.", cur=currency))
    st.caption(" ".join(notes))
    for name, ws in comp.warnings.items():
        st.warning(f"**{name}:** " + " ".join(ws))


def _model_name(m: str) -> str:
    from portfolio_models.models import MODELS

    if m == ma.ACTUAL:
        return t("Kurumun portföyü")
    return t(MODELS[m][1]) if m in MODELS else display_label(m)


RANK_LABELS = {
    "return": "En yüksek getiri",
    "risk_adjusted": "Riske göre getiri (Sharpe)",
    "alpha": "Kıyasa göre fark (alfa)",
    "hit_rate": "İsabet oranı",
    "consistency": "Tutarlılık (aylık)",
    "drawdown": "En küçük düşüş",
    "volatility": "En düşük oynaklık",
}
RANK_HELP = {
    "return": "Seçilen dönemdeki toplam getiri.",
    "risk_adjusted": "Günlük getirilerin ortalamasının oynaklığa oranı, yıllık. Risksiz faiz düşülmez.",
    "alpha": "Yıllık getirinin, aynı dönemde kıyas serisinin yıllık getirisinden farkı (en az 90 gün).",
    "hit_rate": "Her revizyonda seçilen varlıklardan (nakit hariç), tutuldukları dönemde kıyası geçenlerin oranı.",
    "consistency": "Ayların yüzde kaçında portföyün kıyas serisinin üstünde kaldığı (en az 3 ay).",
    "drawdown": "Zirveden en büyük düşüş; küçük olan üstte.",
    "volatility": "Yıllık oynaklık; düşük olan üstte.",
}
RANK_WINDOWS = {"Başlangıçtan": None, "Yılbaşından": "ytd", "1 yıl": 365, "3 ay": 91}


def _ranking(sel: dict[str, dict], prices: pd.DataFrame, bench: str | None, currency: str) -> None:
    c1, c2 = st.columns([2, 1])
    by = c1.segmented_control(t("Sırala"), list(RANK_LABELS), default="risk_adjusted", key="mp_rank_by",
                              format_func=lambda k: t(RANK_LABELS[k])) or "risk_adjusted"
    win = c2.selectbox(t("Dönem"), list(RANK_WINDOWS), key="mp_rank_win", format_func=t)
    st.caption(t(RANK_HELP[by]))
    if by in ("alpha", "hit_rate", "consistency") and not bench:
        st.info(t("Bu sıralama için yukarıdan bir kıyas serisi seçin."))
        return
    lb = ma.leaderboard(sel, prices, bench, RANK_WINDOWS[win])
    if lb.empty:
        st.info(t("Bu dönemin tamamını kapsayan model portföy yok."))
        return
    lb = ma.rank(lb, by)
    fmt_pct = lambda v: _fmt(v)  # noqa: E731
    fmt_num = lambda v: "—" if v is None or pd.isna(v) else num(v)  # noqa: E731
    rows = []
    for i, (name, r) in enumerate(lb.iterrows(), 1):
        rows.append({
            "#": i, t("Model portföy"): name, t("Kurum"): r["provider"] or "—",
            t("Getiri"): fmt_pct(r["total"]), t("Yıllık"): fmt_pct(r["annual"]),
            t("Volatilite"): fmt_pct(r["vol"]), t("Maks. düşüş"): fmt_pct(r["max_dd"]),
            "Sharpe": fmt_num(r["sharpe"]), "Sortino": fmt_num(r["sortino"]),
            t("Alfa"): fmt_pct(r["alpha"]), "Beta": fmt_num(r["beta"]),
            t("İsabet"): fmt_pct(r["hit_rate"]), t("Tutarlılık"): fmt_pct(r["monthly_win"]),
            t("Revizyon"): int(r["revisions"]),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(t("Para birimi: {cur}. Kıyas: {b}. Dönem seçildiğinde tüm portföyler aynı günden başlatılır; o "
                 "tarihten sonra başlayanlar listede yer almaz.", cur=currency, b=display_label(bench) if bench else "—")
               + " " + t("Sıralama geçmiş verinin özetidir; gelecekteki sonuçları göstermez."))


@st.cache_data(ttl=900, show_spinner=False)
def _analysis(cfg_json: str, prices: pd.DataFrame, bench: str | None, revision: int):
    return ma.analyze(json.loads(cfg_json), prices, bench, revision=revision)


def _analysis_tab(sel, try_prices, closes, currency, bench) -> None:
    st.markdown(t("Kurumun seçtiği varlıklar, revizyon tarihine kadarki (en çok 1 yıllık) fiyatlarla optimizasyon "
                  "modellerine verilir. Böylece kurumun ağırlıklarının risk açısından nerede durduğu ve **aynı "
                  "varlıkları bir model ağırlıklandırsaydı** sonucun ne olacağı görülür. Modeller geleceği görmez."))
    c1, c2 = st.columns([2, 1])
    name = c1.selectbox(t("Model portföy"), list(sel), key="mp_an_pick")
    cfg = sel[name]
    revs = cfg["revisions"]
    labels = {i - len(revs): pd.Timestamp(r["date"]).strftime("%d.%m.%Y") for i, r in enumerate(revs)}
    revision = c2.selectbox(t("İncelenen revizyon"), list(labels)[::-1], format_func=labels.get, key=f"mp_an_rev_{name}")
    prices = ma.in_ccy(try_prices, closes, currency)
    with st.spinner(t("Modeller hesaplanıyor…")):
        try:
            a = _analysis(json.dumps(cfg, sort_keys=True, default=str), prices, bench, revision)
        except Exception as exc:  # noqa: BLE001
            st.error(t("Hesaplanamadı: {err}", err=exc))
            return

    # Özet
    d = a.decomposition
    facts = []
    if a.closest:
        facts.append(t("Ağırlıkça en çok benzediği model: **{m}** (fark: portföyün {d}).",
                       m=_model_name(a.closest), d=pct(a.profiles[a.closest].distance, 0)))
    pa = a.profiles[ma.ACTUAL]
    if pa.ann_vol is not None:
        facts.append(t("Revizyon öncesi verilerle yıllık oynaklık ~{v}, etkin varlık sayısı {n}, çeşitlendirme "
                       "oranı {dr}.", v=pct(pa.ann_vol, 1), n=num(pa.eff_n, 1),
                       dr="—" if pa.div_ratio is None else num(pa.div_ratio)))
    if pa.top_risk:
        facts.append(t("Riskin en büyük kaynağı **{a}** (toplam riskteki payı: {s}).", a=display_label(pa.top_risk),
                       s=pct(pa.top_risk_share, 0)))
    if d["total_vs_benchmark"] is not None:
        facts.append(t("İlk revizyondan bu yana kıyasa göre fark {tot}: varlık seçimi {sel} (aynı varlıklar eşit "
                       "ağırlıkla), ağırlıklandırma {w}.", tot=pct(d["total_vs_benchmark"], 1, sign=True),
                       sel=pct(d["selection"], 1, sign=True), w=pct(d["weighting"], 1, sign=True)))
    if facts:
        st.markdown("\n".join(f"- {f}" for f in facts))

    # Ağırlıklar
    st.markdown("**" + t("Ağırlıklar ({d})", d=pd.Timestamp(a.as_of).strftime("%d.%m.%Y")) + "**")
    w = a.weights.rename(index=display_label, columns=_model_name)
    st.dataframe(w.map(lambda v: pct(v, 1) if v > 1e-6 else ""), width="stretch")

    # Risk profili
    st.markdown("**" + t("Risk profili (revizyon öncesi veriyle)") + "**")
    prof = []
    for k, p in a.profiles.items():
        prof.append({t("Portföy"): _model_name(k), t("Yıllık oynaklık"): _fmt(p.ann_vol),
                     t("Geçmiş getiri"): _fmt(p.ann_ret),
                     t("Getiri/risk"): "—" if p.ratio is None else num(p.ratio),
                     t("Etkin varlık"): num(p.eff_n, 1),
                     t("Çeşitlendirme oranı"): "—" if p.div_ratio is None else num(p.div_ratio),
                     t("Kurumdan farkı"): pct(p.distance, 0)})
    st.dataframe(pd.DataFrame(prof), hide_index=True, width="stretch")

    # Performans: kurum vs modeller
    st.markdown("**" + t("Aynı varlıklar, farklı ağırlıklar: ilk revizyondan bu yana") + "**")
    fig = go.Figure()
    for i, (k, s) in enumerate(a.paths.items()):
        is_act, is_b = k == ma.ACTUAL, k == bench
        fig.add_trace(go.Scatter(
            x=s.index, y=s, name=display_label(k) if is_b else _model_name(k), mode="lines",
            line={"color": PALETTE[0] if is_act else GREY if is_b else PALETTE[1 + i % (len(PALETTE) - 1)],
                  "width": 3 if is_act else 1.4, "dash": "dot" if is_b else "solid"},
            opacity=1 if is_act or is_b else 0.75))
    fig.update_layout(height=400, legend={"orientation": "h", "y": -0.18}, hovermode="x unified",
                      yaxis_title=t("Başlangıç = 100 ({cur})", cur=currency), margin={"t": 10})
    st.plotly_chart(fig, width="stretch")
    perf = []
    for k, sc in sorted(a.scores.items(), key=lambda kv: -(kv[1].get("sharpe") or -99)):
        perf.append({t("Portföy"): display_label(k) + " ⓑ" if k == bench else _model_name(k),
                     t("Getiri"): _fmt(sc.get("total")), t("Volatilite"): _fmt(sc.get("vol")),
                     t("Maks. düşüş"): _fmt(sc.get("max_dd")),
                     "Sharpe": "—" if sc.get("sharpe") is None else num(sc["sharpe"]),
                     t("Alfa"): _fmt(sc.get("alpha"))})
    st.dataframe(pd.DataFrame(perf), hide_index=True, width="stretch")
    st.caption(t("Model yolları kurumun revizyon takvimini izler: her revizyon tarihinde model, o güne kadarki "
                 "verilerle yeniden ağırlıklandırır ve bir sonraki revizyona kadar tutar. Nakit ve fiyat geçmişi "
                 "yetersiz varlıkların payı kurumunkiyle aynı bırakılır."))
    for n in a.notes:
        st.caption("ⓘ " + n)
