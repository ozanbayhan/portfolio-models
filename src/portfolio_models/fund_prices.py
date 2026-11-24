"""TEFAS fon fiyat geçmişi: dosyadan (CSV/Excel) okuma, elle girilen fiyatlar ve birleştirme.

Fiyat geçmişi {fon_kodu: {"YYYY-MM-DD": fiyat}} biçiminde saklanır.
"""

from __future__ import annotations

import io
import re
import unicodedata
from datetime import date

import pandas as pd

FundHistory = dict[str, dict[str, float]]

_CODE_KEYS = ("fonkodu", "fonkod", "kod", "code", "fundcode")
_DATE_KEYS = ("tarih", "date")
_PRICE_KEYS = ("fiyat", "birimpaydegeri", "paydegeri", "price", "nav")


def _norm(name: str) -> str:
    """'Fon Kodu' -> 'fonkodu', 'Birim Pay Değeri' -> 'birimpaydegeri'."""
    s = unicodedata.normalize("NFKD", str(name).replace("ı", "i").replace("İ", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def _find(columns: list[str], keys: tuple[str, ...]) -> str | None:
    normed = {c: _norm(c) for c in columns}
    for k in keys:  # önce tam eşleşme
        for c, n in normed.items():
            if n == k:
                return c
    for k in keys:  # sonra içeren
        for c, n in normed.items():
            if k in n:
                return c
    return None


def parse_number(v) -> float:
    """Türkçe ve İngilizce sayı biçimlerini çözer: '1.234,56' '3,775584' '1,234.56' '3.775584'."""
    if v is None:
        return float("nan")
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "").replace("₺", "").replace("TL", "")
    if not s or s in ("-", "—"):
        return float("nan")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:  # 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1:  # 1.234.567
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _parse_dates(col: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(col):
        return pd.to_datetime(col).dt.normalize()
    if pd.api.types.is_numeric_dtype(col):  # epoch ms
        return pd.to_datetime(col, unit="ms", errors="coerce").dt.normalize()
    s = col.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    out = pd.to_datetime(s.where(~iso), dayfirst=True, errors="coerce", format="mixed")
    out = out.fillna(pd.to_datetime(s.where(iso), errors="coerce", format="mixed"))
    return out.dt.normalize()


def _read_table(data: bytes, filename: str) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(io.BytesIO(data), dtype=object)
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Dosyanın karakter kodlaması okunamadı.")
    first = text.splitlines()[0] if text else ""
    sep = ";" if first.count(";") > first.count(",") else ("\t" if "\t" in first else ",")
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=str)


def parse_fund_file(data: bytes, filename: str, default_code: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """TEFAS'tan indirilen (veya benzer) dosyayı [code, date, price] tablosuna çevirir.

    Dosyada fon kodu sütunu yoksa `default_code` kullanılır.
    """
    warnings: list[str] = []
    raw = _read_table(data, filename)
    raw.columns = [str(c).strip() for c in raw.columns]
    date_col = _find(list(raw.columns), _DATE_KEYS)
    price_col = _find(list(raw.columns), _PRICE_KEYS)
    code_col = _find(list(raw.columns), _CODE_KEYS)
    if not date_col or not price_col:
        raise ValueError(
            "Dosyada 'Tarih' ve 'Fiyat' sütunları bulunamadı. Bulunan sütunlar: " + ", ".join(map(str, raw.columns))
        )
    if not code_col and not default_code:
        raise ValueError("Dosyada 'Fon Kodu' sütunu yok; yüklemeden önce fon kodunu seçin.")

    df = pd.DataFrame(
        {
            "code": raw[code_col].astype(str).str.strip().str.upper() if code_col else (default_code or "").upper(),
            "date": _parse_dates(raw[date_col]),
            "price": raw[price_col].map(parse_number),
        }
    )
    bad = df["date"].isna() | df["price"].isna() | (df["price"] <= 0) | (df["code"] == "")
    if bad.any():
        warnings.append(f"{int(bad.sum())} satır okunamadı ve atlandı.")
    df = df[~bad]
    future = df["date"] > pd.Timestamp(date.today())
    if future.any():
        warnings.append(f"{int(future.sum())} satır ileri tarihli olduğu için atlandı.")
        df = df[~future]
    df = df.drop_duplicates(["code", "date"], keep="last").sort_values(["code", "date"])
    return df.reset_index(drop=True), warnings


def merge_history(existing: FundHistory, new: pd.DataFrame) -> FundHistory:
    """Yeni fiyatları mevcut geçmişe ekler (aynı tarih varsa yeni değer geçerli)."""
    out = {code: dict(h) for code, h in existing.items()}
    for code, grp in new.groupby("code"):
        h = out.setdefault(str(code), {})
        for d, p in zip(grp["date"], grp["price"]):
            h[pd.Timestamp(d).strftime("%Y-%m-%d")] = float(p)
    return out


def history_series(history: dict[str, float]) -> pd.Series:
    if not history:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(k): float(v) for k, v in history.items()}).sort_index()
    return s[~s.index.duplicated(keep="last")]


def editor_frame(history: dict[str, float]) -> pd.DataFrame:
    s = history_series(history)
    return pd.DataFrame({"Tarih": [d.date() for d in s.index], "Fiyat": s.values})


def from_editor(df: pd.DataFrame) -> tuple[dict[str, float], list[str]]:
    warnings: list[str] = []
    out: dict[str, float] = {}
    for i, row in df.iterrows():
        d, p = row.get("Tarih"), row.get("Fiyat")
        if d is None or pd.isna(d):
            continue
        p = parse_number(p)
        if not (p > 0):
            warnings.append(f"{d}: fiyat geçersiz, atlandı.")
            continue
        if pd.Timestamp(d) > pd.Timestamp(date.today()):
            warnings.append(f"{d}: ileri tarih, atlandı.")
            continue
        out[pd.Timestamp(d).strftime("%Y-%m-%d")] = float(p)
    return out, warnings
