"""Ortak görsel düzen: stil, sayfa başı şeridi ve alt bilgi."""

from __future__ import annotations

import streamlit as st

from portfolio_models.charts import register_template
from portfolio_models.i18n import get_lang, t

REPO = "https://github.com/ozanbayhan/portfolio-models"

CSS = """
<style>
/* Genel */
.block-container { padding-top: 2.2rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.01em; }
h3 { font-weight: 650; }

/* Metrikler kart görünümünde */
[data-testid="stMetric"] {
  background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
  padding: 14px 16px 10px; box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
[data-testid="stMetricLabel"] p { color: #64748B; font-size: .82rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .04em; }
[data-testid="stMetricValue"] { font-weight: 700; }

/* Sekmeler */
.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { padding: .55rem .9rem; border-radius: 10px 10px 0 0; font-weight: 600; }

/* Açılır kutular ve kenarlıklı kaplar */
[data-testid="stExpander"] details { border-radius: 12px; border-color: #E2E8F0; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }

/* Sayfa başı şeridi */
.pm-hero {
  border-radius: 18px; padding: 22px 26px; margin: 0 0 18px 0; color: #fff;
  background: radial-gradient(1200px 300px at 0% 0%, #6366F1 0%, #4F46E5 45%, #3730A3 100%);
  box-shadow: 0 10px 30px rgba(79, 70, 229, .18);
}
.pm-hero h1 { color: #fff; font-size: 1.9rem; margin: 0 0 .25rem 0; padding: 0; }
.pm-hero p { margin: 0; opacity: .92; font-size: 1rem; }
.pm-hero .pm-chips { margin-top: .75rem; display: flex; flex-wrap: wrap; gap: .4rem; }
.pm-hero .pm-chip { background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .25);
  padding: .2rem .6rem; border-radius: 999px; font-size: .78rem; }
.pm-hero a { color: #fff; text-decoration: underline; }

/* Alt bilgi */
.pm-footer { color: #94A3B8; font-size: .8rem; margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid #E2E8F0; }
.pm-footer a { color: #64748B; }
</style>
"""


def setup() -> None:
    """Her çalıştırmanın başında: stil ve grafik teması."""
    register_template()
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, chips: list[str] | None = None) -> None:
    chips_html = "".join(f'<span class="pm-chip">{c}</span>' for c in (chips or []))
    st.markdown(
        f'<div class="pm-hero"><h1>{title}</h1><p>{subtitle}</p>'
        + (f'<div class="pm-chips">{chips_html}</div>' if chips_html else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def footer() -> None:
    lang = get_lang()
    st.markdown(
        f'<div class="pm-footer">⭐ <a href="{REPO}" target="_blank">GitHub</a> · '
        f'<a href="{REPO}#-self-hosting" target="_blank">{t("Kendi sunucunuza kurun")}</a> · '
        f'<a href="?page=privacy&lang={lang}">{t("Gizlilik")}</a> · '
        f'<a href="?page=terms&lang={lang}">{t("Koşullar")}</a> · '
        f'{t("Eğitim amaçlıdır, yatırım tavsiyesi değildir.")} · MIT</div>',
        unsafe_allow_html=True,
    )
