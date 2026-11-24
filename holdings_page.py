"""💼 Portföyüm sayfası: pozisyonlar, işlem geçmişi, fon fiyatları; takip ve yeniden dengeleme."""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portfolio_models import fit_weights, store
from portfolio_models.report import set_weekly, weekly_enabled
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
from portfolio_models.trades_io import export_csv, merge_trades, parse_trades_file, template_csv
from portfolio_models.holdings import (
    COLUMNS,
    KIND_BIST,
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    KINDS,
    SIDES,
    TXN_COLUMNS,
    TXN_KINDS,
    aggregate_trades,
    cash_balances,
    cash_movements,
    cash_tracking,
    dividends_tl,
    asset_label,
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

EXAMPLE_ROWS = [
    {"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 100.0, "Ort. maliyet": 250.0},
    {"Tür": KIND_BIST, "Sembol": "ASELS", "Miktar": 200.0, "Ort. maliyet": None},
    {"Tür": KIND_GOLD, "Sembol": "", "Miktar": 10.0, "Ort. maliyet": None},
    {"Tür": KIND_YAHOO, "Sembol": "AAPL", "Miktar": 5.0, "Ort. maliyet": 180.0},
    {"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 10000.0, "Ort. maliyet": None},
]
DEFAULT_NAME = "Portföyüm"
FUND_KIND = "fund_prices"  # kayıt türü (store)


# --- Yardımcılar -----------------------------------------------------------------


@st.cache_data(ttl=900, show_spinner="Güncel fiyatlar alınıyor…")
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


PERIODS = {"1 ay": 30, "3 ay": 91, "6 ay": 182, "1 yıl": 365, "Yılbaşından": "ytd", "Tümü": None}


def _comparison(port_vals: pd.Series, inflows: pd.Series | None, years: int) -> None:
    st.subheader("Karşılaştırma")
    if port_vals is None or len(port_vals.dropna()) < 5:
        st.caption("Karşılaştırma için yeterli portföy geçmişi yok.")
        return
    period = st.segmented_control("Dönem", list(PERIODS), default="1 yıl", key="cmp_period",
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
        st.warning(f"Benchmark verisi alınamadı: {exc}")
        return
    index = twr_index(port_vals, inflows)
    cpi, cpi_source = cached_cpi(bool(_evds_key()))
    bench = benchmark_prices(bclose)
    norm = compare(index, bench, daily_cpi(cpi, bench.index.union(index.index)), start, end)
    if norm.empty:
        st.caption("Seçilen dönem için veri yok.")
        return
    fig = go.Figure()
    for c in norm.columns:
        dash = "dot" if c == "Enflasyon (TÜFE)" else None
        width = 3 if c == "Portföyüm" else 1.5
        fig.add_scatter(x=norm.index, y=norm[c], name=c, mode="lines", line=dict(dash=dash, width=width))
    fig.add_hline(y=100, line_width=1, line_color="gray", opacity=0.4)
    fig.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), yaxis_title="Başlangıç = 100",
                      legend=dict(orientation="h", y=-0.12), hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    s = bench_summary(norm)
    if not s.empty:
        for col in ("Başlangıç", "Bitiş"):
            s[col] = [pd.Timestamp(v).strftime("%d.%m.%Y") for v in s[col]]
        st.dataframe(
            s.style.format({"Toplam getiri": "{:+.1%}", "Yıllık": "{:+.1%}", "Reel (TÜFE'ye göre)": "{:+.1%}"},
                           na_rep="—"),
            hide_index=True, width="stretch",
        )
    notes = ["Portföy getirisi zaman ağırlıklıdır (TWR): para yatırma/çekme ve alımların etkisi ayıklanır."]
    if not cpi.empty:
        notes.append(f"TÜFE: {cpi_source}, {cpi.index.max():%m.%Y} ayına kadar; sonrası için reel getiri hesaplanmaz.")
    else:
        notes.append("TÜFE verisi şu an alınamadı.")
    st.caption(" ".join(notes))


def _records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    df = df.reindex(columns=columns)
    recs = df.astype(object).where(df.notna(), None).to_dict("records")
    for r in recs:  # tarihleri JSON için metne çevir
        if isinstance(r.get("Tarih"), (date, pd.Timestamp)):
            r["Tarih"] = pd.Timestamp(r["Tarih"]).strftime("%Y-%m-%d")
    return recs


def _txn_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=TXN_COLUMNS)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce").dt.date
    return df


def _num(v) -> str:
    """Adet/miktar: tam sayıysa ondalıksız, değilse en fazla 4 ondalık (sondaki sıfırlar atılır)."""
    if v is None or pd.isna(v):
        return ""
    v = float(v)
    return f"{v:,.0f}" if v.is_integer() else f"{v:,.4f}".rstrip("0").rstrip(".")


def _fmt_tl(x: float) -> str:
    return f"₺{x:,.0f}".replace(",", ".")


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
        st.session_state.hold_flash = ("success", f"“{name}” yüklendi.")


def _on_save(engine, email):
    ss = st.session_state
    name = (ss.get("hold_name") or "").strip()
    cfg = {"positions": ss.get("hold_current", []), "transactions": ss.get("txn_current", [])}
    try:
        store.save_portfolio(engine, email, name, cfg, kind="holdings")
        ss.hold_pick = name
        ss.hold_flash = ("success", f"“{name}” kaydedildi.")
    except ValueError as exc:
        ss.hold_flash = ("error", str(exc))


def _on_delete(engine, email):
    name = st.session_state.get("hold_pick")
    if name and store.delete_portfolio(engine, email, name, kind="holdings"):
        st.session_state.hold_pick = None
        st.session_state.hold_flash = ("success", f"“{name}” silindi.")


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


# --- Sekmeler -------------------------------------------------------------------------


def _positions_tab() -> None:
    ss = st.session_state
    st.caption(
        "Şu an elinizde olanlar (tarihsiz). **BIST hissesi:** THYAO · **TEFAS fonu:** fon kodu (TTE, AFT…) — fiyatı "
        "**Güncel fiyat** sütununa ya da *Fon fiyatları* sekmesine girin · **Yahoo sembolü:** AAPL, BTC-USD, VOO… · "
        "**Gram altın:** sembol boş · **Nakit:** TRY, USD, EUR… · **Ort. maliyet** isteğe bağlı, varlığın kendi para "
        "biriminde (AAPL için $). İşlem geçmişi girdiğiniz varlıkları burada tekrar yazmayın; ikisi toplanır."
    )
    edited = st.data_editor(
        pd.DataFrame(ss.hold_rows, columns=COLUMNS),
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Tür": st.column_config.SelectboxColumn(options=KINDS, required=True, width="medium"),
            "Sembol": st.column_config.TextColumn(width="medium"),
            "Miktar": st.column_config.NumberColumn(min_value=0.0, format="%.6g", required=True),
            "Ort. maliyet": st.column_config.NumberColumn(min_value=0.0, format="%.6g"),
            "Güncel fiyat": st.column_config.NumberColumn(
                min_value=0.0, format="%.6g",
                help="Yalnızca TEFAS fonları için: güncel birim fiyat (TL). Fon fiyatları sekmesinde geçmiş "
                     "yüklediyseniz boş bırakabilirsiniz.",
            ),
        },
        key=f"hold_editor_{ss.hold_version}",
    )
    ss.hold_current = _records(edited, COLUMNS)


def _transactions_tab(summary) -> None:
    ss = st.session_state
    st.caption(
        "Her alım ve satımı tarihiyle girin; miktar ve ortalama maliyet bunlardan hesaplanır. **Fiyat** birim fiyattır "
        "ve varlığın kendi para birimindedir (BIST ve fonlar TL, gram altın TL/gram, AAPL $). Dövizli işlemler "
        "işlem günündeki kurla TL'ye çevrilir. **Temettü:** varlığı seçip net tutarı **Tutar**'a yazın. "
        "**Para yatır / Para çek:** Tür *Nakit*, Sembol para birimi (TRY, USD…), tutar **Tutar**'a — girerseniz "
        "nakit takibi açılır ve nakit bakiyesi işlemlerden hesaplanır."
    )
    show = ss.pop("txn_flash", None)
    if show:
        getattr(st, show[0])(show[1])
    with st.expander("📥 Dosyadan içe aktar / 📤 dışa aktar"):
        st.caption(
            "Aracı kurum ekstresi ya da kendi tablonuz (CSV/Excel). Tarih, işlem yönü (Al/Alış/Buy — Sat/Satış/Sell), "
            "sembol, adet ve fiyat sütunları otomatik tanınır; tür sütunu yoksa aşağıda seçtiğiniz tür kullanılır. "
            "Aynı işlem iki kez eklenmez."
        )
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        up = c1.file_uploader("İşlem dosyası", type=["csv", "xlsx", "xls"], key=f"txn_up_{ss.txn_up_ver}",
                              label_visibility="collapsed")
        default_kind = c2.selectbox("Tür sütunu yoksa", TXN_KINDS, key="txn_default_kind")
        if up is not None and st.button("İşlemleri içe aktar", type="primary"):
            try:
                new_rows, warns = parse_trades_file(up.getvalue(), up.name, default_kind)
            except Exception as exc:  # noqa: BLE001
                ss.txn_flash = ("error", f"Dosya okunamadı: {exc}")
            else:
                current = ss.get("txn_current", ss.hold_txns)
                merged, skipped = merge_trades(current, new_rows)
                added = len(merged) - len(current)
                ss.hold_rows = ss.get("hold_current", ss.hold_rows)  # pozisyon tablosundaki düzenlemeler korunur
                ss.hold_txns = merged
                ss.hold_version += 1
                msg = f"{added} işlem eklendi." + (f" {skipped} tekrar eden işlem atlandı." if skipped else "")
                if warns:
                    msg += " " + " ".join(warns[:5]) + (f" (+{len(warns) - 5} uyarı)" if len(warns) > 5 else "")
                ss.txn_flash = ("success" if added else "warning",
                                msg + (" Kalıcı olması için Kaydet'e basın." if added else ""))
            ss.txn_up_ver += 1
            st.rerun()
        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button("Şablonu indir", template_csv(), "islem_sablonu.csv", "text/csv",
                           help="Örnek satırlı, Excel'de açılabilen CSV şablonu.")
        d2.download_button("İşlemleri indir", export_csv(ss.get("txn_current", ss.hold_txns)), "islemlerim.csv",
                           "text/csv", disabled=not ss.get("txn_current", ss.hold_txns))
    edited = st.data_editor(
        _txn_frame(ss.hold_txns),
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY", max_value=date.today(), required=True),
            "İşlem": st.column_config.SelectboxColumn(options=SIDES, required=True),
            "Tür": st.column_config.SelectboxColumn(options=TXN_KINDS + [KIND_CASH], width="medium"),
            "Sembol": st.column_config.TextColumn(),
            "Adet": st.column_config.NumberColumn(min_value=0.0, format="%.6g"),
            "Fiyat": st.column_config.NumberColumn(min_value=0.0, format="%.6g"),
            "Tutar": st.column_config.NumberColumn(
                min_value=0.0, format="%.2f",
                help="Temettü, para yatırma ve çekmede toplam tutar. Temettüde bunun yerine Adet × hisse başı "
                     "temettü de girebilirsiniz.",
            ),
        },
        key=f"txn_editor_{ss.hold_version}",
    )
    ss.txn_current = _records(edited, TXN_COLUMNS)
    if summary:
        rows = [
            {"Varlık": k, "Kalan adet": s.qty, "Ort. maliyet": s.avg_cost, "Gerçekleşen K/Z": s.realized,
             "Temettü": s.dividends, "İlk işlem": s.first_date.date() if s.first_date is not None else None}
            for k, s in summary.items()
        ]
        st.caption("İşlemlerden hesaplanan özet (tutarlar varlığın kendi para biriminde):")
        st.dataframe(
            pd.DataFrame(rows).style.format(
                {"Kalan adet": _num, "Ort. maliyet": "{:,.4g}", "Gerçekleşen K/Z": "{:+,.2f}", "Temettü": "{:,.2f}"},
                na_rep=""
            ),
            hide_index=True, width="stretch",
        )


