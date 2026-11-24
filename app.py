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
from portfolio_models import store

st.set_page_config(page_title="Portföy Modelleri", page_icon="📊", layout="wide")

PRIVACY = """
# Gizlilik Politikası

*Son güncelleme: 24 Kasım 2026*

**Portföy Modelleri** ([portfolio-models.streamlit.app](https://portfolio-models.streamlit.app)) açık kaynaklı,
ücretsiz bir portföy analiz aracıdır. Kaynak kodu: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models).

### Hangi verileri topluyoruz?
- **Girişsiz kullanımda:** hiçbir kişisel veri saklanmaz. Girdiğiniz semboller ve yüklediğiniz dosyalar yalnızca oturumunuz süresince sunucu belleğinde tutulur.
- **Google ile giriş yaptığınızda:** Google'dan yalnızca e-posta adresiniz ve adınız alınır (`openid`, `email`, `profile`). Google hesabınızdaki başka hiçbir veriye erişilmez.
- **Portföy kaydettiğinizde:** e-posta adresiniz ile kaydettiğiniz ayarlar (semboller, tarihler, model seçimleri, görüşler) bir veritabanında saklanır.

### Verileri nasıl kullanıyoruz?
Yalnızca kayıtlı portföylerinizi size göstermek için. Veriler satılmaz, paylaşılmaz, reklam veya analiz için kullanılmaz.
Her kullanıcı yalnızca kendi kayıtlarını görebilir.

### Nerede saklanıyor?
Supabase (PostgreSQL) üzerinde, AB bölgesinde. Uygulama Streamlit Community Cloud'da çalışır.

### Verilerinizi silme
Kayıtlı portföylerinizi uygulamadaki **Sil** butonuyla istediğiniz an silebilirsiniz. Tüm verilerinizin silinmesi için
[GitHub Issues](https://github.com/ozanbayhan/portfolio-models/issues) üzerinden talepte bulunabilirsiniz.

### Google API kullanımı
Bu uygulamanın Google API'lerinden aldığı bilgileri kullanımı, Limited Use gereklilikleri dahil olmak üzere
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy)'ye uygundur.
"""

TERMS = """
# Kullanım Koşulları

*Son güncelleme: 24 Kasım 2026*

- Portföy Modelleri **eğitim ve araştırma amaçlı**, ücretsiz ve açık kaynaklı bir araçtır. **Yatırım tavsiyesi değildir.**
- Sonuçlar geçmiş verilere dayanır; geçmiş performans gelecekteki sonuçları garanti etmez.
- Piyasa verileri Yahoo Finance'ten alınır; doğruluğu ve sürekliliği garanti edilmez.
- Araç "olduğu gibi" sunulur; kullanımından doğan kayıplardan geliştirici sorumlu tutulamaz.
- Hizmet önceden haber verilmeksizin değiştirilebilir veya durdurulabilir.
- Gizlilik ile ilgili ayrıntılar için [Gizlilik Politikası](?page=privacy).

Kaynak kodu MIT lisansıyla: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models)
"""

_page = st.query_params.get("page")
if _page in ("privacy", "terms"):
    st.markdown(PRIVACY if _page == "privacy" else TERMS)
    st.markdown("[← Uygulamaya dön](/)")
    st.stop()

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


# --- Hesap ve kayıt ----------------------------------------------------------

def _secret(*keys: str):
    try:
        node = st.secrets
        for k in keys:
            node = node[k]
        return node
    except Exception:  # noqa: BLE001 - secrets dosyası yoksa ya da anahtar eksikse
        return None


AUTH_ENABLED = _secret("auth") is not None
# Yerel mod (girişsiz, tek kullanıcı) yalnızca kendi bilgisayarınızda, secrets.toml içinde
# `local_mode = true` yazılıysa açılır. Bulutta asla açık değildir: aksi halde tüm
# ziyaretçiler aynı kayıtları paylaşırdı.
LOCAL_MODE = not AUTH_ENABLED and _secret("local_mode") is True
DB_URL = _secret("connections", "portfolios", "url")
LOCAL_DB = f"sqlite:///{Path(__file__).parent / 'portfolios.db'}"

