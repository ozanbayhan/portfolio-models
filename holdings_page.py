"""💼 Portföyüm sayfası: gerçek pozisyonları miktarlarıyla takip ve yeniden dengeleme."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_models import fit_weights, store
from portfolio_models.holdings import (
    COLUMNS,
    KIND_BIST,
    KIND_CASH,
    KIND_GOLD,
    KIND_YAHOO,
    KINDS,
    fetch_market_data,
    history_returns,
    parse_positions,
    rebalance,
    try_price_history,
    valuation,
    value_history,
)

EXAMPLE_ROWS = [
    {"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 100.0, "Ort. maliyet": 250.0},
    {"Tür": KIND_BIST, "Sembol": "ASELS", "Miktar": 200.0, "Ort. maliyet": None},
    {"Tür": KIND_GOLD, "Sembol": "", "Miktar": 10.0, "Ort. maliyet": None},
    {"Tür": KIND_YAHOO, "Sembol": "AAPL", "Miktar": 5.0, "Ort. maliyet": 180.0},
    {"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 10000.0, "Ort. maliyet": None},
]
DEFAULT_NAME = "Portföyüm"


@st.cache_data(ttl=900, show_spinner="Güncel fiyatlar alınıyor…")
def cached_market(positions: tuple):
    return fetch_market_data(list(positions))


def _clean_records(df: pd.DataFrame) -> list[dict]:
    df = df.reindex(columns=COLUMNS)
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _set_rows(rows: list[dict], name: str | None = None) -> None:
    ss = st.session_state
    ss.hold_rows = rows
    ss.hold_version += 1
    if name:
        ss.hold_name = name
    ss.pop("hold_reb", None)


def _on_load(engine, email):
    name = st.session_state.get("hold_pick")
    rows = store.load_portfolio(engine, email, name, kind="holdings") if name else None
    if rows is not None:
        _set_rows(rows, name)
        st.session_state.hold_flash = ("success", f"“{name}” yüklendi.")


def _on_save(engine, email):
    ss = st.session_state
    name = (ss.get("hold_name") or "").strip()
    try:
        store.save_portfolio(engine, email, name, ss.get("hold_current", []), kind="holdings")
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
    _set_rows([], DEFAULT_NAME)
    st.session_state.hold_pick = None


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


def _num(v) -> str:
    """Adet/miktar: tam sayıysa ondalıksız, değilse en fazla 4 ondalık (sondaki sıfırlar atılır)."""
    if v is None or pd.isna(v):
        return ""
    v = float(v)
    if v.is_integer():
        return f"{v:,.0f}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def _fmt_tl(x: float) -> str:
    return f"₺{x:,.0f}".replace(",", ".")


def holdings_page(user_store, show_flash, model_desc: dict[str, str]) -> None:
    ss = st.session_state
    ss.setdefault("hold_version", 0)
    ss.setdefault("hold_name", DEFAULT_NAME)

    st.title("💼 Portföyüm")
    st.caption(
        "Varlıklarınızı miktarlarıyla girin; güncel değer, kâr/zarar ve modele göre yeniden dengeleme önerisi "
        "hesaplanır. Fiyatlar Yahoo Finance'ten (BIST ~15 dk gecikmeli). Eğitim amaçlıdır, yatırım tavsiyesi değildir."
    )

    engine, email = user_store()

    # İlk açılışta kullanıcının en son kaydettiği portföyü getir
    if "hold_rows" not in ss:
        rows, name = EXAMPLE_ROWS, DEFAULT_NAME
        if engine is not None:
            try:
                saved = store.list_portfolios(engine, email, kind="holdings")
                if saved:
                    name = saved[0]["name"]
                    rows = store.load_portfolio(engine, email, name, kind="holdings") or []
                    ss.hold_pick = name
            except Exception:  # noqa: BLE001
                pass
        ss.hold_rows = rows
        ss.hold_name = name

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
            c4.button("Kaydet", type="primary", on_click=_on_save, args=(engine, email), width="stretch")
            c5.button("Sil", on_click=_on_delete, args=(engine, email), width="stretch",
                      disabled=not ss.get("hold_pick"))

    # --- Pozisyon tablosu
    st.subheader("Pozisyonlar")
    st.caption(
        "**BIST hissesi:** THYAO gibi kod · **Yahoo sembolü:** AAPL, BTC-USD, VOO… · **Gram altın:** sembol boş · "
        "**Nakit:** sembol TRY, USD, EUR… · **Ort. maliyet** isteğe bağlı, varlığın kendi para biriminde (AAPL için $)."
    )
    c_new, _ = st.columns([1, 5])
    c_new.button("Tabloyu temizle", on_click=_on_new)
    edited = st.data_editor(
        pd.DataFrame(ss.hold_rows, columns=COLUMNS),
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "Tür": st.column_config.SelectboxColumn(options=KINDS, required=True, width="medium"),
            "Sembol": st.column_config.TextColumn(width="medium"),
            "Miktar": st.column_config.NumberColumn(min_value=0.0, format="%.4g", required=True),
            "Ort. maliyet": st.column_config.NumberColumn(min_value=0.0, format="%.4g"),
        },
        key=f"hold_editor_{ss.hold_version}",
    )
    ss.hold_current = _clean_records(edited)

    positions, warns = parse_positions(ss.hold_current)
    for w in warns:
        st.warning(w)
    if not positions:
        st.info("Tabloya en az bir pozisyon ekleyin (alttaki + satırı).")
        return

    try:
        closes, currencies = cached_market(tuple(positions))
        prices_try = try_price_history(positions, closes, currencies)
        table, missing = valuation(positions, closes, currencies, prices_try)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Fiyatlar alınamadı: {exc}")
        return
    if missing:
        st.warning(f"Fiyat bulunamadı, hesaba katılmadı: {', '.join(missing)}. Sembolü kontrol edin.")
    if table.empty:
        return

    # --- Özet
    total = table["Değer (TL)"].sum()
    daily = table["Günlük %"].fillna(0)
    daily_tl = float((table["Değer (TL)"] - table["Değer (TL)"] / (1 + daily)).sum())
    with_cost = table.dropna(subset=["Maliyet (TL)"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam değer", _fmt_tl(total))
    m2.metric("Günlük değişim", _fmt_tl(daily_tl), f"{daily_tl / (total - daily_tl):+.2%}" if total else None)
    if not with_cost.empty:
        pnl = float(with_cost["K/Z (TL)"].sum())
        cost = float(with_cost["Maliyet (TL)"].sum())
        m3.metric("Kâr/zarar (maliyeti girilenler)", _fmt_tl(pnl), f"{pnl / cost:+.2%}" if cost else None)
    else:
        m3.metric("Kâr/zarar", "—", help="Ort. maliyet girdiğiniz varlıklar için hesaplanır.")

    shown = table.copy()
    for col, fmt in (("Maliyet (TL)", "₺{:,.0f}"), ("K/Z (TL)", "₺{:+,.0f}"), ("K/Z %", "{:+.1%}")):
        shown[col] = [("" if pd.isna(v) else fmt.format(v)) for v in shown[col]]
    st.dataframe(
        shown.style.format(
            {
                "Miktar": _num,
                "Son fiyat": "{:,.2f}",
                "Değer (TL)": "₺{:,.0f}",
                "Günlük %": "{:+.2%}",
                "Ağırlık": "{:.1%}",
            },
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Döviz cinsinden varlıklarda K/Z %, varlığın kendi para birimindedir; TL tutarları bugünkü kurla çevrilir."
    )

    c1, c2 = st.columns([2, 3])
    pie = px.pie(table, names="Varlık", values="Değer (TL)", hole=0.5)
    pie.update_traces(textinfo="percent+label", showlegend=False)
    pie.update_layout(height=360, margin=dict(t=30, b=10, l=10, r=10), title="Dağılım")
    c1.plotly_chart(pie, width="stretch")
    hist = value_history(positions, prices_try)
    line = px.line(hist.rename("Değer (TL)").to_frame(), y="Değer (TL)")
    line.update_layout(
        height=360, margin=dict(t=30, b=10, l=10, r=10), title="Bugünkü miktarlarla son 1 yıl",
        yaxis_tickprefix="₺", xaxis_title=None, showlegend=False,
    )
    c2.plotly_chart(line, width="stretch")

    st.button(
        "📊 Bu varlıkları Model analizi sayfasında kullan",
        on_click=_use_in_analysis, args=(positions,),
        help="Sembolleri analiz sayfasının kenar çubuğuna aktarır.",
    )
    if ss.pop("hold_used", False):
        st.success("Semboller aktarıldı. Soldaki menüden **📊 Model analizi** sayfasına geçin.")

    # --- Yeniden dengeleme
    st.subheader("Yeniden dengeleme önerisi")
    returns = history_returns(prices_try, positions)
    if returns.shape[1] < 2:
        st.info("Öneri için nakit dışında en az 2 varlık gerekir.")
        return
    if len(returns) < 120:
        st.info("Öneri için en az ~6 aylık fiyat geçmişi gerekir.")
        return

    names = list(model_desc)
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    model = c1.selectbox(
        "Model", names, index=names.index("hrp") if "hrp" in names else 0,
        format_func=lambda m: f"{m} — {model_desc[m]}", key="hold_model",
    )
    has_cash = (table["Tür"] == KIND_CASH).any()
    include_cash = c2.checkbox("Nakdi de yatırıma dahil et", value=True, disabled=not has_cash, key="hold_cash")
    st.caption(
        f"Model, varlıkların son {len(returns) // 252 or 1} yıllık TL getirileriyle eğitilir. "
        "BIST hisseleri tam adete yuvarlanır."
    )

    errors: list = []
    with st.spinner("Hedef ağırlıklar hesaplanıyor…"):
        weights = fit_weights(returns, [model], on_error=lambda n, e: errors.append(e))
    if errors or weights.empty:
        st.warning(f"Bu model bu varlıklarla çözüm bulamadı: {errors[0] if errors else ''}. Başka bir model deneyin.")
        return
    target = weights[model]
    whole = {p.label for p in positions if p.kind == KIND_BIST}
    reb = rebalance(table, target, prices_try.iloc[-1], include_cash=include_cash and has_cash, whole_units=whole)

    def _color(v):
        return "color: #2e9e5b; font-weight:600" if v == "Al" else ("color: #d9534f; font-weight:600" if v == "Sat" else "")

    st.dataframe(
        reb.style.format(
            {
                "Mevcut (TL)": "₺{:,.0f}",
                "Mevcut ağırlık": "{:.1%}",
                "Hedef ağırlık": "{:.1%}",
                "Hedef (TL)": "₺{:,.0f}",
                "Adet": _num,
                "Tutar (TL)": "₺{:,.0f}",
            }
        ).map(_color, subset=["İşlem"]),
        hide_index=True,
        width="stretch",
    )
    if has_cash:
        cash_after = reb.attrs.get("cash_after", 0.0)
        if cash_after < -1:
            st.warning(f"Bu işlemler için {_fmt_tl(-cash_after)} ek nakit gerekir.")
        else:
            st.caption(f"İşlemler sonrası kalan nakit: {_fmt_tl(cash_after)} (TL karşılığı).")
    turnover = float(reb["Tutar (TL)"].sum())
    if total and not math.isnan(turnover):
        st.caption(f"Toplam işlem hacmi: {_fmt_tl(turnover)} (portföyün %{turnover / total * 100:.0f}'i). "
                   "Komisyon ve vergiler dahil değildir.")
