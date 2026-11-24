"""Gerçek portföy takibi: pozisyonlar, TL değerleme, kâr/zarar ve yeniden dengeleme.

Hesaplama fonksiyonları (valuation, rebalance, try_price_history) internetten bağımsızdır;
piyasa verisi `fetch_market_data` ile ayrıca indirilir. Böylece hepsi test edilebilir.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

TROY_OUNCE_GRAMS = 31.1034768
GOLD_FUTURES = "GC=F"  # USD / ons

KIND_BIST = "BIST hissesi"
KIND_YAHOO = "Yahoo sembolü"
KIND_GOLD = "Gram altın"
KIND_CASH = "Nakit"
KINDS = [KIND_BIST, KIND_YAHOO, KIND_GOLD, KIND_CASH]

COLUMNS = ["Tür", "Sembol", "Miktar", "Ort. maliyet"]


@dataclass(frozen=True)
class Position:
    kind: str
    label: str  # tabloda görünen ad
    ticker: str | None  # Yahoo sembolü (altın ve nakitte None)
    quantity: float
    cost: float | None  # birim maliyet, varlığın kendi para biriminde
    cash_currency: str | None = None

    @property
    def is_cash(self) -> bool:
        return self.kind == KIND_CASH


def fx_ticker(currency: str) -> str:
    return f"{currency.upper()}TRY=X"


def parse_positions(rows: list[dict]) -> tuple[list[Position], list[str]]:
    """Kullanıcı tablosundaki satırları doğrular. Geçersiz satırlar için uyarı listesi döner."""
    positions: list[Position] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        kind = row.get("Tür")
        symbol = str(row.get("Sembol") or "").strip().upper()
        qty = row.get("Miktar")
        cost = row.get("Ort. maliyet")
        if not kind and not symbol and qty in (None, ""):
            continue  # boş satır
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            warnings.append(f"Satır {i}: miktar sayı olmalı.")
            continue
        if not math.isfinite(qty) or qty <= 0:
            warnings.append(f"Satır {i}: miktar sıfırdan büyük olmalı.")
            continue
        try:
            cost = float(cost) if cost not in (None, "") else None
            if cost is not None and (not math.isfinite(cost) or cost <= 0):
                cost = None
        except (TypeError, ValueError):
            cost = None

        if kind == KIND_BIST:
            if not symbol:
                warnings.append(f"Satır {i}: sembol boş.")
                continue
            base = symbol.removesuffix(".IS")
            pos = Position(kind, base, f"{base}.IS", qty, cost)
        elif kind == KIND_YAHOO:
            if not symbol:
                warnings.append(f"Satır {i}: sembol boş.")
                continue
            pos = Position(kind, symbol, symbol, qty, cost)
        elif kind == KIND_GOLD:
            pos = Position(kind, "Gram altın", None, qty, cost)
        elif kind == KIND_CASH:
            cur = symbol or "TRY"
            if len(cur) != 3 or not cur.isalpha():
                warnings.append(f"Satır {i}: nakit için para birimi kodu yazın (TRY, USD, EUR…).")
                continue
            pos = Position(kind, f"Nakit {cur}", None, qty, None, cash_currency=cur)
        else:
            warnings.append(f"Satır {i}: tür seçin.")
            continue

        if pos.label in seen:
            warnings.append(f"Satır {i}: {pos.label} birden fazla kez girilmiş; miktarları tek satırda toplayın.")
            continue
        seen.add(pos.label)
        positions.append(pos)
    return positions, warnings


def required_tickers(positions: list[Position]) -> list[str]:
    out: list[str] = []
    for p in positions:
        if p.ticker:
            out.append(p.ticker)
        elif p.kind == KIND_GOLD:
            out += [GOLD_FUTURES, "USDTRY=X"]
        elif p.is_cash and p.cash_currency != "TRY":
            out.append(fx_ticker(p.cash_currency))
    return list(dict.fromkeys(out))


def _currency_guess(ticker: str) -> str:
    if ticker.endswith(".IS") or ticker.endswith("TRY=X"):
        return "TRY"
    return "USD"


def fetch_market_data(positions: list[Position], years: int = 3) -> tuple[pd.DataFrame, dict[str, str]]:
    """Gerekli tüm sembollerin ve döviz kurlarının kapanış fiyatlarını indirir.

    Döner: (kapanış fiyatları, {sembol: para birimi}). Fiyatlar sembolün kendi para birimindedir.
    """
    import yfinance as yf

    tickers = required_tickers(positions)
    currencies: dict[str, str] = {}
    for t in tickers:
        if t.endswith("=X"):
            currencies[t] = "TRY" if t.endswith("TRY=X") else _currency_guess(t)
            continue
        try:
            currencies[t] = yf.Ticker(t).fast_info["currency"] or _currency_guess(t)
        except Exception:  # noqa: BLE001
            currencies[t] = _currency_guess(t)

    fx_needed = {fx_ticker(c.upper() if c != "GBp" else "GBP") for c in currencies.values() if c not in ("TRY",)}
    all_tickers = list(dict.fromkeys(tickers + sorted(fx_needed)))
    if not all_tickers:
        return pd.DataFrame(), currencies
    start = date.today() - timedelta(days=365 * years + 10)
    raw = yf.download(all_tickers, start=str(start), auto_adjust=True, progress=False, threads=False)
    closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(all_tickers[0])
    if list(closes.columns) == ["Close"]:
        closes.columns = all_tickers
    closes = closes.sort_index().ffill()
    return closes, currencies


def _fx_series(closes: pd.DataFrame, currency: str) -> pd.Series:
    if currency == "TRY":
        return pd.Series(1.0, index=closes.index)
    factor = 1.0
    if currency == "GBp":  # Londra borsası peni cinsinden fiyatlar
        currency, factor = "GBP", 0.01
    col = fx_ticker(currency)
    if col not in closes:
        raise KeyError(f"{currency}/TRY kuru bulunamadı")
    return closes[col] * factor


def try_price_history(
    positions: list[Position], closes: pd.DataFrame, currencies: dict[str, str]
) -> pd.DataFrame:
    """Her pozisyonun TL cinsinden birim fiyat geçmişi (sütun = pozisyon etiketi)."""
    out: dict[str, pd.Series] = {}
    for p in positions:
        if p.ticker:
            if p.ticker not in closes or closes[p.ticker].dropna().empty:
                continue
            out[p.label] = closes[p.ticker] * _fx_series(closes, currencies.get(p.ticker, "USD"))
        elif p.kind == KIND_GOLD:
            if GOLD_FUTURES in closes and "USDTRY=X" in closes:
                out[p.label] = closes[GOLD_FUTURES] * closes["USDTRY=X"] / TROY_OUNCE_GRAMS
        elif p.is_cash:
            out[p.label] = _fx_series(closes, p.cash_currency) if p.cash_currency != "TRY" else pd.Series(
                1.0, index=closes.index
            )
    return pd.DataFrame(out).ffill()


def _local_last(p: Position, closes: pd.DataFrame, try_prices: pd.DataFrame) -> tuple[float, float, str]:
    """(son fiyat, önceki kapanış, para birimi) — varlığın kendi para biriminde."""
    if p.ticker:
        s = closes[p.ticker].dropna()
        return float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else float("nan"), ""
    s = try_prices[p.label].dropna()
    return float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else float("nan"), "TRY"


def valuation(
    positions: list[Position],
    closes: pd.DataFrame,
    currencies: dict[str, str],
    try_prices: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Güncel değerleme tablosu. Fiyatı bulunamayan pozisyonlar uyarı listesine yazılır."""
    if try_prices is None:
        try_prices = try_price_history(positions, closes, currencies)
    rows, missing = [], []
    for p in positions:
        if p.label not in try_prices or try_prices[p.label].dropna().empty:
            missing.append(p.label)
            continue
        last_local, prev_local, cur = _local_last(p, closes, try_prices)
        cur = cur or currencies.get(p.ticker, "USD")
        if p.is_cash:
            last_local, prev_local, cur = 1.0, 1.0, p.cash_currency
        tl = try_prices[p.label].dropna()
        price_try = float(tl.iloc[-1])
        prev_try = float(tl.iloc[-2]) if len(tl) > 1 else float("nan")
        value = p.quantity * price_try
        cost_value_try = None
        pnl_pct = None
        if p.cost:
            # Maliyet varlığın kendi para biriminde girilir; TL karşılığı bugünkü kurla hesaplanır.
            fx_now = price_try / last_local if last_local else float("nan")
            cost_value_try = p.cost * p.quantity * fx_now
            pnl_pct = last_local / p.cost - 1
        rows.append(
            {
                "Varlık": p.label,
                "Tür": p.kind,
                "Miktar": p.quantity,
                "Son fiyat": last_local,
                "Para birimi": cur,
                "Değer (TL)": value,
                "Günlük %": price_try / prev_try - 1 if prev_try else float("nan"),
                "Maliyet (TL)": cost_value_try,
                "K/Z (TL)": value - cost_value_try if cost_value_try is not None else None,
                "K/Z %": pnl_pct,
            }
        )
    table = pd.DataFrame(rows)
    if not table.empty:
        for col in ("Maliyet (TL)", "K/Z (TL)", "K/Z %"):
            table[col] = pd.to_numeric(table[col], errors="coerce")
        table["Ağırlık"] = table["Değer (TL)"] / table["Değer (TL)"].sum()
    return table, missing


