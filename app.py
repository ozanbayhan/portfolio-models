"""Portföy modelleri — web arayüzü.

Yerelde:  uv run streamlit run app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st
from skfolio import RiskMeasure
from skfolio.optimization import MeanRisk, ObjectiveFunction
from skfolio.prior import BlackLitterman

from portfolio_models import backtest, bist, fit_weights, list_models, summarize, to_returns
from portfolio_models.data import clean_prices, load_prices

st.set_page_config(page_title="Portföy Modelleri", page_icon="📊", layout="wide")

MODEL_DESC = dict(list_models())
DEFAULT_MODELS = ["equal_weighted", "inverse_volatility", "min_variance", "max_sharpe", "risk_parity", "hrp", "min_cvar"]
PCT_COLS = ["Yıllık getiri", "Yıllık volatilite", "Maks. düşüş", "CVaR %95"]


@st.cache_data(ttl=3600, show_spinner="Fiyatlar indiriliyor…")
def cached_prices(tickers: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    return load_prices(list(tickers), start=start, end=end)


@st.cache_data(show_spinner=False)
def read_uploaded(data: bytes) -> pd.DataFrame:
    from io import BytesIO

    return clean_prices(pd.read_csv(BytesIO(data), index_col=0, parse_dates=True))


# --- Kenar çubuğu ------------------------------------------------------------

with st.sidebar:
    st.header("Veri")
    source = st.radio("Kaynak", ["Yahoo Finance", "CSV dosyası"], horizontal=True, label_visibility="collapsed")
    if source == "Yahoo Finance":
        bist_text = st.text_input("BIST hisseleri", "THYAO ASELS EREGL GARAN BIMAS", help="Boşlukla ayırın; .IS eki otomatik eklenir.")
        other_text = st.text_input("Diğer semboller", "GC=F", help="Yahoo sembolleri: GC=F (altın), USDTRY=X, BTC-USD, AAPL…")
        c1, c2 = st.columns(2)
        start = c1.date_input("Başlangıç", date(2020, 1, 1), min_value=date(2000, 1, 1))
        end = c2.date_input("Bitiş", date.today())
        uploaded = None
    else:
        uploaded = st.file_uploader("Fiyat dosyası (.csv)", type="csv", help="İlk sütun tarih, diğer sütunlar varlık fiyatları.")

    st.header("Modeller")
    models = st.multiselect(
        "Karşılaştırılacak modeller",
        options=list(MODEL_DESC),
        default=DEFAULT_MODELS,
        format_func=lambda m: f"{m} — {MODEL_DESC[m]}",
        label_visibility="collapsed",
    )
    if st.button("Tümünü seç", width="stretch"):
        models = list(MODEL_DESC)

    st.header("Backtest")
    train = st.slider("Eğitim penceresi (iş günü)", 63, 756, 252, step=21, help="252 ≈ 1 yıl")
    test = st.slider("Yeniden dengeleme aralığı (iş günü)", 5, 126, 21, step=1, help="21 ≈ 1 ay")

# --- Veri yükleme ------------------------------------------------------------

st.title("📊 Portföy Modelleri")
st.caption(
    "skfolio · Riskfolio-Lib · PyPortfolioOpt — "
    "[GitHub](https://github.com/ozanbayhan/portfolio-models) · Eğitim amaçlıdır, yatırım tavsiyesi değildir."
)

try:
    if source == "CSV dosyası":
        if uploaded is None:
            st.info("Sol panelden bir CSV dosyası yükleyin.")
            st.stop()
        prices = read_uploaded(uploaded.getvalue())
    else:
        tickers = bist(*bist_text.split()) + other_text.split()
        if len(tickers) < 2:
            st.warning("En az 2 sembol girin.")
            st.stop()
        prices = cached_prices(tuple(tickers), str(start), str(end))
except Exception as exc:  # noqa: BLE001
    st.error(f"Veri yüklenemedi: {exc}")
    st.stop()

returns = to_returns(prices)
if not models:
    st.warning("En az bir model seçin.")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Varlık", prices.shape[1])
m2.metric("Gün", len(prices))
m3.metric("Dönem", f"{prices.index[0]:%d.%m.%Y} → {prices.index[-1]:%d.%m.%Y}")

tab_w, tab_bt, tab_bl, tab_data, tab_info = st.tabs(
    ["Ağırlıklar", "Backtest", "Black-Litterman", "Veri", "Modeller"]
)


def show_errors(errors: list[tuple[str, Exception]]) -> None:
    for name, exc in errors:
        st.warning(f"**{name}** atlandı: {exc}")


# --- Ağırlıklar --------------------------------------------------------------

with tab_w:
    st.subheader("Güncel ağırlıklar")
    st.caption("Her model seçilen dönemin tamamıyla eğitilir; bugün kurulacak portföyü gösterir.")
    errors: list = []
    with st.spinner("Modeller eğitiliyor…"):
        weights = fit_weights(returns, models, on_error=lambda n, e: errors.append((n, e)))
    show_errors(errors)
    if not weights.empty:
        st.dataframe(
            weights.style.format("{:.1%}").background_gradient(cmap="Blues", axis=None),
            width="stretch",
        )
        long = weights.reset_index(names="Varlık").melt("Varlık", var_name="Model", value_name="Ağırlık")
        fig = px.bar(long, x="Model", y="Ağırlık", color="Varlık", barmode="stack")
        fig.update_layout(yaxis_tickformat=".0%", height=450, legend_title=None)
        st.plotly_chart(fig, width="stretch")
        st.download_button("CSV indir", weights.to_csv().encode(), "weights.csv", "text/csv")

# --- Backtest ----------------------------------------------------------------

with tab_bt:
    st.subheader("Walk-forward backtest")
    st.caption(
        f"Her model {train} iş günü veriyle eğitilir, sonraki {test} gün tutulur, sonra pencere kaydırılır. "
        "Sonuçlar yalnızca modelin o an göremediği verilerden hesaplanır."
    )
    if len(returns) <= train + test:
        st.warning("Bu ayarlar için veri kısa; başlangıç tarihini geriye alın veya eğitim penceresini küçültün.")
    else:
        bt_key = (tuple(returns.columns), str(returns.index[0]), str(returns.index[-1]), tuple(models), train, test)
        if st.button("Backtest'i çalıştır", type="primary"):
            errors = []
            with st.spinner(f"{len(models)} model test ediliyor…"):
                population = backtest(
                    returns, models, train_size=train, test_size=test, on_error=lambda n, e: errors.append((n, e))
                )
            st.session_state["bt"] = (bt_key, population, errors)
        saved = st.session_state.get("bt")
        if saved and saved[0] != bt_key:
            st.info("Ayarlar değişti; güncel sonuç için backtest'i yeniden çalıştırın.")
            saved = None
        population, errors = (saved[1], saved[2]) if saved else (None, [])
        show_errors(errors)
        if population is not None and len(population):
            table = summarize(population)
            fmt = {c: "{:.1%}" for c in PCT_COLS if c in table}
            fmt |= {c: "{:.2f}" for c in ("Sharpe", "Sortino") if c in table}
            st.dataframe(
                table.style.format(fmt).highlight_max(subset=["Sharpe"], props="background-color:#c6efce;color:#111;font-weight:600"),
                width="stretch",
            )
            st.plotly_chart(population.plot_cumulative_returns(), width="stretch")
            st.plotly_chart(population.plot_drawdowns(), width="stretch")
            st.plotly_chart(population.plot_composition(), width="stretch")
            st.download_button("Özet CSV indir", table.to_csv().encode(), "backtest_summary.csv", "text/csv")

# --- Black-Litterman ---------------------------------------------------------

with tab_bl:
    st.subheader("Kendi görüşlerinizle Black-Litterman")
    st.caption(
        "Görüşlerinizi yıllık getiri olarak girin. **Mutlak**: varlık bu kadar getirir. "
        "**Göreli**: Varlık 1, Varlık 2'yi bu kadar geçer. Model geçmiş veriyle görüşlerinizi harmanlar."
    )
    assets = list(returns.columns)
    default_views = pd.DataFrame(
        [
            {"Tür": "Mutlak", "Varlık 1": assets[0], "Varlık 2": None, "Yıllık getiri %": 25.0},
            {"Tür": "Göreli", "Varlık 1": assets[1], "Varlık 2": assets[-1], "Yıllık getiri %": 10.0},
        ]
    )
    views_df = st.data_editor(
        default_views,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Tür": st.column_config.SelectboxColumn(options=["Mutlak", "Göreli"], required=True),
            "Varlık 1": st.column_config.SelectboxColumn(options=assets, required=True),
            "Varlık 2": st.column_config.SelectboxColumn(options=assets),
            "Yıllık getiri %": st.column_config.NumberColumn(format="%.1f", step=1.0, required=True),
        },
        key="bl_views",
    )
    tau = st.slider("Görüşlere güven (tau)", 0.01, 0.5, 0.05, 0.01, help="Büyüdükçe görüşleriniz daha ağır basar.")

    views: list[str] = []
    for _, row in views_df.dropna(subset=["Varlık 1", "Yıllık getiri %"]).iterrows():
        daily = row["Yıllık getiri %"] / 100 / 252
        if row["Tür"] == "Göreli" and row["Varlık 2"] and row["Varlık 2"] != row["Varlık 1"]:
            views.append(f"{row['Varlık 1']} - {row['Varlık 2']} == {daily:.8f}")
        elif row["Tür"] == "Mutlak":
            views.append(f"{row['Varlık 1']} == {daily:.8f}")

    if views and st.button("Hesapla", type="primary", key="bl_run"):
        try:
            base = MeanRisk(objective_function=ObjectiveFunction.MAXIMIZE_RATIO, risk_measure=RiskMeasure.VARIANCE)
            bl = MeanRisk(
                objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
                risk_measure=RiskMeasure.VARIANCE,
                prior_estimator=BlackLitterman(views=views, tau=tau),
            )
            base.fit(returns)
            bl.fit(returns)
            comp = pd.DataFrame(
                {"Görüşsüz (maks. Sharpe)": base.weights_, "Görüşlerle (Black-Litterman)": bl.weights_},
                index=assets,
            )
            st.dataframe(comp.style.format("{:.1%}"), width="stretch")
            long = comp.reset_index(names="Varlık").melt("Varlık", var_name="Model", value_name="Ağırlık")
            fig = px.bar(long, x="Varlık", y="Ağırlık", color="Model", barmode="group")
            fig.update_layout(yaxis_tickformat=".0%", legend_title=None)
            st.plotly_chart(fig, width="stretch")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Hesaplanamadı: {exc}")

# --- Veri --------------------------------------------------------------------

with tab_data:
    st.subheader("Normalize fiyatlar (başlangıç = 100)")
    st.plotly_chart(px.line(prices / prices.iloc[0] * 100), width="stretch")
    st.subheader("Korelasyon")
    st.plotly_chart(
        px.imshow(returns.corr(), text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1),
        width="stretch",
    )

# --- Model listesi -----------------------------------------------------------

with tab_info:
    st.dataframe(
        pd.DataFrame(list_models(), columns=["Model", "Açıklama"]),
        hide_index=True,
        width="stretch",
    )