def _funds_tab(engine, email, fund_codes: list[str]) -> None:
    ss = st.session_state
    st.caption(
        "TEFAS fonlarının fiyat geçmişini buradan yükleyin ya da elle girin. Geçmişi olan fonlar değer grafiğine, "
        "günlük değişime ve yeniden dengelemeye katılır. "
        "[TEFAS → Fon Verileri](https://www.tefas.gov.tr/tr/fon-verileri) sayfasında fonu ve tarih aralığını seçip "
        "**Excel** ya da **CSV** ile indirin."
        + (" Fiyatlar hesabınıza kaydedilir." if engine is not None else " (Giriş yapmadığınız için yalnızca bu oturumda tutulur.)")
    )
    show = ss.pop("fund_flash", None)
    if show:
        getattr(st, show[0])(show[1])

    with st.container(border=True):
        st.markdown("**📄 Dosyadan yükle**")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        up = c1.file_uploader("TEFAS dosyası", type=["csv", "xlsx", "xls"], key=f"fund_up_{ss.fund_up_ver}",
                              label_visibility="collapsed")
        default_code = c2.text_input("Dosyada fon kodu yoksa", placeholder="ör. TTE", max_chars=12)
        if up is not None and st.button("İçe aktar", type="primary"):
            try:
                df, warns = parse_fund_file(up.getvalue(), up.name, default_code.strip() or None)
            except Exception as exc:  # noqa: BLE001
                ss.fund_flash = ("error", f"Dosya okunamadı: {exc}")
            else:
                if df.empty:
                    ss.fund_flash = ("warning", "Dosyada geçerli fiyat satırı bulunamadı. " + " ".join(warns))
                else:
                    ss.fund_hist = merge_history(ss.fund_hist, df)
                    codes = sorted(df["code"].unique())
                    err = _persist_funds(engine, email, codes)
                    summary = ", ".join(f"{c}: {int((df['code'] == c).sum())} gün" for c in codes)
                    msg = f"İçe aktarıldı — {summary}." + (" " + " ".join(warns) if warns else "")
                    ss.fund_flash = ("error", err) if err else ("success", msg)
                    ss.fund_pick = codes[0]
                ss.fund_up_ver += 1
            st.rerun()

    with st.container(border=True):
        st.markdown("**✏️ Elle gir / düzenle**")
        options = sorted(set(fund_codes) | set(ss.fund_hist))
        c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
        new_code = c2.text_input("Yeni fon kodu ekle", placeholder="ör. AFT", max_chars=12, key="fund_new")
        if new_code.strip():
            code = new_code.strip().upper()
            if code not in options:
                options.append(code)
            ss.fund_pick = code
        if not options:
            st.caption("Önce bir fon kodu yazın ya da pozisyon/işlem tablosuna TEFAS fonu ekleyin.")
            return
        if ss.get("fund_pick") not in options:
            ss.fund_pick = options[0]
        code = c1.selectbox("Fon", options, key="fund_pick")
        hist = ss.fund_hist.get(code, {})
        frame = editor_frame(hist) if hist else pd.DataFrame({"Tarih": pd.Series(dtype="object"),
                                                              "Fiyat": pd.Series(dtype=float)})
        c_ed, c_chart = st.columns([2, 3])
        edited = c_ed.data_editor(
            frame, num_rows="dynamic", hide_index=True, width="stretch", height=320,
            column_config={
                "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY", max_value=date.today(), required=True),
                "Fiyat": st.column_config.NumberColumn(min_value=0.0, format="%.6f", required=True),
            },
            key=f"fund_editor_{code}_{ss.fund_ed_ver}",
        )
        s = history_series(hist)
        if len(s) > 1:
            fig = px.line(s.rename("Fiyat"), labels={"index": "", "value": "Fiyat (TL)"})
            fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            c_chart.plotly_chart(fig, width="stretch")
        elif hist:
            c_chart.caption("Grafik için en az 2 fiyat gerekir.")
        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button("Fiyatları kaydet", type="primary", key="fund_save"):
            new_hist, warns = from_editor(edited)
            ss.fund_hist = {**ss.fund_hist, code: new_hist}
            err = _persist_funds(engine, email, [code])
            ss.fund_flash = ("error", err) if err else (
                "success", f"{code}: {len(new_hist)} fiyat kaydedildi." + (" " + " ".join(warns) if warns else ""))
            ss.fund_ed_ver += 1
            st.rerun()
        if hist and b2.button("Geçmişi sil", key="fund_del"):
            ss.fund_hist = {k: v for k, v in ss.fund_hist.items() if k != code}
            _persist_funds(engine, email, [code])
            ss.fund_flash = ("success", f"{code} fiyat geçmişi silindi.")
            ss.fund_ed_ver += 1
            st.rerun()