DEFAULTS = {
    "bist_text": "THYAO ASELS EREGL GARAN BIMAS",
    "other_text": "GC=F",
    "start": date(2020, 1, 1),
    "end": None,  # None = bugün
    "models": DEFAULT_MODELS,
    "train": 252,
    "test": 21,
    "bl_views": None,
}
for k, v in DEFAULTS.items():
    if k in ("end", "bl_views"):
        continue
    st.session_state.setdefault(k, v)
st.session_state.setdefault("end", date.today())
st.session_state.setdefault("bl_version", 0)


@st.cache_resource(show_spinner=False)
def get_engine(url: str):
    return store.make_engine(url)


def current_user() -> str | None:
    """Giriş yapan kullanıcının e-postası. Giriş ayarlı değilse (yerel geliştirme) sabit bir kullanıcı."""
    if LOCAL_MODE:
        return "yerel@localhost"
    if not AUTH_ENABLED:
        return None
    if st.user.get("is_logged_in", False):
        return st.user.get("email")
    return None


def current_config() -> dict:
    ss = st.session_state
    return {
        "bist_text": ss.bist_text,
        "other_text": ss.other_text,
        "start": str(ss.start),
        "end": str(ss.end),
        "models": list(ss.models),
        "train": ss.train,
        "test": ss.test,
        "bl_views": ss.get("bl_current"),
    }


def apply_config(cfg: dict) -> None:
    ss = st.session_state
    ss.source = "Yahoo Finance"
    ss.bist_text = cfg.get("bist_text", DEFAULTS["bist_text"])
    ss.other_text = cfg.get("other_text", DEFAULTS["other_text"])
    ss.start = date.fromisoformat(cfg["start"]) if cfg.get("start") else DEFAULTS["start"]
    ss.end = date.fromisoformat(cfg["end"]) if cfg.get("end") else date.today()
    ss.models = [m for m in cfg.get("models", DEFAULT_MODELS) if m in MODEL_DESC]
    ss.train = int(cfg.get("train", 252))
    ss.test = int(cfg.get("test", 21))
    ss.bl_loaded = cfg.get("bl_views")
    ss.bl_version += 1  # görüş tablosunu yeniden oluştur
    ss.pop("bt", None)


def on_load(engine, email: str) -> None:
    name = st.session_state.get("pf_pick")
    cfg = store.load_portfolio(engine, email, name) if name else None
    if cfg:
        apply_config(cfg)
        st.session_state.pf_name = name
        st.session_state.flash = ("success", f"“{name}” yüklendi.")


def on_save(engine, email: str) -> None:
    name = (st.session_state.get("pf_name") or "").strip()
    try:
        store.save_portfolio(engine, email, name, current_config())
        st.session_state.pf_pick = name
        st.session_state.flash = ("success", f"“{name}” kaydedildi.")
    except ValueError as exc:
        st.session_state.flash = ("error", str(exc))


def on_delete(engine, email: str) -> None:
    name = st.session_state.get("pf_pick")
    if name and store.delete_portfolio(engine, email, name):
        st.session_state.pf_pick = None
        st.session_state.flash = ("success", f"“{name}” silindi.")


def select_all_models() -> None:
    st.session_state.models = list(MODEL_DESC)


