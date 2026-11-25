"""Çeviri kataloğu eksiksiz ve tutarlı mı?"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from i18n_keys import all_keys  # noqa: E402

from portfolio_models.i18n import set_lang, t  # noqa: E402
from portfolio_models.locales import CATALOG  # noqa: E402

PLACEHOLDER = re.compile(r"{(\w*)}")


def test_every_key_translated():
    missing = sorted(k for k in all_keys() if not all(CATALOG.get(k, {}).get(lang) for lang in ("en", "de")))
    assert missing == [], f"Çevirisi eksik metinler: {missing[:10]}"


@pytest.mark.parametrize("key", sorted(CATALOG))
def test_placeholders_match(key):
    want = sorted(PLACEHOLDER.findall(key))
    for lang in ("en", "de"):
        assert sorted(PLACEHOLDER.findall(CATALOG[key][lang])) == want, (key, lang)


def test_switching():
    try:
        set_lang("de")
        assert t("{n} işlem eklendi.", n=3) == "3 Transaktionen hinzugefügt."
        set_lang("en")
        assert t("Toplam değer") == "Total value"
        assert t("katalogda olmayan metin") == "katalogda olmayan metin"  # Türkçeye geri düşer
    finally:
        set_lang("tr")
    assert t("Toplam değer") == "Toplam değer"
