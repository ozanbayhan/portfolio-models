"""💼 Portföyüm sayfası: pozisyonlar, işlem geçmişi, fon fiyatları; takip ve yeniden dengeleme (TR / EN / DE).

Kayıtlarda saklanan değerler (sütun adları, tür ve işlem adları) dilden bağımsız iç anahtarlardır (Türkçe).
Ekranda seçili dile çevrilir, kaydederken tekrar iç anahtara dönüştürülür.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portfolio_models import fit_weights, store
from portfolio_models.benchmarks import (
    BENCHMARK_TICKERS,
    benchmark_prices,
    compare,
    daily_cpi,
    fetch_cpi_best,
    inflows_by_day,
    summary as bench_summary,
    twr_index,
)
from portfolio_models.fund_prices import (
    editor_frame,
    from_editor,
    history_series,
    merge_history,
    parse_fund_file,
)
from portfolio_models.holdings import (
    COLUMNS,
    KIND_BIST,
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    KINDS,
    SIDE_BUY,
    SIDE_SELL,
    SIDES,
    TXN_COLUMNS,
    TXN_KINDS,
    aggregate_trades,
    asset_label,
    display_label,
    cash_balances,
    cash_movements,
    cash_tracking,
    dividends_tl,
    fetch_market_data,
    history_returns,
    invested_series,
    make_position,
    merge_rows_with_trades,
    parse_positions,
    parse_trades,
    quantity_timeline,
    rebalance,
    trade_cashflows,
    try_price_history,
    valuation,
    value_history,
    value_series,
    xirr,
)
from portfolio_models.i18n import get_lang, num_sep, t
from portfolio_models.insights import pct, rebalance_comment
from portfolio_models.report import set_weekly, weekly_enabled
from portfolio_models.trades_io import export_csv, merge_trades, parse_trades_file, template_csv

EXAMPLE_ROWS = [
    {"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 100.0, "Ort. maliyet": 250.0},
    {"Tür": KIND_BIST, "Sembol": "ASELS", "Miktar": 200.0, "Ort. maliyet": None},
    {"Tür": KIND_GOLD, "Sembol": "", "Miktar": 10.0, "Ort. maliyet": None},
    {"Tür": KIND_YAHOO, "Sembol": "AAPL", "Miktar": 5.0, "Ort. maliyet": 180.0},
    {"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 10000.0, "Ort. maliyet": None},
]
DEFAULT_NAME = "Portföyüm"
FUND_KIND = "fund_prices"  # kayıt türü (store)
PERIODS = {"1 ay": 30, "3 ay": 91, "6 ay": 182, "1 yıl": 365, "Yılbaşından": "ytd", "Tümü": None}


# --- Yardımcılar -----------------------------------------------------------------


@st.cache_data(ttl=900, show_spinner=False)
def cached_market(assets: tuple[tuple[str, str], ...], years: int):
    """Piyasa verisi yalnızca varlık listesine ve döneme göre önbelleklenir (miktar değişince yeniden indirilmez)."""
    return fetch_market_data([make_position(k, s, 1.0) for k, s in assets], years=years)


def _evds_key() -> str | None:
    try:
        return st.secrets.get("evds_api_key") or None
    except Exception:  # noqa: BLE001 - secrets dosyası yoksa
        return None


@st.cache_data(ttl=43200, show_spinner=False)
def cached_cpi(has_key: bool) -> tuple[pd.Series, str]:
    return fetch_cpi_best(_evds_key() if has_key else None, "2015-01")


def _to_display(values: list[str]) -> dict[str, str]:
    """İç değer -> ekrandaki çeviri."""
    return {v: t(v) for v in values}


def _to_internal(values: list[str]) -> dict[str, str]:
    """Ekrandaki çeviri (ya da iç değer) -> iç değer."""
    return {t(v): v for v in values} | {v: v for v in values}


def _records(df: pd.DataFrame, columns: list[str], maps: dict[str, dict] | None = None) -> list[dict]:
    df = df.reindex(columns=columns)
    recs = df.astype(object).where(df.notna(), None).to_dict("records")
    for r in recs:
        if isinstance(r.get("Tarih"), (date, pd.Timestamp)):  # tarihleri JSON için metne çevir
            r["Tarih"] = pd.Timestamp(r["Tarih"]).strftime("%Y-%m-%d")
        for col, m in (maps or {}).items():
            if r.get(col) in m:
                r[col] = m[r[col]]
    return recs


def _num(v) -> str:
    """Adet/miktar: tam sayıysa ondalıksız, değilse en fazla 4 ondalık (sondaki sıfırlar atılır)."""
    if v is None or pd.isna(v):
        return ""
    v = float(v)
    s = f"{v:,.0f}" if v.is_integer() else f"{v:,.4f}".rstrip("0").rstrip(".")
    return _localize(s)


def _localize(s: str) -> str:
    """'1,234.5' biçimini dile göre ayırıcılara çevirir."""
    dec, thou = num_sep()
    return s.replace(",", "\0").replace(".", dec).replace("\0", thou)


def _fmt_tl(x: float) -> str:
    return "₺" + _localize(f"{x:,.0f}")


def _delta(x: float, digits: int = 2) -> str:
    """st.metric için yüzde değişim (ASCII işaret; renklendirme için)."""
    body = pct(abs(x), digits)
    return ("+" if x >= 0 else "-") + body


# --- Kayıt işlemleri ------------------------------------------------------------------


def _set_data(positions: list[dict], txns: list[dict], name: str | None = None) -> None:
    ss = st.session_state
    ss.hold_rows, ss.hold_txns = positions, txns
    ss.hold_version += 1
    if name:
        ss.hold_name = name


def _unpack(cfg) -> tuple[list[dict], list[dict]]:
    if isinstance(cfg, list):  # eski kayıtlar: yalnızca pozisyon listesi
        return cfg, []
    cfg = cfg or {}
    return cfg.get("positions", []), cfg.get("transactions", [])


def _on_load(engine, email):
    name = st.session_state.get("hold_pick")
    cfg = store.load_portfolio(engine, email, name, kind="holdings") if name else None
    if cfg is not None:
        _set_data(*_unpack(cfg), name)
        st.session_state.hold_flash = ("success", t("“{name}” yüklendi.", name=name))


def _on_save(engine, email):
    ss = st.session_state
    name = (ss.get("hold_name") or "").strip()
    cfg = {"positions": ss.get("hold_current", []), "transactions": ss.get("txn_current", [])}
    try:
        store.save_portfolio(engine, email, name, cfg, kind="holdings")
        ss.hold_pick = name
        ss.hold_flash = ("success", t("“{name}” kaydedildi.", name=name))
    except ValueError as exc:
        ss.hold_flash = ("error", str(exc))


def _on_delete(engine, email):
    name = st.session_state.get("hold_pick")
    if name and store.delete_portfolio(engine, email, name, kind="holdings"):
        st.session_state.hold_pick = None
        st.session_state.hold_flash = ("success", t("“{name}” silindi.", name=name))


def _on_new():
    _set_data([], [], DEFAULT_NAME)
    st.session_state.hold_pick = None


def _persist_funds(engine, email, codes) -> str | None:
    """Fon fiyat geçmişini kullanıcının hesabına yazar. Hata olursa mesaj döner."""
    if engine is None:
        return None
    try:
        for code in codes:
            hist = st.session_state.fund_hist.get(code)
            if hist:
                store.save_portfolio(engine, email, code, hist, kind=FUND_KIND)
            else:
                store.delete_portfolio(engine, email, code, kind=FUND_KIND)
    except ValueError as exc:
        return str(exc)
    return None


def _use_in_analysis(positions):
    bist = [p.label for p in positions if p.kind == KIND_BIST]
    other = [p.ticker for p in positions if p.kind == KIND_YAHOO]
    if any(p.kind == KIND_GOLD for p in positions):
        other.append("GC=F")
    st.session_state.bist_text = " ".join(bist)
    st.session_state.other_text = " ".join(other)
    st.session_state.source = "Yahoo Finance"
    st.session_state.pop("bt", None)
    st.session_state.hold_used = True


# --- Karşılaştırma ---------------------------------------------------------------------


def _comparison(port_vals: pd.Series, inflows: pd.Series | None, years: int) -> None:
    st.subheader(t("Karşılaştırma"))
    if port_vals is None or len(port_vals.dropna()) < 5:
        st.caption(t("Karşılaştırma için yeterli portföy geçmişi yok."))
        return
    period = st.segmented_control(t("Dönem"), list(PERIODS), default="1 yıl", key="cmp_period", format_func=t,
                                  label_visibility="collapsed") or "1 yıl"
    end = port_vals.index.max()
    p = PERIODS[period]
    if p is None:
        start = port_vals.index.min()
    elif p == "ytd":
        start = pd.Timestamp(year=end.year, month=1, day=1)
    else:
        start = end - pd.Timedelta(days=p)
    start = max(start, port_vals.index.min())
    try:
        bclose, _ = cached_market(tuple((KIND_YAHOO, tk) for tk in BENCHMARK_TICKERS), years)
    except Exception as exc:  # noqa: BLE001
        st.warning(t("Benchmark verisi alınamadı: {err}", err=exc))
        return
    index = twr_index(port_vals, inflows)
    cpi, cpi_source = cached_cpi(bool(_evds_key()))
    bench = benchmark_prices(bclose)
    norm = compare(index, bench, daily_cpi(cpi, bench.index.union(index.index)), start, end)
    if norm.empty:
        st.caption(t("Seçilen dönem için veri yok."))
        return
    fig = go.Figure()
    for c in norm.columns:
        dash = "dot" if c == "Enflasyon (TÜFE)" else None
        width = 3 if c == "Portföyüm" else 1.5
        fig.add_scatter(x=norm.index, y=norm[c], name=t(c), mode="lines", line=dict(dash=dash, width=width))
    fig.add_hline(y=100, line_width=1, line_color="gray", opacity=0.4)
    fig.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=t("Başlangıç = 100"),
                      legend=dict(orientation="h", y=-0.12), hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    s = bench_summary(norm)
    if not s.empty:
        for col in ("Başlangıç", "Bitiş"):
            s[col] = [pd.Timestamp(v).strftime("%d.%m.%Y") for v in s[col]]
        s["Seri"] = s["Seri"].map(t)
        s = s.rename(columns=t)
        st.dataframe(
            s.style.format({t("Toplam getiri"): "{:+.1%}", t("Yıllık"): "{:+.1%}",
                            t("Reel (TÜFE'ye göre)"): "{:+.1%}"}, na_rep="—"),
            hide_index=True, width="stretch",
        )
    notes = [t("Portföy getirisi zaman ağırlıklıdır (TWR): para yatırma/çekme ve alımların etkisi ayıklanır.")]
    if not cpi.empty:
        notes.append(t("TÜFE: {src}, {month} ayına kadar; sonrası için reel getiri hesaplanmaz.",
                       src=cpi_source, month=f"{cpi.index.max():%m.%Y}"))
    else:
        notes.append(t("TÜFE verisi şu an alınamadı."))
    st.caption(" ".join(notes))


# --- Sekmeler -------------------------------------------------------------------------


def _positions_tab() -> None:
    ss = st.session_state
    st.caption(t(
        "Şu an elinizde olanlar (tarihsiz). **BIST hissesi:** THYAO · **TEFAS fonu:** fon kodu (TTE, AFT…) — fiyatı "
        "**Güncel fiyat** sütununa ya da *Fon fiyatları* sekmesine girin · **Yahoo sembolü:** AAPL, BTC-USD, VOO… · "
        "**Gram altın:** sembol boş · **Nakit:** TRY, USD, EUR… · **Ort. maliyet** isteğe bağlı, varlığın kendi para "
        "biriminde (AAPL için $). İşlem geçmişi girdiğiniz varlıkları burada tekrar yazmayın; ikisi toplanır."
    ))
    kind_disp = _to_display(KINDS)
    frame = pd.DataFrame(ss.hold_rows, columns=COLUMNS)
    frame["Tür"] = frame["Tür"].map(lambda v: kind_disp.get(v, v))
    edited = st.data_editor(
        frame,
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Tür": st.column_config.SelectboxColumn(t("Tür"), options=list(kind_disp.values()), required=True,
                                                   width="medium"),
            "Sembol": st.column_config.TextColumn(t("Sembol"), width="medium"),
            "Miktar": st.column_config.NumberColumn(t("Miktar"), min_value=0.0, format="%.6g", required=True),
            "Ort. maliyet": st.column_config.NumberColumn(t("Ort. maliyet"), min_value=0.0, format="%.6g"),
            "Güncel fiyat": st.column_config.NumberColumn(
                t("Güncel fiyat"), min_value=0.0, format="%.6g",
                help=t("Yalnızca TEFAS fonları için: güncel birim fiyat (TL). Fon fiyatları sekmesinde geçmiş "
                       "yüklediyseniz boş bırakabilirsiniz."),
            ),
        },
        key=f"hold_editor_{ss.hold_version}_{get_lang()}",
    )
    ss.hold_current = _records(edited, COLUMNS, {"Tür": _to_internal(KINDS)})


def _transactions_tab(summary) -> None:
    ss = st.session_state
    st.caption(t(
        "Her alım ve satımı tarihiyle girin; miktar ve ortalama maliyet bunlardan hesaplanır. **Fiyat** birim fiyattır "
        "ve varlığın kendi para birimindedir (BIST ve fonlar TL, gram altın TL/gram, AAPL $). Dövizli işlemler "
        "işlem günündeki kurla TL'ye çevrilir. **Temettü:** varlığı seçip net tutarı **Tutar**'a yazın. "
        "**Para yatır / Para çek:** Tür *Nakit*, Sembol para birimi (TRY, USD…), tutar **Tutar**'a — girerseniz "
        "nakit takibi açılır ve nakit bakiyesi işlemlerden hesaplanır."
    ))
    show = ss.pop("txn_flash", None)
    if show:
        getattr(st, show[0])(show[1])
    with st.expander(t("📥 Dosyadan içe aktar / 📤 dışa aktar")):
        st.caption(t(
            "Aracı kurum ekstresi ya da kendi tablonuz (CSV/Excel). Tarih, işlem yönü (Al/Alış/Buy — Sat/Satış/Sell), "
            "sembol, adet ve fiyat sütunları otomatik tanınır; tür sütunu yoksa aşağıda seçtiğiniz tür kullanılır. "
            "Aynı işlem iki kez eklenmez."
        ))
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        up = c1.file_uploader(t("İşlem dosyası"), type=["csv", "xlsx", "xls"], key=f"txn_up_{ss.txn_up_ver}",
                              label_visibility="collapsed")
        default_kind = c2.selectbox(t("Tür sütunu yoksa"), TXN_KINDS, format_func=t, key="txn_default_kind")
        if up is not None and st.button(t("İşlemleri içe aktar"), type="primary"):
            try:
                new_rows, warns = parse_trades_file(up.getvalue(), up.name, default_kind)
            except Exception as exc:  # noqa: BLE001
                ss.txn_flash = ("error", t("Dosya okunamadı: {err}", err=exc))
            else:
                current = ss.get("txn_current", ss.hold_txns)
                merged, skipped = merge_trades(current, new_rows)
                added = len(merged) - len(current)
                ss.hold_rows = ss.get("hold_current", ss.hold_rows)  # pozisyon tablosundaki düzenlemeler korunur
                ss.hold_txns = merged
                ss.hold_version += 1
                msg = t("{n} işlem eklendi.", n=added)
                if skipped:
                    msg += " " + t("{n} tekrar eden işlem atlandı.", n=skipped)
                if warns:
                    msg += " " + " ".join(warns[:5])
                    if len(warns) > 5:
                        msg += " " + t("(+{n} uyarı)", n=len(warns) - 5)
                if added:
                    msg += " " + t("Kalıcı olması için Kaydet'e basın.")
                ss.txn_flash = ("success" if added else "warning", msg)
            ss.txn_up_ver += 1
            st.rerun()
        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button(t("Şablonu indir"), template_csv(), "islem_sablonu.csv", "text/csv",
                           help=t("Örnek satırlı, Excel'de açılabilen CSV şablonu."))
        d2.download_button(t("İşlemleri indir"), export_csv(ss.get("txn_current", ss.hold_txns)), "islemlerim.csv",
                           "text/csv", disabled=not ss.get("txn_current", ss.hold_txns))
    side_disp, kind_disp = _to_display(SIDES), _to_display(TXN_KINDS + [KIND_CASH])
    frame = pd.DataFrame(ss.hold_txns, columns=TXN_COLUMNS)
    frame["Tarih"] = pd.to_datetime(frame["Tarih"], errors="coerce").dt.date
    frame["İşlem"] = frame["İşlem"].map(lambda v: side_disp.get(v, v))
    frame["Tür"] = frame["Tür"].map(lambda v: kind_disp.get(v, v))
    edited = st.data_editor(
        frame,
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Tarih": st.column_config.DateColumn(t("Tarih"), format="DD.MM.YYYY", max_value=date.today(),
                                                 required=True),
            "İşlem": st.column_config.SelectboxColumn(t("İşlem"), options=list(side_disp.values()), required=True),
            "Tür": st.column_config.SelectboxColumn(t("Tür"), options=list(kind_disp.values()), width="medium"),
            "Sembol": st.column_config.TextColumn(t("Sembol")),
            "Adet": st.column_config.NumberColumn(t("Adet"), min_value=0.0, format="%.6g"),
            "Fiyat": st.column_config.NumberColumn(t("Fiyat"), min_value=0.0, format="%.6g"),
            "Tutar": st.column_config.NumberColumn(
                t("Tutar"), min_value=0.0, format="%.2f",
                help=t("Temettü, para yatırma ve çekmede toplam tutar. Temettüde bunun yerine Adet × hisse başı "
                       "temettü de girebilirsiniz."),
            ),
        },
        key=f"txn_editor_{ss.hold_version}_{get_lang()}",
    )
    ss.txn_current = _records(edited, TXN_COLUMNS,
                              {"İşlem": _to_internal(SIDES), "Tür": _to_internal(TXN_KINDS + [KIND_CASH])})
    if summary:
        rows = [
            {t("Varlık"): k, t("Kalan adet"): s.qty, t("Ort. maliyet"): s.avg_cost, t("Gerçekleşen K/Z"): s.realized,
             t("Temettü"): s.dividends, t("İlk işlem"): s.first_date.date() if s.first_date is not None else None}
            for k, s in summary.items()
        ]
        st.caption(t("İşlemlerden hesaplanan özet (tutarlar varlığın kendi para biriminde):"))
        st.dataframe(
            pd.DataFrame(rows).style.format(
                {t("Kalan adet"): _num, t("Ort. maliyet"): "{:,.4g}", t("Gerçekleşen K/Z"): "{:+,.2f}",
                 t("Temettü"): "{:,.2f}"},
                na_rep="",
            ),
            hide_index=True, width="stretch",
        )


def _funds_tab(engine, email, fund_codes: list[str]) -> None:
    ss = st.session_state
    st.caption(
        t("TEFAS fonlarının fiyat geçmişini buradan yükleyin ya da elle girin. Geçmişi olan fonlar değer grafiğine, "
          "günlük değişime ve yeniden dengelemeye katılır. "
          "[TEFAS → Fon Verileri](https://www.tefas.gov.tr/tr/fon-verileri) sayfasında fonu ve tarih aralığını seçip "
          "**Excel** ya da **CSV** ile indirin.")
        + " " + (t("Fiyatlar hesabınıza kaydedilir.") if engine is not None
                 else t("(Giriş yapmadığınız için yalnızca bu oturumda tutulur.)"))
    )
    show = ss.pop("fund_flash", None)
    if show:
        getattr(st, show[0])(show[1])

    with st.container(border=True):
        st.markdown(t("**📄 Dosyadan yükle**"))
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        up = c1.file_uploader(t("TEFAS dosyası"), type=["csv", "xlsx", "xls"], key=f"fund_up_{ss.fund_up_ver}",
                              label_visibility="collapsed")
        default_code = c2.text_input(t("Dosyada fon kodu yoksa"), placeholder=t("ör. TTE"), max_chars=12)
        if up is not None and st.button(t("İçe aktar"), type="primary"):
            try:
                df, warns = parse_fund_file(up.getvalue(), up.name, default_code.strip() or None)
            except Exception as exc:  # noqa: BLE001
                ss.fund_flash = ("error", t("Dosya okunamadı: {err}", err=exc))
            else:
                if df.empty:
                    ss.fund_flash = ("warning", t("Dosyada geçerli fiyat satırı bulunamadı.") + " " + " ".join(warns))
                else:
                    ss.fund_hist = merge_history(ss.fund_hist, df)
                    codes = sorted(df["code"].unique())
                    err = _persist_funds(engine, email, codes)
                    summary = ", ".join(t("{code}: {n} gün", code=c, n=int((df["code"] == c).sum())) for c in codes)
                    msg = t("İçe aktarıldı — {summary}.", summary=summary) + (" " + " ".join(warns) if warns else "")
                    ss.fund_flash = ("error", err) if err else ("success", msg)
                    ss.fund_pick = codes[0]
                ss.fund_up_ver += 1
            st.rerun()

    with st.container(border=True):
        st.markdown(t("**✏️ Elle gir / düzenle**"))
        options = sorted(set(fund_codes) | set(ss.fund_hist))
        c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
        new_code = c2.text_input(t("Yeni fon kodu ekle"), placeholder=t("ör. AFT"), max_chars=12, key="fund_new")
        if new_code.strip():
            code = new_code.strip().upper()
            if code not in options:
                options.append(code)
            ss.fund_pick = code
        if not options:
            st.caption(t("Önce bir fon kodu yazın ya da pozisyon/işlem tablosuna TEFAS fonu ekleyin."))
            return
        if ss.get("fund_pick") not in options:
            ss.fund_pick = options[0]
        code = c1.selectbox(t("Fon"), options, key="fund_pick")
        hist = ss.fund_hist.get(code, {})
        frame = editor_frame(hist) if hist else pd.DataFrame({"Tarih": pd.Series(dtype="object"),
                                                              "Fiyat": pd.Series(dtype=float)})
        c_ed, c_chart = st.columns([2, 3])
        edited = c_ed.data_editor(
            frame, num_rows="dynamic", hide_index=True, width="stretch", height=320,
            column_config={
                "Tarih": st.column_config.DateColumn(t("Tarih"), format="DD.MM.YYYY", max_value=date.today(),
                                                     required=True),
                "Fiyat": st.column_config.NumberColumn(t("Fiyat"), min_value=0.0, format="%.6f", required=True),
            },
            key=f"fund_editor_{code}_{ss.fund_ed_ver}",
        )
        s = history_series(hist)
        if len(s) > 1:
            fig = px.line(s.rename(t("Fiyat")), labels={"index": "", "value": t("Fiyat (TL)")})
            fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            c_chart.plotly_chart(fig, width="stretch")
        elif hist:
            c_chart.caption(t("Grafik için en az 2 fiyat gerekir."))
        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button(t("Fiyatları kaydet"), type="primary", key="fund_save"):
            new_hist, warns = from_editor(edited)
            ss.fund_hist = {**ss.fund_hist, code: new_hist}
            err = _persist_funds(engine, email, [code])
            ss.fund_flash = ("error", err) if err else (
                "success", t("{code}: {n} fiyat kaydedildi.", code=code, n=len(new_hist))
                + (" " + " ".join(warns) if warns else ""))
            ss.fund_ed_ver += 1
            st.rerun()
        if hist and b2.button(t("Geçmişi sil"), key="fund_del"):
            ss.fund_hist = {k: v for k, v in ss.fund_hist.items() if k != code}
            _persist_funds(engine, email, [code])
            ss.fund_flash = ("success", t("{code} fiyat geçmişi silindi.", code=code))
            ss.fund_ed_ver += 1
            st.rerun()


# --- Sayfa --------------------------------------------------------------------------


def holdings_page(user_store, show_flash, model_desc: dict[str, str]) -> None:
    ss = st.session_state
    for k, v in (("hold_version", 0), ("hold_name", DEFAULT_NAME), ("fund_up_ver", 0), ("fund_ed_ver", 0),
                 ("txn_up_ver", 0)):
        ss.setdefault(k, v)

    st.title(t("💼 Portföyüm"))
    st.caption(t(
        "Varlıklarınızı girin; güncel değer, kâr/zarar, geçmiş performans ve modele göre yeniden dengeleme önerisi "
        "hesaplanır. Fiyatlar Yahoo Finance'ten (BIST ~15 dk gecikmeli). Eğitim amaçlıdır, yatırım tavsiyesi değildir."
    ))

    engine, email = user_store()

    # İlk açılış: kullanıcının en son portföyü ve fon fiyat geçmişi
    if "hold_rows" not in ss:
        rows, txns, name = EXAMPLE_ROWS, [], DEFAULT_NAME
        if engine is not None:
            try:
                saved = store.list_portfolios(engine, email, kind="holdings")
                if saved:
                    name = saved[0]["name"]
                    rows, txns = _unpack(store.load_portfolio(engine, email, name, kind="holdings"))
                    ss.hold_pick = name
            except Exception:  # noqa: BLE001
                pass
        ss.hold_rows, ss.hold_txns, ss.hold_name = rows, txns, name
    if "fund_hist" not in ss:
        ss.fund_hist = {}
        if engine is not None:
            try:
                for item in store.list_portfolios(engine, email, kind=FUND_KIND):
                    ss.fund_hist[item["name"]] = store.load_portfolio(engine, email, item["name"], kind=FUND_KIND) or {}
            except Exception:  # noqa: BLE001
                pass

    # --- Kayıt çubuğu
    with st.container(border=True):
        if engine is None:
            st.caption("🔒 " + email + " " + t("Girdikleriniz bu oturum kapanınca silinir."))
        else:
            show_flash("hold_flash")
            try:
                saved_names = [p["name"] for p in store.list_portfolios(engine, email, kind="holdings")]
            except Exception as exc:  # noqa: BLE001
                saved_names = []
                st.error(t("Kayıtlar okunamadı: {err}", err=exc.__class__.__name__))
            c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 1, 1], vertical_alignment="bottom")
            if ss.get("hold_pick") not in saved_names:
                ss.hold_pick = None
            c1.selectbox(t("Kayıtlı portföyler"), saved_names, index=None, key="hold_pick",
                         placeholder=t("Seçin…") if saved_names else t("Henüz kayıt yok"))
            c2.button(t("Yükle"), on_click=_on_load, args=(engine, email), width="stretch",
                      disabled=not ss.get("hold_pick"))
            c3.text_input(t("Portföy adı"), key="hold_name", max_chars=120)
            c4.button(t("Kaydet"), type="primary", on_click=_on_save, args=(engine, email), width="stretch",
                      help=t("Pozisyonları ve işlemleri kaydeder. Fon fiyatları ayrıca, kendi sekmesinde kaydedilir."))
            c5.button(t("Sil"), on_click=_on_delete, args=(engine, email), width="stretch",
                      disabled=not ss.get("hold_pick"))
            try:
                if "weekly_on" not in ss:
                    ss.weekly_on = weekly_enabled(engine, email)

                def _toggle_weekly():
                    set_weekly(engine, email, ss.weekly_on, lang=get_lang())
                    ss.hold_flash = ("success", t("Haftalık e-posta özeti açıldı: her pazartesi sabah {email} adresine "
                                                  "gönderilir (son kaydettiğiniz portföy).", email=email)
                                     if ss.weekly_on else t("Haftalık e-posta özeti kapatıldı."))

                st.toggle(t("📧 Haftalık e-posta özeti"), key="weekly_on", on_change=_toggle_weekly,
                          help=t("Her pazartesi 09:00'da son kaydettiğiniz portföyün değerini, haftalık değişimini ve "
                                 "fiyatı eskimiş fonları e-postayla gönderir."))
            except Exception:  # noqa: BLE001 - ayar tablosu okunamazsa sayfa çalışmaya devam etsin
                pass

    # --- Girdi sekmeleri (işlem özeti için işlemler önce okunur)
    trades, t_warn = parse_trades(ss.get("txn_current", ss.hold_txns))
    summary, a_warn = aggregate_trades(trades)
    # Sekme başlıkları sabit kalmalı: başlık değişirse Streamlit seçili sekmeyi ilk sekmeye sıfırlar
    tab_pos, tab_txn, tab_fund = st.tabs([t("📋 Pozisyonlar"), t("🧾 İşlemler"), t("📈 Fon fiyatları")])
    with tab_pos:
        _positions_tab()
        st.button(t("Tüm tabloları temizle"), on_click=_on_new, help=t("Pozisyonları ve işlemleri boşaltır."))
    with tab_txn:
        _transactions_tab(summary)
    # İşlem tablosu bu çalıştırmada değiştiyse güncel haliyle yeniden hesapla
    trades, t_warn = parse_trades(ss.txn_current)
    summary, a_warn = aggregate_trades(trades)
    fund_codes = sorted({asset_label(r.get("Tür"), r.get("Sembol")) for r in ss.hold_current + ss.txn_current
                         if r.get("Tür") == KIND_FUND and r.get("Sembol")} - {None})
    with tab_fund:
        _funds_tab(engine, email, fund_codes)

    # --- Pozisyonları birleştir ve fiyatla
    real_hist = {c: history_series(h) for c, h in ss.fund_hist.items() if h}
    fund_pricing = dict(real_hist)
    for tr in trades:  # işlem fiyatları da fon için fiyat gözlemi sayılır (geçmişte olmayan tarihler)
        if tr.kind == KIND_FUND and tr.is_trade:
            s = fund_pricing.get(tr.label, pd.Series(dtype=float))
            if tr.date not in s.index:
                s = pd.concat([s, pd.Series({tr.date: tr.price})]).sort_index()
            fund_pricing[tr.label] = s
    tracking = cash_tracking(trades)
    fund_sets = dict(funds_with_history=set(real_hist), funds_with_price=set(fund_pricing))
    base_positions, _ = parse_positions(ss.hold_current, **fund_sets)
    base_qty = {p.label: p.quantity for p in base_positions}
    # 1) Nakit hariç pozisyonlar: piyasa verisini (ve para birimlerini) almak için
    positions, p_warn = parse_positions(merge_rows_with_trades(ss.hold_current, summary), **fund_sets)
    if not positions and not trades:
        for w in t_warn + a_warn + p_warn:
            st.warning(w)
        st.info(t("Pozisyonlar veya İşlemler sekmesine en az bir varlık ekleyin."))
        return

    held = {p.label for p in positions}
    sold = [make_position(s.kind, s.symbol, 0.0, has_history=s.symbol.upper() in real_hist)
            for lbl, s in summary.items() if lbl not in held]
    cash_curs = {tr.symbol for tr in trades if tr.kind == KIND_CASH}
    first_trade = min((tr.date for tr in trades), default=None)
    years = 3
    if first_trade is not None:
        years = max(3, math.ceil((pd.Timestamp(date.today()) - first_trade).days / 365) + 1)

    def _symbol(p):  # make_position ile yeniden oluşturulabilecek sembol
        if p.is_cash:
            return p.cash_currency
        return p.ticker if p.kind == KIND_YAHOO else ("" if p.kind == KIND_GOLD else p.label)

    assets = {(p.kind, _symbol(p)) for p in positions + sold
              if p.kind != KIND_FUND and not (p.is_cash and p.cash_currency == "TRY")}
    assets |= {(KIND_CASH, c) for c in cash_curs if c != "TRY"}
    try:
        with st.spinner(t("Güncel fiyatlar alınıyor…")):
            closes, currencies = cached_market(tuple(sorted(assets)), years) if assets else (pd.DataFrame(), {})
    except Exception as exc:  # noqa: BLE001
        st.error(t("Fiyatlar alınamadı: {err}", err=exc))
        return

    # 2) Nakit takibi açıksa işlemlerden türeyen nakit bakiyeleri pozisyonlara eklenir
    cash_moves: list = []
    if tracking:
        balances = cash_balances(trades, currencies)
        bal_warn = [t("{label} bakiyesi işlemlere göre eksiye düşüyor ({b}). Eksik para yatırma işlemi olabilir; "
                      "eksi bakiye sıfır kabul edildi.", label=t("Nakit") + " " + label.split()[-1],
                      b=_localize(f"{b:,.2f}"))
                    for label, b in balances.items() if b < -0.5]
        positions, p_warn = parse_positions(merge_rows_with_trades(ss.hold_current, summary, balances), **fund_sets)
        p_warn += bal_warn
        cash_moves = cash_movements(trades, currencies)
        held = {p.label for p in positions}
    for w in t_warn + a_warn + p_warn:
        st.warning(w)

    cash_zero = [make_position(KIND_CASH, lbl.split()[-1], 0.0) for lbl in {m[1] for m in cash_moves}
                 if lbl not in held]
    pricing_positions = positions + sold + cash_zero
    try:
        prices_try = try_price_history(pricing_positions, closes, currencies, fund_pricing)
        table, missing = valuation(positions, closes, currencies, prices_try, fund_pricing)
    except Exception as exc:  # noqa: BLE001
        st.error(t("Fiyatlar hesaplanamadı: {err}", err=exc))
        return
    if missing:
        st.warning(t("Fiyat bulunamadı, hesaba katılmadı: {assets}. Sembolü kontrol edin.", assets=", ".join(missing)))

    # --- Özet
    st.divider()
    total = float(table["Değer (TL)"].sum()) if not table.empty else 0.0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("Toplam değer"), _fmt_tl(total))
    if not table.empty:
        daily = table["Günlük %"].fillna(0)
        daily_tl = float((table["Değer (TL)"] - table["Değer (TL)"] / (1 + daily)).sum())
        m2.metric(t("Günlük değişim"), _fmt_tl(daily_tl), _delta(daily_tl / (total - daily_tl)) if total else None)
        with_cost = table.dropna(subset=["Maliyet (TL)"])
        if not with_cost.empty:
            pnl, cost = float(with_cost["K/Z (TL)"].sum()), float(with_cost["Maliyet (TL)"].sum())
            m3.metric(t("Açık pozisyon K/Z"), _fmt_tl(pnl), _delta(pnl / cost) if cost else None,
                      help=t("Maliyeti bilinen varlıklar için. Dövizli varlıklarda bugünkü kurla."))
        else:
            m3.metric(t("Açık pozisyon K/Z"), "—",
                      help=t("Ort. maliyet girdiğiniz ya da işlem geçmişi olan varlıklar için."))

    flows = trade_cashflows(trades, closes, currencies) if trades else pd.DataFrame(columns=["date", "label", "amount"])
    if trades:
        # Gerçekleşen K/Z: varlığın para biriminde hesaplanır, bugünkü kurla TL'ye çevrilir
        realized_tl = 0.0
        for lbl, s in summary.items():
            if not s.realized:
                continue
            p = make_position(s.kind, s.symbol, 1.0)
            fx = 1.0
            if p.ticker and lbl in prices_try and p.ticker in closes:
                local = closes[p.ticker].dropna()
                fx = float(prices_try[lbl].dropna().iloc[-1] / local.iloc[-1]) if len(local) else 1.0
            realized_tl += s.realized * fx
        div_tl = dividends_tl(trades, closes, currencies)
        # XIRR: işlemlerden gelen kısmın bugünkü değeri (tarihsiz pozisyon satırları düşülür) + nakit akışları
        last_px = prices_try.ffill().iloc[-1] if not prices_try.empty else pd.Series(dtype=float)
        base_value = sum(q * float(last_px.get(lbl, 0.0)) for lbl, q in base_qty.items())
        final = max(total - base_value, 0.0)
        span = (pd.Timestamp(date.today()) - flows["date"].min()).days if not flows.empty else 0
        rate = (xirr(list(zip(flows["date"], flows["amount"])) + [(pd.Timestamp(date.today()), final)])
                if span >= 90 else None)
        m4.metric(
            t("Yıllık getiri (XIRR)"), pct(rate, sign=True) if rate is not None else "—",
            help=t("İşlem tarihleri ve tutarlarına göre yıllıklandırılmış getiri; en az 3 aylık işlem geçmişi gerekir.")
            + " " + (t("Nakit takibi açık: yalnızca para yatırma/çekme dış akış sayılır.") if tracking
                     else t("Alımlar para girişi, satışlar ve temettüler para çıkışı sayılır."))
            + (" " + t("Tarihsiz pozisyon satırları hesaba katılmaz.") if base_qty else ""),
        )
        n1, n2, n3, n4 = st.columns(4)
        n1.metric(t("Gerçekleşen K/Z"), _fmt_tl(realized_tl),
                  help=t("Satışlardan elde edilen kâr/zarar (bugünkü kurla)."))
        n2.metric(t("Alınan temettü"), _fmt_tl(div_tl), help=t("Temettü tarihindeki kurla TL."))
        net_in = float(-flows["amount"].sum()) if not flows.empty else 0.0
        n3.metric(t("Net yatırılan"), _fmt_tl(net_in),
                  help=t("Para yatırma − çekme") if tracking else t("Alımlar − satımlar − temettüler"))
        n4.metric(t("Nakit takibi"), t("Açık") if tracking else t("Kapalı"),
                  help=t("İşlemlere 'Para yatır' / 'Para çek' eklediğinizde açılır: alımlar nakitten düşer, satış ve "
                         "temettüler nakde eklenir."))

    if table.empty:
        return

    shown = table.copy()
    for col, fmt in (("Maliyet (TL)", "₺{:,.0f}"), ("K/Z (TL)", "₺{:+,.0f}")):
        shown[col] = [("" if pd.isna(v) else _localize(fmt.format(v))) for v in shown[col]]
    shown["K/Z %"] = ["" if pd.isna(v) else pct(v, sign=True) for v in shown["K/Z %"]]
    shown["Fiyat tarihi"] = [("" if v is None or pd.isna(v) else pd.Timestamp(v).strftime("%d.%m.%Y"))
                             for v in shown["Fiyat tarihi"]]
    shown["Tür"] = shown["Tür"].map(t)
    shown["Varlık"] = shown["Varlık"].map(display_label)
    shown = shown.rename(columns=t)
    st.dataframe(
        shown.style.format(
            {t("Miktar"): _num, t("Son fiyat"): lambda v: _localize(f"{v:,.4g}"),
             t("Değer (TL)"): lambda v: "₺" + _localize(f"{v:,.0f}"),
             t("Günlük %"): lambda v: pct(v, 2, sign=True), t("Ağırlık"): lambda v: pct(v)},
            na_rep="",
        ),
        hide_index=True, width="stretch",
    )
    stale = [r["Varlık"] for _, r in table.iterrows()
             if r["Tür"] == KIND_FUND and r["Fiyat tarihi"] and (date.today() - r["Fiyat tarihi"]).days > 7]
    if stale:
        st.caption(t("⚠️ Fiyatı 7 günden eski fonlar: {funds}. Fon fiyatları sekmesinden güncelleyin.",
                     funds=", ".join(stale)))
    st.caption(t("Döviz cinsinden varlıklarda K/Z %, varlığın kendi para birimindedir; TL tutarları bugünkü kurla "
                 "çevrilir."))

    # --- Grafikler
    c1, c2 = st.columns([2, 3])
    pie_df = table.assign(Varlık=table["Varlık"].map(display_label))
    pie = px.pie(pie_df, names="Varlık", values="Değer (TL)", hole=0.5)
    pie.update_traces(textinfo="percent+label", showlegend=False)
    pie.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title=t("Dağılım"))
    c1.plotly_chart(pie, width="stretch")

    if trades:
        qty = quantity_timeline(base_qty, trades, prices_try.index, cash=cash_moves)
        start = first_trade - pd.Timedelta(days=3)
        vals = value_series(qty, prices_try)
        vals = vals[vals.index >= start]
        port_vals, port_in = vals, inflows_by_day(flows, vals.index)
        inv = invested_series(flows, prices_try.index)
        inv = inv[inv.index >= start].reindex(vals.index)
        fig = go.Figure()
        fig.add_scatter(x=vals.index, y=vals.values, name=t("Portföy değeri"), mode="lines")
        fig.add_scatter(x=inv.index, y=inv.values, name=t("Net yatırılan"), mode="lines", line=dict(dash="dot"))
        title = t("Gerçek elde tutulan miktarlarla değer")
        if base_qty:
            title += " " + t("(tarihsiz pozisyonlar tüm dönem dahil)")
        fig.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title=title, yaxis_tickprefix="₺",
                          legend=dict(orientation="h", y=-0.15))
        c2.plotly_chart(fig, width="stretch")
    else:
        hist = value_history(positions, prices_try)
        port_vals, port_in = value_history(positions, prices_try, days=365 * years), None
        line = px.line(hist.rename(t("Değer (TL)")).to_frame(), y=t("Değer (TL)"))
        line.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title=t("Bugünkü miktarlarla son 1 yıl"),
                           yaxis_tickprefix="₺", xaxis_title=None, showlegend=False)
        c2.plotly_chart(line, width="stretch")

    _comparison(port_vals, port_in, years)

    st.button(t("📊 Bu varlıkları Model analizi sayfasında kullan"), on_click=_use_in_analysis, args=(positions,),
              help=t("Sembolleri analiz sayfasının kenar çubuğuna aktarır."))
    if ss.pop("hold_used", False):
        st.success(t("Semboller aktarıldı. Soldaki menüden **📊 Model analizi** sayfasına geçin."))

    # --- Yeniden dengeleme
    st.subheader(t("Yeniden dengeleme önerisi"))
    returns = history_returns(prices_try, positions)
    fixed = {p.label for p in positions if p.is_fixed}
    funds_fixed = [p.label for p in positions if p.kind == KIND_FUND and p.is_fixed]
    if returns.shape[1] < 2:
        st.info(t("Öneri için fiyat geçmişi olan en az 2 varlık gerekir (nakit ve geçmişi girilmemiş fonlar hariç)."))
        return
    if len(returns) < 120:
        st.info(t("Öneri için varlıkların ortak en az ~6 aylık fiyat geçmişi gerekir. Fonların geçmişini uzatmak için "
                  "Fon fiyatları sekmesinden daha uzun dönem yükleyin."))
        return

    names = list(model_desc)
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    model = c1.selectbox("Model", names, index=names.index("hrp") if "hrp" in names else 0,
                         format_func=lambda m: f"{m} — {model_desc[m]}", key="hold_model")
    has_cash = (table["Tür"] == KIND_CASH).any()
    include_cash = c2.checkbox(t("Nakdi de yatırıma dahil et"), value=True, disabled=not has_cash, key="hold_cash")
    st.caption(
        t("Model, varlıkların son {n} yıllık TL getirileriyle eğitilir. BIST hisseleri tam adete yuvarlanır.",
          n=max(len(returns) // 252, 1))
        + (" " + t("Fiyat geçmişi olmayan fonlar ({funds}) olduğu gibi bırakılır.", funds=", ".join(funds_fixed))
           if funds_fixed else "")
    )
    errors: list = []
    with st.spinner(t("Hedef ağırlıklar hesaplanıyor…")):
        weights = fit_weights(returns, [model], on_error=lambda n, e: errors.append(e))
    if errors or weights.empty:
        st.warning(t("Bu model bu varlıklarla çözüm bulamadı: {err}. Başka bir model deneyin.",
                     err=errors[0] if errors else ""))
        return
    whole = {p.label for p in positions if p.kind == KIND_BIST}
    reb = rebalance(table, weights[model], prices_try.iloc[-1], include_cash=include_cash and has_cash,
                    whole_units=whole, fixed=fixed)

    buy_l, sell_l = t(SIDE_BUY), t(SIDE_SELL)

    def _color(v):
        return ("color: #2e9e5b; font-weight:600" if v == buy_l else
                ("color: #d9534f; font-weight:600" if v == sell_l else ""))

    reb_shown = reb.assign(**{"İşlem": reb["İşlem"].map(lambda v: t(v) if v in (SIDE_BUY, SIDE_SELL) else v),
                              "Varlık": reb["Varlık"].map(display_label)})
    reb_shown = reb_shown.rename(columns=t)
    tl = lambda v: "₺" + _localize(f"{v:,.0f}")  # noqa: E731
    st.dataframe(
        reb_shown.style.format(
            {t("Mevcut (TL)"): tl, t("Mevcut ağırlık"): lambda v: pct(v), t("Hedef ağırlık"): lambda v: pct(v),
             t("Hedef (TL)"): tl, t("Adet"): _num, t("Tutar (TL)"): tl}
        ).map(_color, subset=[t("İşlem")]),
        hide_index=True, width="stretch",
    )
    with st.container(border=True):
        st.markdown(t("**🧠 Yorum**"))
        st.markdown("\n".join(f"- {line}" for line in rebalance_comment(reb, model)))
    if has_cash:
        cash_after = reb.attrs.get("cash_after", 0.0)
        if cash_after < -1:
            st.warning(t("Bu işlemler için {x} ek nakit gerekir.", x=_fmt_tl(-cash_after)))
        else:
            st.caption(t("İşlemler sonrası kalan nakit: {x} (TL karşılığı).", x=_fmt_tl(cash_after)))
    turnover = float(reb["Tutar (TL)"].sum())
    if total and not math.isnan(turnover):
        st.caption(t("Toplam işlem hacmi: {x} — portföy değerine oranı {r}. Komisyon ve vergiler dahil değildir.",
                     x=_fmt_tl(turnover), r=pct(turnover / total, 0)))
