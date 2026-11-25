"""Portföy modelleri — web arayüzü (TR / EN / DE).

Çalıştırma:  portfolio-models serve        (ya da: streamlit run src/portfolio_models/web/app.py)

Yapılandırma ortam değişkenleriyle ya da .streamlit/secrets.toml ile yapılır; ayrıntılar docs/self-hosting.md.
"""

from __future__ import annotations

import importlib
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


def _reload_own_modules_if_changed() -> None:
    """Streamlit Cloud git'ten yeni kod çekince yalnızca app.py'yi yeniden çalıştırır; içe aktarılan
    kendi modüllerimizi (src/portfolio_models, holdings_page.py) yeniden yüklemez. Dosyalar
    değiştiyse burada yeniden yükleyerek her güncellemenin elle yeniden başlatma gerekmeden yansımasını sağlarız."""
    pkg = Path(__file__).resolve().parent.parent  # src/portfolio_models
    files = sorted(pkg.glob("*.py")) + sorted((pkg / "web").glob("*.py"))
    stamp = tuple((f.name, f.stat().st_mtime_ns) for f in files if f.exists())
    state = sys.modules.setdefault("_pm_reload_state", type(sys)("_pm_reload_state"))
    previous = getattr(state, "stamp", None)
    state.stamp = stamp
    if previous == stamp:
        return
    # previous None: bu süreçte ilk çalıştırma. Modüller daha önce (eski sürüm app.py ile) yüklendiyse
    # yenilenir; taze süreçte henüz yüklenmedikleri için aşağıdaki döngü hiçbir şey yapmaz.
    # Bağımlılık sırasıyla: alt modüller önce, paket ve sayfa sonra
    for name in ("portfolio_models.i18n", "portfolio_models.locales", "portfolio_models.data",
                 "portfolio_models.adapters", "portfolio_models.models",
                 "portfolio_models.backtest", "portfolio_models.store", "portfolio_models.fund_prices",
                 "portfolio_models.holdings", "portfolio_models.trades_io", "portfolio_models.benchmarks",
                 "portfolio_models.model_guide", "portfolio_models.report", "portfolio_models.insights",
                 "portfolio_models", "portfolio_models.web.ui", "portfolio_models.web.holdings_page"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    if previous is not None:
        st.cache_data.clear()


_reload_own_modules_if_changed()
from skfolio import RiskMeasure
from skfolio.optimization import MeanRisk, ObjectiveFunction
from skfolio.prior import BlackLitterman

from portfolio_models import backtest, bist, fit_weights, insights, list_models, model_guide, store, summarize, to_returns
from portfolio_models.data import clean_prices, load_prices
from portfolio_models.i18n import LANGS, set_lang, t

# --- Dil ------------------------------------------------------------------------
# Öncelik: adres çubuğu (?lang=) → bu oturumda seçilen → Türkçe.
# Tarayıcı dili kullanılmaz: uygulama Türk yatırımcılara yönelik; dil seçici her sayfada en üstte.


def _initial_lang() -> str:
    q = st.query_params.get("lang")
    if q in LANGS:
        return q
    if st.session_state.get("lang") in LANGS:
        return st.session_state["lang"]
    return "tr"


st.session_state["lang"] = _initial_lang()
set_lang(st.session_state["lang"])
st.set_page_config(page_title=t("Portföy Modelleri"), page_icon="📊", layout="wide")

PRIVACY = {
    "tr": """
# Gizlilik Politikası

*Son güncelleme: 25 Kasım 2026*

**Portföy Modelleri** ([portfolio-models.streamlit.app](https://portfolio-models.streamlit.app)) açık kaynaklı,
ücretsiz bir portföy analiz aracıdır. Kaynak kodu: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models).

### Hangi verileri topluyoruz?
- **Girişsiz kullanımda:** hiçbir kişisel veri saklanmaz. Girdiğiniz semboller ve yüklediğiniz dosyalar yalnızca oturumunuz süresince sunucu belleğinde tutulur.
- **Google ile giriş yaptığınızda:** Google'dan yalnızca e-posta adresiniz ve adınız alınır (`openid`, `email`, `profile`). Google hesabınızdaki başka hiçbir veriye erişilmez.
- **Portföy kaydettiğinizde:** e-posta adresiniz ile kaydettiğiniz ayarlar, pozisyonlar, işlemler ve fon fiyatları bir veritabanında saklanır.
- **Haftalık e-posta özetini açtıysanız:** her pazartesi e-posta adresinize portföy özetiniz gönderilir; istediğiniz an kapatabilirsiniz.

### Verileri nasıl kullanıyoruz?
Yalnızca kayıtlarınızı size göstermek ve istediyseniz haftalık özetinizi göndermek için. Veriler satılmaz, paylaşılmaz, reklam veya analiz için kullanılmaz.
Her kullanıcı yalnızca kendi kayıtlarını görebilir.

### Nerede saklanıyor?
Supabase (PostgreSQL) üzerinde, AB bölgesinde (Frankfurt). Uygulama Streamlit Community Cloud'da çalışır.

### Verilerinizi silme
Kayıtlarınızı uygulamadaki **Sil** butonlarıyla istediğiniz an silebilirsiniz. Tüm verilerinizin silinmesi için
[GitHub Issues](https://github.com/ozanbayhan/portfolio-models/issues) üzerinden talepte bulunabilirsiniz.

### Google API kullanımı
Bu uygulamanın Google API'lerinden aldığı bilgileri kullanımı, Limited Use gereklilikleri dahil olmak üzere
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy)'ye uygundur.
""",
    "en": """
# Privacy Policy

*Last updated: 25 November 2026*

**Portfolio Models** ([portfolio-models.streamlit.app](https://portfolio-models.streamlit.app)) is a free, open-source
portfolio analysis tool. Source code: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models).

### What data do we collect?
- **Without signing in:** no personal data is stored. Symbols you enter and files you upload stay in server memory only for your session.
- **When you sign in with Google:** we receive only your email address and name (`openid`, `email`, `profile`). No other data in your Google account is accessed.
- **When you save a portfolio:** your email address and the settings, positions, transactions and fund prices you save are stored in a database.
- **If you enable the weekly email summary:** a summary of your portfolio is sent to your email every Monday; you can switch it off at any time.

### How do we use it?
Only to show you your saved data and, if you asked for it, to send your weekly summary. Data is never sold, shared or used for advertising or analytics.
Each user can see only their own records.

### Where is it stored?
In Supabase (PostgreSQL) in the EU (Frankfurt). The app runs on Streamlit Community Cloud.

### Deleting your data
You can delete your records at any time with the **Delete** buttons in the app. To have all your data removed, open a request on
[GitHub Issues](https://github.com/ozanbayhan/portfolio-models/issues).

### Use of Google APIs
This app's use of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements.
""",
    "de": """
# Datenschutzerklärung

*Zuletzt aktualisiert: 25. November 2026*

**Portfolio-Modelle** ([portfolio-models.streamlit.app](https://portfolio-models.streamlit.app)) ist ein kostenloses
Open-Source-Werkzeug zur Portfolioanalyse. Quellcode: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models).

### Welche Daten erheben wir?
- **Ohne Anmeldung:** Es werden keine personenbezogenen Daten gespeichert. Eingegebene Symbole und hochgeladene Dateien bleiben nur während Ihrer Sitzung im Serverspeicher.
- **Bei Anmeldung mit Google:** Wir erhalten nur Ihre E-Mail-Adresse und Ihren Namen (`openid`, `email`, `profile`). Auf andere Daten Ihres Google-Kontos wird nicht zugegriffen.
- **Beim Speichern eines Portfolios:** Ihre E-Mail-Adresse sowie die gespeicherten Einstellungen, Positionen, Transaktionen und Fondspreise werden in einer Datenbank abgelegt.
- **Wenn Sie die wöchentliche E-Mail-Zusammenfassung aktivieren:** Jeden Montag wird eine Zusammenfassung Ihres Portfolios an Ihre E-Mail-Adresse gesendet; Sie können sie jederzeit abschalten.

### Wie verwenden wir die Daten?
Nur um Ihnen Ihre gespeicherten Daten anzuzeigen und, falls gewünscht, Ihre wöchentliche Zusammenfassung zu senden. Daten werden weder verkauft noch weitergegeben noch für Werbung oder Analysen genutzt.
Jede Person sieht nur ihre eigenen Einträge.

### Wo werden sie gespeichert?
Bei Supabase (PostgreSQL) in der EU (Frankfurt). Die App läuft auf Streamlit Community Cloud.

### Löschen Ihrer Daten
Sie können Ihre Einträge jederzeit mit den **Löschen**-Schaltflächen in der App entfernen. Für die Löschung aller Daten stellen Sie eine Anfrage über
[GitHub Issues](https://github.com/ozanbayhan/portfolio-models/issues).

### Nutzung von Google-APIs
Die Nutzung von Informationen aus Google-APIs durch diese App entspricht der
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), einschließlich der Anforderungen zur eingeschränkten Nutzung (Limited Use).
""",
}

TERMS = {
    "tr": """
# Kullanım Koşulları

*Son güncelleme: 25 Kasım 2026*

- Portföy Modelleri **eğitim ve araştırma amaçlı**, ücretsiz ve açık kaynaklı bir araçtır. **Yatırım tavsiyesi değildir.**
- Sonuçlar ve yorumlar geçmiş verilere dayanır; geçmiş performans gelecekteki sonuçları garanti etmez.
- Piyasa verileri Yahoo Finance'ten, enflasyon verileri TCMB EVDS ve OECD'den alınır; doğruluğu ve sürekliliği garanti edilmez.
- Araç "olduğu gibi" sunulur; kullanımından doğan kayıplardan geliştirici sorumlu tutulamaz.
- Hizmet önceden haber verilmeksizin değiştirilebilir veya durdurulabilir.
- Gizlilik ile ilgili ayrıntılar için [Gizlilik Politikası](?page=privacy&lang=tr).

Kaynak kodu MIT lisansıyla: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models)
""",
    "en": """
# Terms of Use

*Last updated: 25 November 2026*

- Portfolio Models is a free, open-source tool **for education and research**. **It is not investment advice.**
- Results and comments are based on historical data; past performance does not guarantee future results.
- Market data comes from Yahoo Finance and inflation data from the CBRT (EVDS) and OECD; accuracy and availability are not guaranteed.
- The tool is provided "as is"; the developer is not liable for any losses arising from its use.
- The service may be changed or discontinued without notice.
- For privacy details see the [Privacy Policy](?page=privacy&lang=en).

Source code under the MIT licence: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models)
""",
    "de": """
# Nutzungsbedingungen

*Zuletzt aktualisiert: 25. November 2026*

- Portfolio-Modelle ist ein kostenloses Open-Source-Werkzeug **für Bildung und Forschung**. **Es stellt keine Anlageberatung dar.**
- Ergebnisse und Kommentare beruhen auf historischen Daten; vergangene Wertentwicklung ist keine Garantie für die Zukunft.
- Marktdaten stammen von Yahoo Finance, Inflationsdaten von der türkischen Zentralbank (EVDS) und der OECD; Richtigkeit und Verfügbarkeit werden nicht garantiert.
- Das Werkzeug wird „wie besehen“ bereitgestellt; der Entwickler haftet nicht für Verluste aus seiner Nutzung.
- Der Dienst kann ohne Ankündigung geändert oder eingestellt werden.
- Einzelheiten zum Datenschutz finden Sie in der [Datenschutzerklärung](?page=privacy&lang=de).

Quellcode unter MIT-Lizenz: [github.com/ozanbayhan/portfolio-models](https://github.com/ozanbayhan/portfolio-models)
""",
}

_page = st.query_params.get("page")
if _page in ("privacy", "terms"):
    lang = st.session_state["lang"]
    st.markdown((PRIVACY if _page == "privacy" else TERMS)[lang])
    st.markdown(f"[{t('← Uygulamaya dön')}](/?lang={lang})")
    st.stop()


def model_desc() -> dict[str, str]:
    """Model adı -> etkin dildeki kısa açıklama."""
    return dict(list_models())


DEFAULT_MODELS = ["equal_weighted", "inverse_volatility", "min_variance", "max_sharpe", "risk_parity", "hrp", "min_cvar"]
PCT_COLS = ["Yıllık getiri", "Yıllık volatilite", "Maks. düşüş", "CVaR %95"]
SOURCE_YAHOO, SOURCE_CSV = "Yahoo Finance", "CSV dosyası"  # iç değerler (kayıtlarda saklanır)
VIEW_ABS, VIEW_REL = "Mutlak", "Göreli"
ABS_ALIASES = {"Mutlak", "Absolute", "Absolut"}
REL_ALIASES = {"Göreli", "Relative", "Relativ"}


@st.cache_data(ttl=3600, show_spinner=False)
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


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


AUTH_ENABLED = _secret("auth") is not None
# Yerel mod (girişsiz, tek kullanıcı): secrets.toml'da `local_mode = true` ya da PM_LOCAL_MODE=1.
# Giriş (auth) ayarlıysa asla açılmaz: aksi halde tüm ziyaretçiler aynı kayıtları paylaşırdı.
LOCAL_MODE = not AUTH_ENABLED and (_secret("local_mode") is True or _env_flag("PM_LOCAL_MODE"))
DB_URL = _secret("connections", "portfolios", "url") or os.environ.get("PM_DATABASE_URL") or None
DATA_DIR = Path(os.environ.get("PM_DATA_DIR", ".")).expanduser()
LOCAL_DB = f"sqlite:///{DATA_DIR / 'portfolios.db'}"

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
st.session_state.setdefault("source", SOURCE_YAHOO)
# Sayfa değiştirince Streamlit, ekranda olmayan widget'ların değerlerini siler; korumak için yeniden atıyoruz.
for _k in ("bist_text", "other_text", "start", "end", "models", "train", "test", "source"):
    st.session_state[_k] = st.session_state[_k]


@st.cache_resource(show_spinner=False)
def _engine(url: str, schema: tuple[str, ...]):
    # schema anahtarı: yeni tablo eklendiğinde (kod güncellemesi) önbellek yenilenir ve tablo oluşturulur.
    return store.make_engine(url)


def get_engine(url: str):
    return _engine(url, tuple(sorted(store.metadata.tables)))


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
    ss.source = SOURCE_YAHOO
    ss.bist_text = cfg.get("bist_text", DEFAULTS["bist_text"])
    ss.other_text = cfg.get("other_text", DEFAULTS["other_text"])
    ss.start = date.fromisoformat(cfg["start"]) if cfg.get("start") else DEFAULTS["start"]
    ss.end = date.fromisoformat(cfg["end"]) if cfg.get("end") else date.today()
    ss.models = [m for m in cfg.get("models", DEFAULT_MODELS) if m in model_desc()]
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
        st.session_state.flash = ("success", t("“{name}” yüklendi.", name=name))


def on_save(engine, email: str) -> None:
    name = (st.session_state.get("pf_name") or "").strip()
    try:
        store.save_portfolio(engine, email, name, current_config())
        st.session_state.pf_pick = name
        st.session_state.flash = ("success", t("“{name}” kaydedildi.", name=name))
    except ValueError as exc:
        st.session_state.flash = ("error", str(exc))


def on_delete(engine, email: str) -> None:
    name = st.session_state.get("pf_pick")
    if name and store.delete_portfolio(engine, email, name):
        st.session_state.pf_pick = None
        st.session_state.flash = ("success", t("“{name}” silindi.", name=name))


def select_all_models() -> None:
    st.session_state.models = list(model_desc())


def _on_lang_change() -> None:
    st.query_params["lang"] = st.session_state["lang_pick"]
    st.session_state["lang"] = st.session_state["lang_pick"]


def language_box() -> None:
    st.selectbox("🌐 Dil · Language · Sprache", list(LANGS), format_func=lambda k: LANGS[k],
                 index=list(LANGS).index(st.session_state["lang"]), key="lang_pick", on_change=_on_lang_change)


def login_box() -> None:
    """Kenar çubuğunun en üstünde, tüm sayfalarda görünen giriş/çıkış kutusu."""
    email = current_user()
    if email is None and not AUTH_ENABLED:
        st.caption(t("Giriş ve kayıt özelliği bu sunucuda henüz ayarlanmadı."))
    elif email is None:
        st.caption(t("Portföylerinizi kaydetmek için giriş yapın. Kayıtlarınızı yalnızca siz görürsünüz."))
        st.button(t("Google ile giriş yap"), on_click=st.login, type="primary", width="stretch")
    elif LOCAL_MODE:
        st.caption(t("Yerel mod: giriş kapalı, kayıtlar bu bilgisayardaki portfolios.db dosyasında."))
    else:
        c1, c2 = st.columns([3, 1])
        c1.caption(t("Giriş: **{email}**", email=email))
        c2.button(t("Çıkış"), on_click=st.logout, width="stretch")


def user_store():
    """(engine, email) ya da kayıt kullanılamıyorsa (None, neden)."""
    email = current_user()
    if email is None:
        return None, t("Kaydetmek için giriş yapın.")
    if not LOCAL_MODE and not DB_URL:
        return None, t("Veritabanı ayarlanmamış; kayıt özelliği kapalı.")
    try:
        return get_engine(DB_URL or LOCAL_DB), email
    except Exception as exc:  # noqa: BLE001
        return None, t("Veritabanına bağlanılamadı: {err}", err=exc.__class__.__name__)


def show_flash(key: str = "flash") -> None:
    flash = st.session_state.pop(key, None)
    if flash:
        getattr(st, flash[0])(flash[1])


def settings_panel() -> None:
    st.header(t("Analiz ayarlarım"))
    engine, email = user_store()
    if engine is None:
        st.caption(email)
        return
    try:
        saved = [p["name"] for p in store.list_portfolios(engine, email)]
    except Exception as exc:  # noqa: BLE001
        st.error(t("Veritabanına bağlanılamadı: {err}", err=exc.__class__.__name__))
        return

    show_flash()

    if saved:
        if st.session_state.get("pf_pick") not in saved:
            st.session_state.pf_pick = None
        st.selectbox(t("Kayıtlı ayarlar"), saved, index=None, placeholder=t("Seçin…"), key="pf_pick")
        c1, c2 = st.columns(2)
        c1.button(t("Yükle"), on_click=on_load, args=(engine, email), width="stretch",
                  disabled=not st.session_state.get("pf_pick"))
        c2.button(t("Sil"), on_click=on_delete, args=(engine, email), width="stretch",
                  disabled=not st.session_state.get("pf_pick"))
    else:
        st.caption(t("Henüz kayıtlı ayarınız yok."))

    with st.form("save_form", clear_on_submit=False, border=False):
        st.text_input(t("Bu ayarları kaydet"), key="pf_name", placeholder=t("Ad, örn. BIST + Altın"), max_chars=120)
        st.form_submit_button(t("Kaydet"), on_click=on_save, args=(engine, email), width="stretch",
                              disabled=st.session_state.get("source") == SOURCE_CSV)
    if st.session_state.get("source") == SOURCE_CSV:
        st.caption(t("CSV verisi kaydedilmez; kaydetmek için Yahoo Finance kaynağını kullanın."))


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


# --- Model analizi sayfası -------------------------------------------------

def analysis_page() -> None:
    descs = model_desc()

    with st.sidebar:
        settings_panel()

        st.header(t("Veri"))
        source = st.radio(t("Kaynak"), [SOURCE_YAHOO, SOURCE_CSV], horizontal=True, format_func=t,
                          label_visibility="collapsed", key="source")
        if source == SOURCE_YAHOO:
            bist_text = st.text_input(t("BIST hisseleri"), key="bist_text",
                                      help=t("Boşlukla ayırın; .IS eki otomatik eklenir."))
            other_text = st.text_input(t("Diğer semboller"), key="other_text",
                                       help=t("Yahoo sembolleri: GC=F (altın), USDTRY=X, BTC-USD, AAPL…"))
            c1, c2 = st.columns(2)
            start = c1.date_input(t("Başlangıç"), key="start", min_value=date(2000, 1, 1))
            end = c2.date_input(t("Bitiş"), key="end")
            uploaded = None
        else:
            uploaded = st.file_uploader(t("Fiyat dosyası (.csv)"), type="csv",
                                        help=t("İlk sütun tarih, diğer sütunlar varlık fiyatları."))

        st.header(t("Modeller"))
        models = st.multiselect(
            t("Karşılaştırılacak modeller"),
            options=list(descs),
            format_func=lambda m: f"{m} — {descs[m]}",
            label_visibility="collapsed",
            key="models",
        )
        st.button(t("Tümünü seç"), width="stretch", on_click=select_all_models)

        st.header("Backtest")
        train = st.slider(t("Eğitim penceresi (iş günü)"), 63, 756, step=21, help=t("252 ≈ 1 yıl"), key="train")
        test = st.slider(t("Yeniden dengeleme aralığı (iş günü)"), 5, 126, step=1, help=t("21 ≈ 1 ay"), key="test")

    # --- Veri yükleme ------------------------------------------------------------

    st.title(t("📊 Model analizi"))
    lang = st.session_state["lang"]
    st.caption(
        "skfolio · Riskfolio-Lib · PyPortfolioOpt — "
        f"[GitHub](https://github.com/ozanbayhan/portfolio-models) · [{t('Gizlilik')}](?page=privacy&lang={lang}) · "
        f"[{t('Koşullar')}](?page=terms&lang={lang}) · " + t("Eğitim amaçlıdır, yatırım tavsiyesi değildir.")
    )

    try:
        if source == SOURCE_CSV:
            if uploaded is None:
                st.info(t("Sol panelden bir CSV dosyası yükleyin."))
                st.stop()
            prices = read_uploaded(uploaded.getvalue())
        else:
            tickers = bist(*bist_text.split()) + other_text.split()
            if len(tickers) < 2:
                st.warning(t("En az 2 sembol girin."))
                st.stop()
            with st.spinner(t("Fiyatlar indiriliyor…")):
                prices = cached_prices(tuple(tickers), str(start), str(end))
    except Exception as exc:  # noqa: BLE001
        st.error(t("Veri yüklenemedi: {err}", err=exc))
        st.stop()

    returns = to_returns(prices)
    if not models:
        st.warning(t("En az bir model seçin."))
        st.stop()

    m1, m2, m3 = st.columns(3)
    m1.metric(t("Varlık"), prices.shape[1])
    m2.metric(t("Gün"), len(prices))
    m3.metric(t("Dönem"), f"{prices.index[0]:%d.%m.%Y} → {prices.index[-1]:%d.%m.%Y}")

    tab_w, tab_bt, tab_bl, tab_data, tab_info = st.tabs(
        [t("Ağırlıklar"), "Backtest", "Black-Litterman", t("Veri"), t("📚 Modeller ve rehber")]
    )

    def show_errors(errors: list[tuple[str, Exception]]) -> None:
        for name, exc in errors:
            st.warning(t("**{name}** atlandı: {err}", name=name, err=exc))

    col_asset, col_weight = t("Varlık"), t("Ağırlık")

    # --- Ağırlıklar --------------------------------------------------------------

    with tab_w:
        st.subheader(t("Güncel ağırlıklar"))
        st.caption(t("Her model seçilen dönemin tamamıyla eğitilir; bugün kurulacak portföyü gösterir."))
        errors: list = []
        with st.spinner(t("Modeller eğitiliyor…")):
            weights = fit_weights(returns, models, on_error=lambda n, e: errors.append((n, e)))
        show_errors(errors)
        if not weights.empty:
            st.dataframe(
                weights.style.format("{:.1%}").background_gradient(cmap="Blues", axis=None),
                width="stretch",
            )
            long = weights.reset_index(names=col_asset).melt(col_asset, var_name="Model", value_name=col_weight)
            fig = px.bar(long, x="Model", y=col_weight, color=col_asset, barmode="stack")
            fig.update_layout(yaxis_tickformat=".0%", height=450, legend_title=None)
            st.plotly_chart(fig, width="stretch")
            st.download_button(t("CSV indir"), weights.to_csv().encode(), "weights.csv", "text/csv")

            st.subheader(t("🧠 Yorumlar"))
            st.caption(t("Ekrandaki ağırlıklardan ve seçilen dönemin fiyat verisinden otomatik üretilir. "
                         "Eğitim amaçlıdır, yatırım tavsiyesi değildir."))
            with st.container(border=True):
                st.markdown(t("**Genel tablo**"))
                st.markdown(_bullets(insights.consensus(weights) + insights.asset_facts(returns)))
            baseline = insights.weight_metrics(pd.Series(1 / returns.shape[1], index=returns.columns), returns)
            for model_name in weights.columns:
                with st.expander(f"{model_name} — {descs.get(model_name, '')}"):
                    st.markdown(insights.model_comment(model_name, weights[model_name], returns, baseline))
                    guide = model_guide.markdown(model_name)
                    if guide:
                        st.divider()
                        st.markdown(t("**📚 Tarihçe ve okuma rehberi**"))
                        st.markdown(guide)

    # --- Backtest ----------------------------------------------------------------

    with tab_bt:
        st.subheader("Walk-forward backtest")
        st.caption(t("Her model {train} iş günü veriyle eğitilir, sonraki {test} gün tutulur, sonra pencere kaydırılır. "
                     "Sonuçlar yalnızca modelin o an göremediği verilerden hesaplanır.", train=train, test=test))
        if len(returns) <= train + test:
            st.warning(t("Bu ayarlar için veri kısa; başlangıç tarihini geriye alın veya eğitim penceresini küçültün."))
        else:
            bt_key = (tuple(returns.columns), str(returns.index[0]), str(returns.index[-1]), tuple(models), train, test)
            if st.button(t("Backtest'i çalıştır"), type="primary"):
                errors = []
                with st.spinner(t("{n} model test ediliyor…", n=len(models))):
                    population = backtest(
                        returns, models, train_size=train, test_size=test, on_error=lambda n, e: errors.append((n, e))
                    )
                st.session_state["bt"] = (bt_key, population, errors)
            saved = st.session_state.get("bt")
            if saved and saved[0] != bt_key:
                st.info(t("Ayarlar değişti; güncel sonuç için backtest'i yeniden çalıştırın."))
                saved = None
            population, errors = (saved[1], saved[2]) if saved else (None, [])
            show_errors(errors)
            if population is not None and len(population):
                table = summarize(population).rename(columns=t)
                fmt = {t(c): "{:.1%}" for c in PCT_COLS if t(c) in table}
                fmt |= {c: "{:.2f}" for c in ("Sharpe", "Sortino") if c in table}
                st.dataframe(
                    table.style.format(fmt).highlight_max(
                        subset=["Sharpe"], props="background-color:#c6efce;color:#111;font-weight:600"),
                    width="stretch",
                )
                with st.container(border=True):
                    st.markdown(t("**🧠 Yorum**"))
                    st.markdown(_bullets(insights.backtest_comment(table)))
                st.plotly_chart(population.plot_cumulative_returns(), width="stretch")
                st.plotly_chart(population.plot_drawdowns(), width="stretch")
                st.plotly_chart(population.plot_composition(), width="stretch")
                st.download_button(t("Özet CSV indir"), table.to_csv().encode(), "backtest_summary.csv", "text/csv")

    # --- Black-Litterman ---------------------------------------------------------

    with tab_bl:
        st.subheader(t("Kendi görüşlerinizle Black-Litterman"))
        st.caption(t("Görüşlerinizi yıllık getiri olarak girin. **Mutlak**: varlık bu kadar getirir. "
                     "**Göreli**: Varlık 1, Varlık 2'yi bu kadar geçer. Model geçmiş veriyle görüşlerinizi harmanlar."))
        assets = list(returns.columns)
        abs_label, rel_label = t(VIEW_ABS), t(VIEW_REL)
        loaded = st.session_state.get("bl_loaded")
        if loaded:
            default_views = pd.DataFrame(loaded, columns=["Tür", "Varlık 1", "Varlık 2", "Yıllık getiri %"])
            default_views = default_views[default_views["Varlık 1"].isin(assets)]
            default_views.loc[~default_views["Varlık 2"].isin(assets), "Varlık 2"] = None
            default_views["Tür"] = default_views["Tür"].map(
                lambda v: abs_label if v in ABS_ALIASES else (rel_label if v in REL_ALIASES else v))
        else:
            default_views = pd.DataFrame(
                [
                    {"Tür": abs_label, "Varlık 1": assets[0], "Varlık 2": None, "Yıllık getiri %": 25.0},
                    {"Tür": rel_label, "Varlık 1": assets[1], "Varlık 2": assets[-1], "Yıllık getiri %": 10.0},
                ]
            )
        views_df = st.data_editor(
            default_views,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "Tür": st.column_config.SelectboxColumn(t("Tür"), options=[abs_label, rel_label], required=True),
                "Varlık 1": st.column_config.SelectboxColumn(t("Varlık 1"), options=assets, required=True),
                "Varlık 2": st.column_config.SelectboxColumn(t("Varlık 2"), options=assets),
                "Yıllık getiri %": st.column_config.NumberColumn(t("Yıllık getiri %"), format="%.1f", step=1.0,
                                                                 required=True),
            },
            key=f"bl_views_{st.session_state.bl_version}_{lang}",
        )
        st.session_state.bl_current = views_df.astype(object).where(views_df.notna(), None).to_dict("records")
        tau = st.slider(t("Görüşlere güven (tau)"), 0.01, 0.5, 0.05, 0.01,
                        help=t("Büyüdükçe görüşleriniz daha ağır basar."))

        views: list[str] = []
        for _, row in views_df.dropna(subset=["Varlık 1", "Yıllık getiri %"]).iterrows():
            daily = row["Yıllık getiri %"] / 100 / 252
            if row["Tür"] in REL_ALIASES and row["Varlık 2"] and row["Varlık 2"] != row["Varlık 1"]:
                views.append(f"{row['Varlık 1']} - {row['Varlık 2']} == {daily:.8f}")
            elif row["Tür"] in ABS_ALIASES:
                views.append(f"{row['Varlık 1']} == {daily:.8f}")

        if views and st.button(t("Hesapla"), type="primary", key="bl_run"):
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
                    {t("Görüşsüz (maks. Sharpe)"): base.weights_, t("Görüşlerle (Black-Litterman)"): bl.weights_},
                    index=assets,
                )
                st.dataframe(comp.style.format("{:.1%}"), width="stretch")
                long = comp.reset_index(names=col_asset).melt(col_asset, var_name="Model", value_name=col_weight)
                fig = px.bar(long, x=col_asset, y=col_weight, color="Model", barmode="group")
                fig.update_layout(yaxis_tickformat=".0%", legend_title=None)
                st.plotly_chart(fig, width="stretch")
                with st.container(border=True):
                    st.markdown(t("**🧠 Yorum**"))
                    st.markdown(_bullets(insights.black_litterman_comment(
                        pd.Series(base.weights_, index=assets), pd.Series(bl.weights_, index=assets), views)))
            except Exception as exc:  # noqa: BLE001
                st.error(t("Hesaplanamadı: {err}", err=exc))
        with st.expander(t("📚 Black-Litterman nedir?")):
            st.markdown(model_guide.markdown("black_litterman"))

    # --- Veri --------------------------------------------------------------------

    with tab_data:
        st.subheader(t("Normalize fiyatlar (başlangıç = 100)"))
        st.plotly_chart(px.line(prices / prices.iloc[0] * 100), width="stretch")
        st.subheader(t("Korelasyon"))
        st.plotly_chart(
            px.imshow(returns.corr(), text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1),
            width="stretch",
        )

    # --- Model rehberi -------------------------------------------------------------

    with tab_info:
        st.subheader(t("Sonuçlar nasıl okunur?"))
        st.markdown(model_guide.metrics_markdown())
        st.subheader(t("Modeller: tarihçe ve okuma rehberi"))
        st.caption(t("Her modelin kim tarafından, ne zaman geliştirildiği, temel fikri ve sonuçlarının nasıl "
                     "okunacağı."))
        for name, desc in descs.items():
            year = model_guide.info(name, "year")
            with st.expander(f"{name} — {desc}" + (f" · {year}" if year and year != "—" else "")):
                st.markdown(model_guide.markdown(name))


# --- Sayfalar ----------------------------------------------------------------

from portfolio_models.web.holdings_page import holdings_page  # noqa: E402

with st.sidebar:
    language_box()
    login_box()

pg = st.navigation(
    [
        st.Page(analysis_page, title=t("Model analizi"), icon="📊", url_path="analiz", default=True),
        st.Page(lambda: holdings_page(user_store, show_flash, model_desc()), title=t("Portföyüm"), icon="💼",
                url_path="portfoyum"),
    ]
)
pg.run()