def value_history(positions: list[Position], try_prices: pd.DataFrame, days: int = 365) -> pd.Series:
    """Bugünkü miktarlarla portföyün geçmiş TL değeri."""
    qty = pd.Series({p.label: p.quantity for p in positions})
    cols = [c for c in try_prices.columns if c in qty.index]
    prices = try_prices[cols].dropna()
    prices = prices[prices.index >= prices.index.max() - pd.Timedelta(days=days)]
    return (prices * qty[cols]).sum(axis=1)


def rebalance(
    table: pd.DataFrame,
    target_weights: pd.Series,
    prices_try: pd.Series,
    include_cash: bool = True,
    whole_units: set[str] | None = None,
) -> pd.DataFrame:
    """Hedef ağırlıklara ulaşmak için alım/satım miktarlarını hesaplar.

    target_weights: riskli varlıklar için (toplam 1). Nakit hedefte 0 kabul edilir ve
    include_cash=True ise yatırıma kullanılır; False ise nakit olduğu gibi kalır.
    whole_units: yalnızca tam adet alınıp satılabilen varlıklar (ör. BIST hisseleri).
    """
    whole_units = whole_units or set()
    values = table.set_index("Varlık")["Değer (TL)"]
    is_cash = table.set_index("Varlık")["Tür"].eq(KIND_CASH)
    cash_total = values[is_cash].sum()
    investable = values[~is_cash].sum() + (cash_total if include_cash else 0.0)

    rows = []
    for asset, w in target_weights.items():
        current = float(values.get(asset, 0.0))
        target = investable * float(w)
        diff = target - current
        price = float(prices_try[asset])
        units = diff / price
        if asset in whole_units:
            units = math.floor(units) if units > 0 else -math.floor(-units)
        rows.append(
            {
                "Varlık": asset,
                "Mevcut (TL)": current,
                "Mevcut ağırlık": current / investable if investable else 0.0,
                "Hedef ağırlık": float(w),
                "Hedef (TL)": target,
                "İşlem": "Al" if units > 0 else ("Sat" if units < 0 else "—"),
                "Adet": abs(units),
                "Tutar (TL)": abs(units) * price,
                "_net": units * price,  # + alım, - satım
            }
        )
    out = pd.DataFrame(rows)
    # İşlemler sonrası kalan nakit (tam adet yuvarlaması dahil, gerçek tutarlarla)
    out.attrs["cash_after"] = cash_total - float(out["_net"].sum())
    return out.drop(columns="_net")


def history_returns(try_prices: pd.DataFrame, positions: list[Position]) -> pd.DataFrame:
    """Yeniden dengeleme modelleri için riskli varlıkların TL getirileri."""
    risky = [p.label for p in positions if not p.is_cash and p.label in try_prices]
    prices = try_prices[risky].dropna()
    return prices.pct_change().dropna().replace([np.inf, -np.inf], np.nan).dropna()