# --- Sayfa --------------------------------------------------------------------------


def holdings_page(user_store, show_flash, model_desc: dict[str, str]) -> None:
    ss = st.session_state
    for k, v in (("hold_version", 0), ("hold_name", DEFAULT_NAME), ("fund_up_ver", 0), ("fund_ed_ver", 0),
                 ("txn_up_ver", 0)):
        ss.setdefault(k, v)

    st.title("💼 Portföyüm")
    st.caption(
        "Varlıklarınızı girin; güncel değer, kâr/zarar, geçmiş performans ve modele göre yeniden dengeleme önerisi "
        "hesaplanır. Fiyatlar Yahoo Finance'ten (BIST ~15 dk gecikmeli). Eğitim amaçlıdır, yatırım tavsiyesi değildir."
    )

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
            st.caption(f"🔒 {email} Girdikleriniz bu oturum kapanınca silinir.")
        else:
            show_flash("hold_flash")
            try:
                saved_names = [p["name"] for p in store.list_portfolios(engine, email, kind="holdings")]
            except Exception as exc:  # noqa: BLE001
                saved_names = []
                st.error(f"Kayıtlar okunamadı: {exc.__class__.__name__}")
            c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 1, 1], vertical_alignment="bottom")
            if ss.get("hold_pick") not in saved_names:
                ss.hold_pick = None
            c1.selectbox("Kayıtlı portföyler", saved_names, index=None, key="hold_pick",
                         placeholder="Seçin…" if saved_names else "Henüz kayıt yok")
            c2.button("Yükle", on_click=_on_load, args=(engine, email), width="stretch",
                      disabled=not ss.get("hold_pick"))
            c3.text_input("Portföy adı", key="hold_name", max_chars=120)
            c4.button("Kaydet", type="primary", on_click=_on_save, args=(engine, email), width="stretch",
                      help="Pozisyonları ve işlemleri kaydeder. Fon fiyatları ayrıca, kendi sekmesinde kaydedilir.")
            c5.button("Sil", on_click=_on_delete, args=(engine, email), width="stretch",
                      disabled=not ss.get("hold_pick"))
            try:
                if "weekly_on" not in ss:
                    ss.weekly_on = weekly_enabled(engine, email)

                def _toggle_weekly():
                    set_weekly(engine, email, ss.weekly_on)
                    ss.hold_flash = ("success", "Haftalık e-posta özeti açıldı: her pazartesi sabah "
                                     f"{email} adresine gönderilir (son kaydettiğiniz portföy)."
                                     if ss.weekly_on else "Haftalık e-posta özeti kapatıldı.")

                st.toggle("📧 Haftalık e-posta özeti", key="weekly_on", on_change=_toggle_weekly,
                          help="Her pazartesi 09:00'da son kaydettiğiniz portföyün değerini, haftalık değişimini ve "
                               "fiyatı eskimiş fonları e-postayla gönderir.")
            except Exception:  # noqa: BLE001 - ayar tablosu okunamazsa sayfa çalışmaya devam etsin
                pass

    # --- Girdi sekmeleri (işlem özeti için işlemler önce okunur)
    trades, t_warn = parse_trades(ss.get("txn_current", ss.hold_txns))
    summary, a_warn = aggregate_trades(trades)
    # Sekme başlıkları sabit kalmalı: başlık değişirse Streamlit seçili sekmeyi ilk sekmeye sıfırlar
    tab_pos, tab_txn, tab_fund = st.tabs(["📋 Pozisyonlar", "🧾 İşlemler", "📈 Fon fiyatları"])
    with tab_pos:
        _positions_tab()
        st.button("Tüm tabloları temizle", on_click=_on_new, help="Pozisyonları ve işlemleri boşaltır.")
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
    for t in trades:  # işlem fiyatları da fon için fiyat gözlemi sayılır (geçmişte olmayan tarihler)
        if t.kind == KIND_FUND and t.is_trade:
            s = fund_pricing.get(t.label, pd.Series(dtype=float))
            if t.date not in s.index:
                s = pd.concat([s, pd.Series({t.date: t.price})]).sort_index()
            fund_pricing[t.label] = s
    tracking = cash_tracking(trades)
    fund_sets = dict(funds_with_history=set(real_hist), funds_with_price=set(fund_pricing))
    base_positions, _ = parse_positions(ss.hold_current, **fund_sets)
    base_qty = {p.label: p.quantity for p in base_positions}
    # 1) Nakit hariç pozisyonlar: piyasa verisini (ve para birimlerini) almak için
    positions, p_warn = parse_positions(merge_rows_with_trades(ss.hold_current, summary), **fund_sets)
    if not positions and not trades:
        for w in t_warn + a_warn + p_warn:
            st.warning(w)
        st.info("Pozisyonlar veya İşlemler sekmesine en az bir varlık ekleyin.")
        return

    held = {p.label for p in positions}
    sold = [make_position(s.kind, s.symbol, 0.0, has_history=s.symbol.upper() in real_hist)
            for lbl, s in summary.items() if lbl not in held]
    cash_curs = {t.symbol for t in trades if t.kind == KIND_CASH}
    first_trade = min((t.date for t in trades), default=None)
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
        closes, currencies = cached_market(tuple(sorted(assets)), years) if assets else (pd.DataFrame(), {})
    except Exception as exc:  # noqa: BLE001
        st.error(f"Fiyatlar alınamadı: {exc}")
        return

    # 2) Nakit takibi açıksa işlemlerden türeyen nakit bakiyeleri pozisyonlara eklenir
    cash_moves: list = []
    if tracking:
        balances = cash_balances(trades, currencies)
        bal_warn = []
        for label, b in balances.items():
            if b < -0.5:
                bal_warn.append(f"{label} bakiyesi işlemlere göre eksiye düşüyor ({b:,.2f}). Eksik para yatırma "
                              "işlemi olabilir; eksi bakiye sıfır kabul edildi.")
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
        st.error(f"Fiyatlar hesaplanamadı: {exc}")
        return
    if missing:
        st.warning(f"Fiyat bulunamadı, hesaba katılmadı: {', '.join(missing)}. Sembolü kontrol edin.")

    # --- Özet
    st.divider()
    total = float(table["Değer (TL)"].sum()) if not table.empty else 0.0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam değer", _fmt_tl(total))
    if not table.empty:
        daily = table["Günlük %"].fillna(0)
        daily_tl = float((table["Değer (TL)"] - table["Değer (TL)"] / (1 + daily)).sum())
        m2.metric("Günlük değişim", _fmt_tl(daily_tl), f"{daily_tl / (total - daily_tl):+.2%}" if total else None)
        with_cost = table.dropna(subset=["Maliyet (TL)"])
        if not with_cost.empty:
            pnl, cost = float(with_cost["K/Z (TL)"].sum()), float(with_cost["Maliyet (TL)"].sum())
            m3.metric("Açık pozisyon K/Z", _fmt_tl(pnl), f"{pnl / cost:+.2%}" if cost else None,
                      help="Maliyeti bilinen varlıklar için. Dövizli varlıklarda bugünkü kurla.")
        else:
            m3.metric("Açık pozisyon K/Z", "—", help="Ort. maliyet girdiğiniz ya da işlem geçmişi olan varlıklar için.")

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
            "Yıllık getiri (XIRR)", f"{rate:+.1%}" if rate is not None else "—",
            help="İşlem tarihleri ve tutarlarına göre yıllıklandırılmış getiri; en az 3 aylık işlem geçmişi gerekir. "
                 + ("Nakit takibi açık: yalnızca para yatırma/çekme dış akış sayılır."
                    if tracking else "Alımlar para girişi, satışlar ve temettüler para çıkışı sayılır.")
                 + (" Tarihsiz pozisyon satırları hesaba katılmaz." if base_qty else ""),
        )
        n1, n2, n3, n4 = st.columns(4)
        n1.metric("Gerçekleşen K/Z", _fmt_tl(realized_tl), help="Satışlardan elde edilen kâr/zarar (bugünkü kurla).")
        n2.metric("Alınan temettü", _fmt_tl(div_tl), help="Temettü tarihindeki kurla TL.")
        net_in = float(-flows["amount"].sum()) if not flows.empty else 0.0
        n3.metric("Net yatırılan", _fmt_tl(net_in),
                  help="Para yatırma − çekme" if tracking else "Alımlar − satımlar − temettüler")
        n4.metric("Nakit takibi", "Açık" if tracking else "Kapalı",
                  help="İşlemlere 'Para yatır' / 'Para çek' eklediğinizde açılır: alımlar nakitten düşer, satış ve "
                       "temettüler nakde eklenir.")

    if table.empty:
        return

    shown = table.copy()
    for col, fmt in (("Maliyet (TL)", "₺{:,.0f}"), ("K/Z (TL)", "₺{:+,.0f}"), ("K/Z %", "{:+.1%}")):
        shown[col] = [("" if pd.isna(v) else fmt.format(v)) for v in shown[col]]
    shown["Fiyat tarihi"] = [("" if v is None or pd.isna(v) else pd.Timestamp(v).strftime("%d.%m.%Y"))
                             for v in shown["Fiyat tarihi"]]
    st.dataframe(
        shown.style.format(
            {"Miktar": _num, "Son fiyat": "{:,.4g}", "Değer (TL)": "₺{:,.0f}", "Günlük %": "{:+.2%}",
             "Ağırlık": "{:.1%}"},
            na_rep="",
        ),
        hide_index=True, width="stretch",
    )
    stale = [r["Varlık"] for _, r in table.iterrows()
             if r["Tür"] == KIND_FUND and r["Fiyat tarihi"] and (date.today() - r["Fiyat tarihi"]).days > 7]
    if stale:
        st.caption(f"⚠️ Fiyatı 7 günden eski fonlar: {', '.join(stale)}. Fon fiyatları sekmesinden güncelleyin.")
    st.caption("Döviz cinsinden varlıklarda K/Z %, varlığın kendi para birimindedir; TL tutarları bugünkü kurla çevrilir.")

    # --- Grafikler
    c1, c2 = st.columns([2, 3])
    pie = px.pie(table, names="Varlık", values="Değer (TL)", hole=0.5)
    pie.update_traces(textinfo="percent+label", showlegend=False)
    pie.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title="Dağılım")
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
        fig.add_scatter(x=vals.index, y=vals.values, name="Portföy değeri", mode="lines")
        fig.add_scatter(x=inv.index, y=inv.values, name="Net yatırılan", mode="lines",
                        line=dict(dash="dot"))
        title = "Gerçek elde tutulan miktarlarla değer"
        if base_qty:
            title += " (tarihsiz pozisyonlar tüm dönem dahil)"
        fig.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title=title, yaxis_tickprefix="₺",
                          legend=dict(orientation="h", y=-0.15))
        c2.plotly_chart(fig, width="stretch")
    else:
        hist = value_history(positions, prices_try)
        port_vals, port_in = value_history(positions, prices_try, days=365 * years), None
        line = px.line(hist.rename("Değer (TL)").to_frame(), y="Değer (TL)")
        line.update_layout(height=380, margin=dict(t=30, b=10, l=10, r=10), title="Bugünkü miktarlarla son 1 yıl",
                           yaxis_tickprefix="₺", xaxis_title=None, showlegend=False)
        c2.plotly_chart(line, width="stretch")

    _comparison(port_vals, port_in, years)

    st.button("📊 Bu varlıkları Model analizi sayfasında kullan", on_click=_use_in_analysis, args=(positions,),
              help="Sembolleri analiz sayfasının kenar çubuğuna aktarır.")
    if ss.pop("hold_used", False):
        st.success("Semboller aktarıldı. Soldaki menüden **📊 Model analizi** sayfasına geçin.")

    # --- Yeniden dengeleme
    st.subheader("Yeniden dengeleme önerisi")
    returns = history_returns(prices_try, positions)
    fixed = {p.label for p in positions if p.is_fixed}
    funds_fixed = [p.label for p in positions if p.kind == KIND_FUND and p.is_fixed]
    if returns.shape[1] < 2:
        st.info("Öneri için fiyat geçmişi olan en az 2 varlık gerekir (nakit ve geçmişi girilmemiş fonlar hariç).")
        return
    if len(returns) < 120:
        st.info("Öneri için varlıkların ortak en az ~6 aylık fiyat geçmişi gerekir. Fonların geçmişini uzatmak için "
                "Fon fiyatları sekmesinden daha uzun dönem yükleyin.")
        return

    names = list(model_desc)
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    model = c1.selectbox("Model", names, index=names.index("hrp") if "hrp" in names else 0,
                         format_func=lambda m: f"{m} — {model_desc[m]}", key="hold_model")
    has_cash = (table["Tür"] == KIND_CASH).any()
    include_cash = c2.checkbox("Nakdi de yatırıma dahil et", value=True, disabled=not has_cash, key="hold_cash")
    st.caption(
        f"Model, varlıkların son {max(len(returns) // 252, 1)} yıllık TL getirileriyle eğitilir. "
        "BIST hisseleri tam adete yuvarlanır."
        + (f" Fiyat geçmişi olmayan fonlar ({', '.join(funds_fixed)}) olduğu gibi bırakılır." if funds_fixed else "")
    )
    errors: list = []
    with st.spinner("Hedef ağırlıklar hesaplanıyor…"):
        weights = fit_weights(returns, [model], on_error=lambda n, e: errors.append(e))
    if errors or weights.empty:
        st.warning(f"Bu model bu varlıklarla çözüm bulamadı: {errors[0] if errors else ''}. Başka bir model deneyin.")
        return
    whole = {p.label for p in positions if p.kind == KIND_BIST}
    reb = rebalance(table, weights[model], prices_try.iloc[-1], include_cash=include_cash and has_cash,
                    whole_units=whole, fixed=fixed)

    def _color(v):
        return ("color: #2e9e5b; font-weight:600" if v == "Al" else
                ("color: #d9534f; font-weight:600" if v == "Sat" else ""))

    st.dataframe(
        reb.style.format(
            {"Mevcut (TL)": "₺{:,.0f}", "Mevcut ağırlık": "{:.1%}", "Hedef ağırlık": "{:.1%}",
             "Hedef (TL)": "₺{:,.0f}", "Adet": _num, "Tutar (TL)": "₺{:,.0f}"}
        ).map(_color, subset=["İşlem"]),
        hide_index=True, width="stretch",
    )
    if has_cash:
        cash_after = reb.attrs.get("cash_after", 0.0)
        if cash_after < -1:
            st.warning(f"Bu işlemler için {_fmt_tl(-cash_after)} ek nakit gerekir.")
        else:
            st.caption(f"İşlemler sonrası kalan nakit: {_fmt_tl(cash_after)} (TL karşılığı).")
    turnover = float(reb["Tutar (TL)"].sum())
    if total and not math.isnan(turnover):
        st.caption(f"Toplam işlem hacmi: {_fmt_tl(turnover)} — portföy değerine oranı %{turnover / total * 100:.0f}. "
                   "Komisyon ve vergiler dahil değildir.")
