"""İşlem geçmişini CSV/Excel'den içe aktarma ve dışa aktarma.

Aracı kurum ekstreleri farklı sütun adları kullanır; okuyucu yaygın adları tanır:
    Tarih   : tarih, işlem tarihi, date
    İşlem   : işlem, işlem tipi, tip, yön, al/sat, side, type  (Alış/Al/A/Buy/B — Satış/Sat/S/Sell)
    Sembol  : sembol, hisse, menkul, kod, fon kodu, symbol, ticker
    Adet    : adet, miktar, lot, nominal, quantity
    Fiyat   : fiyat, birim fiyat, ortalama fiyat, price
    Tür     : tür, varlık türü (isteğe bağlı; yoksa kullanıcının seçtiği varsayılan tür)
"""

from __future__ import annotations

import io

import pandas as pd

from .fund_prices import _find, _norm, _parse_dates, _read_table, parse_number
from .holdings import (
    CASH_SIDES,
    KIND_BIST,
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    SIDE_BUY,
    SIDE_DEP,
    SIDE_DIV,
    SIDE_SELL,
    SIDE_WD,
    TXN_COLUMNS,
    TXN_KINDS,
)

_DATE_KEYS = ("tarih", "islemtarihi", "date", "tradedate", "valor")
_SIDE_KEYS = ("islem", "islemtipi", "islemturu", "tip", "yon", "alsat", "side", "type", "buysell")
_SYMBOL_KEYS = ("sembol", "hisse", "menkul", "menkulkiymet", "kod", "fonkodu", "symbol", "ticker", "varlik")
_QTY_KEYS = ("adet", "miktar", "lot", "nominal", "quantity", "qty", "pay")
_PRICE_KEYS = ("fiyat", "birimfiyat", "ortalamafiyat", "islemfiyati", "price", "unitprice")
_KIND_KEYS = ("tur", "varlikturu", "kind", "assettype")
_AMOUNT_KEYS = ("tutar", "nettutar", "toplamtutar", "amount", "netamount", "total")

_BUY = {"al", "alis", "alim", "a", "buy", "b", "long"}
_SELL = {"sat", "satis", "satim", "s", "sell", "short"}
_DIV = {"temettu", "temettugeliri", "karpayi", "dividend", "div", "kupon"}
_DEP = {"parayatir", "parayatirma", "yatirma", "yatir", "deposit", "virmangiris", "nakitgiris"}
_WD = {"paracek", "paracekme", "cekme", "cek", "withdraw", "withdrawal", "virmancikis", "nakitcikis"}
_KIND_ALIASES = {
    "bist": KIND_BIST, "bisthissesi": KIND_BIST, "hisse": KIND_BIST, "hissesenedi": KIND_BIST,
    "tefas": KIND_FUND, "tefasfonu": KIND_FUND, "fon": KIND_FUND, "yatirimfonu": KIND_FUND,
    "yahoo": KIND_YAHOO, "yahoosembolu": KIND_YAHOO, "yurtdisi": KIND_YAHOO, "abd": KIND_YAHOO,
    "kripto": KIND_YAHOO, "etf": KIND_YAHOO,
    "altin": KIND_GOLD, "gramaltin": KIND_GOLD,
    "nakit": KIND_CASH, "cash": KIND_CASH, "doviz": KIND_CASH,
}