def account_panel() -> None:
    st.header("Portföylerim")
    email = current_user()
    if email is None and not AUTH_ENABLED:
        st.caption("Giriş ve kayıt özelliği bu sunucuda henüz ayarlanmadı.")
        return
    if email is None:
        st.caption("Portföylerinizi kaydetmek için giriş yapın. Kayıtlarınızı yalnızca siz görürsünüz.")
        st.button("Google ile giriş yap", on_click=st.login, type="primary", width="stretch")
        return

    if not LOCAL_MODE:
        c1, c2 = st.columns([3, 1])
        c1.caption(f"Giriş: **{email}**")
        c2.button("Çıkış", on_click=st.logout, width="stretch")
    else:
        st.caption("Yerel mod: giriş kapalı, kayıtlar bu bilgisayardaki portfolios.db dosyasında.")

    if not LOCAL_MODE and not DB_URL:
        st.warning("Veritabanı ayarlanmamış; kayıt özelliği kapalı.")
        return
    try:
        engine = get_engine(DB_URL or LOCAL_DB)
        saved = [p["name"] for p in store.list_portfolios(engine, email)]
    except Exception as exc:  # noqa: BLE001
        st.error(f"Veritabanına bağlanılamadı: {exc.__class__.__name__}")
        return

    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])

    if saved:
        if st.session_state.get("pf_pick") not in saved:
            st.session_state.pf_pick = None
        st.selectbox("Kayıtlı portföyler", saved, index=None, placeholder="Seçin…", key="pf_pick")
        c1, c2 = st.columns(2)
        c1.button("Yükle", on_click=on_load, args=(engine, email), width="stretch",
                  disabled=not st.session_state.get("pf_pick"))
        c2.button("Sil", on_click=on_delete, args=(engine, email), width="stretch",
                  disabled=not st.session_state.get("pf_pick"))
    else:
        st.caption("Henüz kayıtlı portföyünüz yok.")

    with st.form("save_form", clear_on_submit=False, border=False):
        st.text_input("Bu ayarları kaydet", key="pf_name", placeholder="Portföy adı, örn. BIST + Altın",
                      max_chars=120)
        st.form_submit_button("Kaydet", on_click=on_save, args=(engine, email), width="stretch",
                              disabled=st.session_state.get("source") == "CSV dosyası")
    if st.session_state.get("source") == "CSV dosyası":
        st.caption("CSV verisi kaydedilmez; kaydetmek için Yahoo Finance kaynağını kullanın.")


# --- Kenar çubuğu ------------------------------------------------------------

with st.sidebar:
    account_panel()

    st.header("Veri")
    source = st.radio("Kaynak", ["Yahoo Finance", "CSV dosyası"], horizontal=True,
                      label_visibility="collapsed", key="source")
    if source == "Yahoo Finance":
        bist_text = st.text_input("BIST hisseleri", key="bist_text", help="Boşlukla ayırın; .IS eki otomatik eklenir.")
        other_text = st.text_input("Diğer semboller", key="other_text",
                                   help="Yahoo sembolleri: GC=F (altın), USDTRY=X, BTC-USD, AAPL…")
        c1, c2 = st.columns(2)
        start = c1.date_input("Başlangıç", key="start", min_value=date(2000, 1, 1))
        end = c2.date_input("Bitiş", key="end")
        uploaded = None
    else:
        uploaded = st.file_uploader("Fiyat dosyası (.csv)", type="csv", help="İlk sütun tarih, diğer sütunlar varlık fiyatları.")

    st.header("Modeller")
    models = st.multiselect(
        "Karşılaştırılacak modeller",
        options=list(MODEL_DESC),
        format_func=lambda m: f"{m} — {MODEL_DESC[m]}",
        label_visibility="collapsed",
        key="models",
    )
    st.button("Tümünü seç", width="stretch", on_click=select_all_models)

    st.header("Backtest")
    train = st.slider("Eğitim penceresi (iş günü)", 63, 756, step=21, help="252 ≈ 1 yıl", key="train")
    test = st.slider("Yeniden dengeleme aralığı (iş günü)", 5, 126, step=1, help="21 ≈ 1 ay", key="test")

# --- Veri yükleme ------------------------------------------------------------

st.title("📊 Portföy Modelleri")
st.caption(
    "skfolio · Riskfolio-Lib · PyPortfolioOpt — "
    "[GitHub](https://github.com/ozanbayhan/portfolio-models) · [Gizlilik](?page=privacy) · [Koşullar](?page=terms) · "
    "Eğitim amaçlıdır, yatırım tavsiyesi değildir."
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
    loaded = st.session_state.get("bl_loaded")
    if loaded:
        default_views = pd.DataFrame(loaded, columns=["Tür", "Varlık 1", "Varlık 2", "Yıllık getiri %"])
        default_views = default_views[default_views["Varlık 1"].isin(assets)]
        default_views.loc[~default_views["Varlık 2"].isin(assets), "Varlık 2"] = None
    else:
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
        key=f"bl_views_{st.session_state.bl_version}",
    )
    st.session_state.bl_current = views_df.astype(object).where(views_df.notna(), None).to_dict("records")
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
