"""Çok dillilik (Türkçe / English / Deutsch).

Türkçe metin anahtar olarak kullanılır (gettext tarzı):

    t("Toplam değer")                       -> "Total value" (en)
    t("{n} işlem eklendi.", n=3)            -> "3 transactions added." (en)

Çeviri bulunamazsa Türkçe metin gösterilir. Etkin dil, her Streamlit çalıştırmasının başında
`set_lang()` ile ayarlanır; kütüphane kodu (uyarılar, yorumlar) da aynı dili kullanır.
"""

from __future__ import annotations

import contextvars

LANGS = {"tr": "Türkçe", "en": "English", "de": "Deutsch"}
DEFAULT_LANG = "tr"

_lang: contextvars.ContextVar[str | None] = contextvars.ContextVar("lang", default=None)


def set_lang(lang: str) -> None:
    _lang.set(lang if lang in LANGS else DEFAULT_LANG)


def get_lang() -> str:
    lang = _lang.get()
    if lang is not None:
        return lang
    # Streamlit buton geri çağrıları sayfa betiğinden önce çalışır; o anda dil henüz ayarlanmamıştır.
    # Bu durumda oturumda seçili dili kullan.
    try:
        import streamlit as st

        lang = st.session_state.get("lang")
    except Exception:  # noqa: BLE001 - Streamlit dışında (testler, CLI, e-posta)
        lang = None
    return lang if lang in LANGS else DEFAULT_LANG


def t(text: str, /, **kwargs) -> str:
    """Metni etkin dile çevirir; kwargs varsa şablonu doldurur."""
    lang = get_lang()
    if lang != DEFAULT_LANG:
        from .locales import CATALOG

        text = CATALOG.get(text, {}).get(lang, text)
    return text.format(**kwargs) if kwargs else text


def num_sep() -> tuple[str, str]:
    """(ondalık, binlik) ayırıcı: Türkçe/Almanca '1.234,5', İngilizce '1,234.5'."""
    return (".", ",") if get_lang() == "en" else (",", ".")