TEMPLATE_ROWS = [
    {"Tarih": "15.01.2025", "İşlem": "Al", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 100, "Fiyat": "290,50"},
    {"Tarih": "03.02.2025", "İşlem": "Al", "Tür": KIND_YAHOO, "Sembol": "AAPL", "Adet": 5, "Fiyat": "230"},
    {"Tarih": "01.03.2025", "İşlem": "Al", "Tür": KIND_FUND, "Sembol": "TTE", "Adet": 5000, "Fiyat": "1,80"},
    {"Tarih": "10.04.2025", "İşlem": "Al", "Tür": KIND_GOLD, "Sembol": "", "Adet": 10, "Fiyat": "3650"},
    {"Tarih": "02.03.2026", "İşlem": "Sat", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": 30, "Fiyat": "330"},
    {"Tarih": "05.06.2025", "İşlem": "Temettü", "Tür": KIND_BIST, "Sembol": "THYAO", "Adet": "", "Fiyat": "",
     "Tutar": "850,00"},
    {"Tarih": "10.01.2025", "İşlem": "Para yatır", "Tür": KIND_CASH, "Sembol": "TRY", "Adet": "", "Fiyat": "",
     "Tutar": "100.000"},
]


def template_csv() -> bytes:
    """Excel'de Türkçe açılan, noktalı virgül ayraçlı şablon."""
    return pd.DataFrame(TEMPLATE_ROWS, columns=TXN_COLUMNS).to_csv(sep=";", index=False).encode("utf-8-sig")


def export_csv(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows, columns=TXN_COLUMNS)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce").dt.strftime("%d.%m.%Y")
    for col in ("Adet", "Fiyat", "Tutar"):
        df[col] = df[col].map(lambda v: "" if v is None or pd.isna(v) else f"{float(v):g}".replace(".", ","))
    return df.to_csv(sep=";", index=False).encode("utf-8-sig")


def _side(v) -> str | None:
    n = _norm(v)
    if n in _DIV or n.startswith("temettu") or n.startswith("dividend"):
        return SIDE_DIV
    if n in _DEP or "yatir" in n or n.startswith("deposit"):
        return SIDE_DEP
    if n in _WD or n.startswith("paracek") or n.startswith("withdraw"):
        return SIDE_WD
    if n in _BUY or n.startswith("alis") or n.startswith("buy"):
        return SIDE_BUY
    if n in _SELL or n.startswith("satis") or n.startswith("sell"):
        return SIDE_SELL
    return None


def _kind(v, default: str) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or not str(v).strip():
        return default
    if v in TXN_KINDS:
        return v
    return _KIND_ALIASES.get(_norm(v), default)


def parse_trades_file(data: bytes, filename: str, default_kind: str = KIND_BIST) -> tuple[list[dict], list[str]]:
    """Dosyayı İşlemler tablosu satırlarına (TXN_COLUMNS) çevirir. Okunamayan satırlar uyarı olarak döner."""
    raw = _read_table(data, filename)
    raw.columns = [str(c).strip() for c in raw.columns]
    cols = list(raw.columns)
    date_c, side_c = _find(cols, _DATE_KEYS), _find(cols, _SIDE_KEYS)
    sym_c, qty_c, price_c = _find(cols, _SYMBOL_KEYS), _find(cols, _QTY_KEYS), _find(cols, _PRICE_KEYS)
    amount_c = _find([c for c in cols if c not in (price_c, qty_c)], _AMOUNT_KEYS)
    kind_c = _find([c for c in cols if c not in (side_c,)], _KIND_KEYS)
    missing = [n for n, c in (("Tarih", date_c), ("İşlem (Al/Sat)", side_c)) if c is None]
    if qty_c is None and amount_c is None:
        missing.append("Adet")
    if price_c is None and amount_c is None:
        missing.append("Fiyat")
    if missing:
        raise ValueError(f"Şu sütunlar bulunamadı: {', '.join(missing)}. Bulunan sütunlar: {', '.join(cols)}")

    dates = _parse_dates(raw[date_c])
    rows: list[dict] = []
    warnings: list[str] = []
    def cell(col, i):
        return None if col is None else raw[col].iloc[i]

    for i in range(len(raw)):
        side = _side(raw[side_c].iloc[i])
        kind = _kind(cell(kind_c, i), default_kind)
        sym = "" if sym_c is None or pd.isna(raw[sym_c].iloc[i]) else str(raw[sym_c].iloc[i]).strip().upper()
        qty, price = parse_number(cell(qty_c, i)), parse_number(cell(price_c, i))
        amount = abs(parse_number(cell(amount_c, i)))  # ekstrelerde çıkışlar eksi yazılabilir
        d = dates.iloc[i]
        problems = []
        if pd.isna(d):
            problems.append("tarih")
        if side is None:
            problems.append("işlem yönü")
        elif side in CASH_SIDES:
            kind, sym = KIND_CASH, (sym if len(sym) == 3 and sym.isalpha() else "TRY")
            if not (amount > 0):
                amount = qty if qty > 0 else float("nan")
            if not (amount > 0):
                problems.append("tutar")
        elif side == SIDE_DIV:
            if not (amount > 0) and not (qty > 0 and price > 0):
                problems.append("temettü tutarı")
        else:
            if not (qty > 0):
                problems.append("adet")
            if not (price > 0) and amount > 0 and qty > 0:
                price = amount / qty
            if not (price > 0):
                problems.append("fiyat")
        if side not in CASH_SIDES and kind != KIND_GOLD and not sym:
            problems.append("sembol")
        if problems:
            warnings.append(f"Dosya satırı {i + 2}: {', '.join(problems)} okunamadı, atlandı.")
            continue
        row = {"Tarih": d.strftime("%Y-%m-%d"), "İşlem": side, "Tür": kind, "Sembol": sym,
               "Adet": float(qty) if qty > 0 else None, "Fiyat": float(price) if price > 0 else None}
        if side in (SIDE_DIV, SIDE_DEP, SIDE_WD) and amount > 0:
            row["Tutar"] = float(amount)
        if side in (SIDE_BUY, SIDE_SELL):
            row.pop("Tutar", None)
        rows.append(row)
    return rows, warnings


def merge_trades(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """Yeni işlemleri ekler; birebir aynı işlemleri (aynı gün, yön, sembol, adet, fiyat) tekrar eklemez."""
    def key(r):
        d = pd.to_datetime(r.get("Tarih"), errors="coerce")
        def num(v):
            try:
                return round(float(v or 0), 8)
            except (TypeError, ValueError):
                return 0.0
        return (None if pd.isna(d) else d.date(), r.get("İşlem"), r.get("Tür"),
                str(r.get("Sembol") or "").upper(), num(r.get("Adet")), num(r.get("Fiyat")), num(r.get("Tutar")))

    seen = {key(r) for r in existing}
    out, skipped = list(existing), 0
    for r in new:
        k = key(r)
        if k in seen:
            skipped += 1
            continue
        seen.add(k)
        out.append(r)
    return out, skipped
