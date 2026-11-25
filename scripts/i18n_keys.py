"""Çevrilecek tüm metinleri toplar (t()/T() çağrıları + dinamik çevrilen değerler).

Kullanım: .venv/bin/python scripts/i18n_keys.py            -> eksik çevirileri listeler
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

FILES = sorted((ROOT / "src" / "portfolio_models").rglob("*.py"))


def literal_keys() -> set[str]:
    keys: set[str] = set()
    for f in FILES:
        if f.name in ("locales.py",):
            continue
        for node in ast.walk(ast.parse(f.read_text())):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("t", "T")
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                keys.add(node.args[0].value)
    return keys


def dynamic_keys() -> set[str]:
    import importlib

    backtest = importlib.import_module("portfolio_models.backtest")
    holdings = importlib.import_module("portfolio_models.holdings")
    models = importlib.import_module("portfolio_models.models")

    keys = set(holdings.KINDS) | set(holdings.SIDES)
    keys |= {desc for _, desc in models.MODELS.values()}
    keys |= set(backtest.SUMMARY_ROWS.values())
    keys |= {"1 ay", "3 ay", "6 ay", "1 yıl", "Yılbaşından", "Tümü"}
    keys |= {"Yahoo Finance", "CSV dosyası", "Mutlak", "Göreli"}
    keys |= {"Portföyüm", "BIST100", "Dolar (USD/TRY)", "Gram altın", "Enflasyon (TÜFE)"}
    keys |= {"Seri", "Toplam getiri", "Yıllık", "Reel (TÜFE'ye göre)", "Başlangıç", "Bitiş"}
    keys |= {"Varlık", "Tür", "Miktar", "Son fiyat", "Para birimi", "Fiyat tarihi", "Değer (TL)", "Günlük %",
             "Maliyet (TL)", "K/Z (TL)", "K/Z %", "Ağırlık"}
    keys |= {"Mevcut (TL)", "Mevcut ağırlık", "Hedef ağırlık", "Hedef (TL)", "İşlem", "Adet", "Tutar (TL)"}
    keys |= {"Tarih", "İşlem (Al/Sat)", "Adet", "Fiyat"}
    keys -= {"BIST100"}
    return keys


def all_keys() -> set[str]:
    return literal_keys() | dynamic_keys()


if __name__ == "__main__":
    from portfolio_models.locales import CATALOG

    missing = sorted(k for k in all_keys() if k not in CATALOG or not all(CATALOG[k].get(l) for l in ("en", "de")))
    print(f"{len(all_keys())} anahtar, eksik: {len(missing)}")
    for k in missing:
        print(repr(k))
