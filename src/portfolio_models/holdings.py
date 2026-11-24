"""Gerçek portföy takibi: pozisyonlar, işlem geçmişi, TL değerleme, kâr/zarar ve yeniden dengeleme.

Hesaplama fonksiyonları internetten bağımsızdır; piyasa verisi `fetch_market_data` ile ayrıca
indirilir. Böylece hepsi test edilebilir.

Kavramlar
- Pozisyon satırı: "şu an elimde X adet var" (tarihsiz; tüm dönem boyunca elde tutulmuş sayılır).
- İşlem: tarihli alım/satım. Miktar ve ortalama maliyet işlemlerden hesaplanır.
- Aynı varlık iki yerde de varsa miktarlar toplanır.
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
KIND_FUND = "TEFAS fonu"
KINDS = [KIND_BIST, KIND_FUND, KIND_YAHOO, KIND_GOLD, KIND_CASH]
TXN_KINDS = [KIND_BIST, KIND_FUND, KIND_YAHOO, KIND_GOLD]

COLUMNS = ["Tür", "Sembol", "Miktar", "Ort. maliyet", "Güncel fiyat"]
TXN_COLUMNS = ["Tarih", "İşlem", "Tür", "Sembol", "Adet", "Fiyat", "Tutar"]
SIDE_BUY, SIDE_SELL, SIDE_DIV, SIDE_DEP, SIDE_WD = "Al", "Sat", "Temettü", "Para yatır", "Para çek"
SIDES = [SIDE_BUY, SIDE_SELL, SIDE_DIV, SIDE_DEP, SIDE_WD]
CASH_SIDES = {SIDE_DEP, SIDE_WD}


@dataclass(frozen=True)
class Position:
    kind: str
    label: str  # tabloda görünen ad
    ticker: str | None  # Yahoo sembolü (altın, fon ve nakitte None)
    quantity: float
    cost: float | None  # birim maliyet, varlığın kendi para biriminde
    cash_currency: str | None = None
    manual_price: float | None = None  # TEFAS fonu: kullanıcının girdiği güncel birim fiyat (TL)
    has_history: bool = False  # TEFAS fonu: fiyat geçmişi (dosya/elle) var mı

    @property
    def is_cash(self) -> bool:
        return self.kind == KIND_CASH

    @property
    def is_fixed(self) -> bool:
        """Fiyat geçmişi olmayan varlık (nakit, geçmişsiz TEFAS fonu); yeniden dengelemeye katılmaz."""
        return self.is_cash or (self.kind == KIND_FUND and not self.has_history)


def fx_ticker(currency: str) -> str:
    return f"{currency.upper()}TRY=X"


def asset_label(kind: str, symbol: str | None) -> str | None:
    """Tür + sembolden tabloda kullanılan tekil ad. Geçersizse None."""
    s = str(symbol or "").strip().upper()
    if kind == KIND_BIST:
        return s.removesuffix(".IS") or None
    if kind in (KIND_YAHOO, KIND_FUND):
        return s or None
    if kind == KIND_GOLD:
        return "Gram altın"
    if kind == KIND_CASH:
        cur = s or "TRY"
        return f"Nakit {cur}" if len(cur) == 3 and cur.isalpha() else None
    return None


def make_position(kind: str, symbol: str | None, qty: float, cost: float | None = None,
                  manual_price: float | None = None, has_history: bool = False) -> Position:
    """Doğrulama yapmadan pozisyon nesnesi oluşturur (sembolün geçerli olduğu varsayılır)."""
    label = asset_label(kind, symbol)
    if kind == KIND_BIST:
        return Position(kind, label, f"{label}.IS", qty, cost)
    if kind == KIND_YAHOO:
        return Position(kind, label, label, qty, cost)
    if kind == KIND_GOLD:
        return Position(kind, label, None, qty, cost)
    if kind == KIND_FUND:
        return Position(kind, label, None, qty, cost, manual_price=manual_price, has_history=has_history)
    if kind == KIND_CASH:
        return Position(kind, label, None, qty, None, cash_currency=label.split()[-1])
    raise ValueError(f"Bilinmeyen tür: {kind}")


def _float_or_none(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f > 0 else None


def parse_positions(rows: list[dict], funds_with_history: set[str] | frozenset = frozenset(),
                    funds_with_price: set[str] | frozenset = frozenset()) -> tuple[list[Position], list[str]]:
    """Pozisyon tablosu satırlarını doğrular. Geçersiz satırlar için uyarı listesi döner.

    funds_with_history: fiyat geçmişi (dosya/elle) olan fonlar — yeniden dengelemeye katılır.
    funds_with_price: herhangi bir fiyat kaynağı olan fonlar (geçmiş ya da işlem fiyatı).
    """
    positions: list[Position] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        kind = row.get("Tür")
        symbol = str(row.get("Sembol") or "").strip().upper()
        qty = row.get("Miktar")
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
        if kind not in KINDS:
            warnings.append(f"Satır {i}: tür seçin.")
            continue
        label = asset_label(kind, symbol)
        if label is None:
            if kind == KIND_CASH:
                warnings.append(f"Satır {i}: nakit için para birimi kodu yazın (TRY, USD, EUR…).")
            elif kind == KIND_FUND:
                warnings.append(f"Satır {i}: TEFAS fon kodunu yazın (ör. TTE, AFT).")
            else:
                warnings.append(f"Satır {i}: sembol boş.")
            continue
        cost = _float_or_none(row.get("Ort. maliyet")) if kind != KIND_CASH else None
        manual = _float_or_none(row.get("Güncel fiyat")) if kind == KIND_FUND else None
        has_hist = kind == KIND_FUND and label in funds_with_history
        if kind == KIND_FUND and manual is None and not has_hist and label not in funds_with_price:
            warnings.append(
                f"Satır {i}: {label} için fiyat yok. 'Güncel fiyat' sütununa birim fiyatı yazın "
                "ya da Fon fiyatları sekmesinden fiyat geçmişi yükleyin."
            )
            continue
        if label in seen:
            warnings.append(f"Satır {i}: {label} birden fazla kez girilmiş; miktarları tek satırda toplayın.")
            continue
        seen.add(label)
        positions.append(make_position(kind, symbol, qty, cost, manual, has_hist))
    return positions, warnings


# --- İşlem geçmişi -------------------------------------------------------------


@dataclass(frozen=True)
class Trade:
    date: pd.Timestamp
    side: str  # Al / Sat / Temettü / Para yatır / Para çek
    kind: str
    label: str
    symbol: str
    qty: float  # Al/Sat: adet; diğerlerinde 0
    price: float  # Al/Sat: birim fiyat (varlığın para birimi; gram altın TL/gram)
    amount: float = 0.0  # Temettü / Para yatır / Para çek: toplam tutar (varlığın ya da nakdin para birimi)

    @property
    def is_trade(self) -> bool:
        return self.side in (SIDE_BUY, SIDE_SELL)

    @property
    def gross(self) -> float:
        """İşlemin toplam tutarı, kendi para biriminde."""
        return self.qty * self.price if self.is_trade else self.amount


def _blank(v) -> bool:
    return v is None or v == "" or (isinstance(v, float) and math.isnan(v))


def parse_trades(rows: list[dict], today: date | None = None) -> tuple[list[Trade], list[str]]:
    today = today or date.today()
    trades: list[Trade] = []
    warnings: list[str] = []
    for i, row in enumerate(rows, start=1):
        d, side, kind = row.get("Tarih"), row.get("İşlem"), row.get("Tür")
        symbol = str(row.get("Sembol") or "").strip().upper()
        if all(_blank(row.get(c)) for c in TXN_COLUMNS):
            continue
        try:
            ts = pd.Timestamp(d).normalize()
            if pd.isna(ts):
                raise ValueError
        except (TypeError, ValueError):
            warnings.append(f"İşlem {i}: tarih geçersiz.")
            continue
        if ts.date() > today:
            warnings.append(f"İşlem {i}: ileri tarihli işlem atlandı.")
            continue
        if side not in SIDES:
            warnings.append(f"İşlem {i}: işlem türünü seçin ({', '.join(SIDES)}).")
            continue
        qty, price, total = (_float_or_none(row.get("Adet")), _float_or_none(row.get("Fiyat")),
                             _float_or_none(row.get("Tutar")))

        if side in CASH_SIDES:  # para yatırma / çekme: Tür = Nakit, Sembol = para birimi
            cur = symbol if kind == KIND_CASH and symbol else ("TRY" if kind in (None, "", KIND_CASH) else None)
            label = asset_label(KIND_CASH, cur) if cur else None
            if label is None:
                warnings.append(f"İşlem {i}: para yatırma/çekme için Tür 'Nakit', Sembol para birimi (TRY, USD…) olmalı.")
                continue
            amount = total or (qty * price if qty and price else None)
            if amount is None:
                warnings.append(f"İşlem {i}: tutarı 'Tutar' sütununa yazın.")
                continue
            trades.append(Trade(ts, side, KIND_CASH, label, label.split()[-1], 0.0, 0.0, amount))
            continue

        if kind not in TXN_KINDS:
            warnings.append(f"İşlem {i}: tür seçin." + (" Nakit yalnızca para yatırma/çekmede kullanılır."
                                                         if kind == KIND_CASH else ""))
            continue
        label = asset_label(kind, symbol)
        if label is None:
            warnings.append(f"İşlem {i}: sembol boş.")
            continue
        if side == SIDE_DIV:
            # Temettü: 'Tutar' (net toplam) ya da Adet × Fiyat (pay adedi × hisse başı net temettü)
            amount = total or (qty * price if qty and price else None)
            if amount is None:
                warnings.append(f"İşlem {i}: temettü için 'Tutar' ya da adet ve hisse başı temettü girin.")
                continue
            trades.append(Trade(ts, side, kind, label, symbol, 0.0, 0.0, amount))
            continue
        if qty is None or price is None:
            if qty is not None and total:  # adet + toplam tutar verilmişse birim fiyatı çıkar
                price = total / qty
            else:
                warnings.append(f"İşlem {i}: adet ve fiyat sıfırdan büyük olmalı.")
                continue
        trades.append(Trade(ts, side, kind, label, symbol, qty, price, qty * price))
    order = {SIDE_DEP: 0, SIDE_BUY: 1, SIDE_DIV: 2, SIDE_SELL: 3, SIDE_WD: 4}
    trades.sort(key=lambda t: (t.date, order[t.side]))  # aynı gün: önce para yatırma ve alımlar
    return trades, warnings


@dataclass
class TradeSummary:
    kind: str
    symbol: str
    qty: float = 0.0
    cost_total: float = 0.0  # kalan pozisyonun toplam maliyeti (varlığın para birimi)
    realized: float = 0.0  # gerçekleşen K/Z (varlığın para birimi)
    dividends: float = 0.0  # alınan temettü toplamı (varlığın para birimi)
    first_date: pd.Timestamp | None = None

    @property
    def avg_cost(self) -> float | None:
        return self.cost_total / self.qty if self.qty > 1e-12 else None


def aggregate_trades(trades: list[Trade]) -> tuple[dict[str, TradeSummary], list[str]]:
    """Ortalama maliyet yöntemiyle her varlığın kalan miktarı, maliyeti, gerçekleşen K/Z'si ve temettüsü."""
    out: dict[str, TradeSummary] = {}
    warnings: list[str] = []
    for t in trades:
        if t.side in CASH_SIDES:
            continue
        s = out.setdefault(t.label, TradeSummary(t.kind, t.symbol, first_date=t.date))
        if t.side == SIDE_DIV:
            s.dividends += t.amount
        elif t.side == SIDE_BUY:
            s.qty += t.qty
            s.cost_total += t.qty * t.price
        else:
            q = t.qty
            if q > s.qty + 1e-9:
                warnings.append(
                    f"{t.label}: {t.date:%d.%m.%Y} tarihinde elde {s.qty:g} adet varken {q:g} adet satış girilmiş; "
                    "fazlası yok sayıldı."
                )
                q = s.qty
            avg = s.avg_cost or 0.0
            s.realized += (t.price - avg) * q
            s.cost_total -= avg * q
            s.qty -= q
            if s.qty < 1e-9:
                s.qty, s.cost_total = 0.0, 0.0
    return out, warnings


def cash_tracking(trades: list[Trade]) -> bool:
    """Para yatırma/çekme girildiyse nakit hesabı işlemlerden türetilir."""
    return any(t.side in CASH_SIDES for t in trades)


def trade_currency(t: Trade, currencies: dict[str, str]) -> tuple[str, float]:
    """İşlem tutarının para birimi ve o birime çevirme çarpanı (GBp -> GBP için 0,01)."""
    if t.kind == KIND_CASH:
        return t.symbol, 1.0
    if t.kind in (KIND_BIST, KIND_GOLD, KIND_FUND):
        return "TRY", 1.0
    cur = currencies.get(make_position(t.kind, t.symbol, 1).ticker, "USD")
    return ("GBP", 0.01) if cur == "GBp" else (cur, 1.0)


def cash_movements(trades: list[Trade], currencies: dict[str, str]) -> list[tuple[pd.Timestamp, str, float]]:
    """Nakit hesabındaki değişimler: (tarih, 'Nakit XXX', tutar). Alım düşer; satış, temettü, yatırma ekler."""
    out = []
    for t in trades:
        cur, f = trade_currency(t, currencies)
        sign = {SIDE_BUY: -1, SIDE_SELL: 1, SIDE_DIV: 1, SIDE_DEP: 1, SIDE_WD: -1}[t.side]
        out.append((t.date, f"Nakit {cur}", sign * t.gross * f))
    return out


def cash_balances(trades: list[Trade], currencies: dict[str, str]) -> dict[str, float]:
    bal: dict[str, float] = {}
    for _, label, delta in cash_movements(trades, currencies):
        bal[label] = bal.get(label, 0.0) + delta
    return bal


def merge_rows_with_trades(rows: list[dict], summary: dict[str, TradeSummary],
                           cash: dict[str, float] | None = None) -> list[dict]:
    """Pozisyon satırlarına işlemlerden gelen miktarları (ve nakit takibi açıksa nakit bakiyelerini) ekler."""
    merged: list[dict] = []
    used: set[str] = set()
    cash = dict(cash or {})
    for r in rows:
        r = dict(r)
        label = asset_label(r.get("Tür"), r.get("Sembol")) if r.get("Tür") else None
        if label in cash and r.get("Tür") == KIND_CASH:
            try:
                manual = float(r.get("Miktar") or 0)
            except (TypeError, ValueError):
                manual = 0.0
            r["Miktar"] = manual + max(cash.pop(label), 0.0)
            merged.append(r)
            continue
        s = summary.get(label) if label else None
        if s and s.kind == r.get("Tür") and s.qty > 0:
            used.add(label)
            try:
                manual_qty = float(r.get("Miktar") or 0)
            except (TypeError, ValueError):
                manual_qty = 0.0
            manual_cost = _float_or_none(r.get("Ort. maliyet"))
            total = manual_qty + s.qty
            if manual_qty > 0 and manual_cost is None:
                cost = None  # elle girilen kısmın maliyeti bilinmiyor
            else:
                cost = ((manual_cost or 0) * manual_qty + s.cost_total) / total if total else None
            r["Miktar"], r["Ort. maliyet"] = total, cost
        merged.append(r)
    for label, s in summary.items():
        if label in used or s.qty <= 0:
            continue
        merged.append({"Tür": s.kind, "Sembol": s.symbol, "Miktar": s.qty, "Ort. maliyet": s.avg_cost,
                       "Güncel fiyat": None})
    for label, amount in cash.items():
        if amount > 0.005:
            merged.append({"Tür": KIND_CASH, "Sembol": label.split()[-1], "Miktar": amount, "Ort. maliyet": None,
                           "Güncel fiyat": None})
    return merged


def quantity_timeline(base: dict[str, float], trades: list[Trade], index: pd.DatetimeIndex,
                      cash: list[tuple[pd.Timestamp, str, float]] | None = None) -> pd.DataFrame:
    """Her gün elde tutulan miktar. `base`: tarihsiz pozisyon satırları (tüm dönemde elde).
    `cash`: nakit takibi açıksa nakit hesabı hareketleri."""
    moves = [(t.date, t.label, t.qty if t.side == SIDE_BUY else -t.qty) for t in trades if t.is_trade]
    moves += list(cash or [])
    labels = list(dict.fromkeys(list(base) + [m[1] for m in moves]))
    q = pd.DataFrame(0.0, index=index, columns=labels)
    for label, v in base.items():
        q[label] += v
    for when, label, delta in moves:
        pos = index.searchsorted(when)  # işlem gününe ya da sonraki ilk fiyat gününe
        if pos < len(index):
            q.iloc[pos:, q.columns.get_loc(label)] += delta
    return q.clip(lower=0)


def value_series(qty: pd.DataFrame, try_prices: pd.DataFrame) -> pd.Series:
    """Gün gün portföy değeri; elde tutulan bir varlığın o gün fiyatı yoksa o gün atlanır."""
    cols = [c for c in qty.columns if c in try_prices.columns]
    prices = try_prices[cols].reindex(qty.index).ffill()
    q = qty[cols]
    held = q > 1e-12
    missing = (prices.isna() & held).any(axis=1)
    v = (prices.fillna(0) * q).sum(axis=1)
    return v[~missing & held.any(axis=1)]


def _fx_at(cur: str, when: pd.Timestamp, closes: pd.DataFrame) -> float:
    if cur == "TRY":
        return 1.0
    col = fx_ticker(cur)
    if col not in closes or closes[col].dropna().empty:
        return float("nan")
    s = closes[col].dropna()
    before = s[s.index <= when]
    return float(before.iloc[-1]) if len(before) else float(s.iloc[0])


def fx_factor_at(kind: str, ticker: str | None, when: pd.Timestamp, closes: pd.DataFrame,
                 currencies: dict[str, str]) -> float:
    """İşlem fiyatını (varlığın para birimi) TL'ye çeviren kur, işlem tarihindeki değeriyle."""
    if kind in (KIND_BIST, KIND_GOLD, KIND_FUND) or not ticker:
        return 1.0
    cur = currencies.get(ticker, "USD")
    factor = 1.0
    if cur == "GBp":
        cur, factor = "GBP", 0.01
    return _fx_at(cur, when, closes) * factor


def trade_cashflows(trades: list[Trade], closes: pd.DataFrame, currencies: dict[str, str]) -> pd.DataFrame:
    """Portföyün dışarıyla TL nakit akışları (işlem günü kuruyla); para portföye girerse negatif.

    Nakit takibi kapalıysa: alım negatif; satış ve temettü pozitif (para size döner).
    Nakit takibi açıksa: yalnızca para yatırma (negatif) ve çekme (pozitif); alım-satım ve temettü
    portföyün içinde kalır.
    """
    tracking = cash_tracking(trades)
    rows = []
    for t in trades:
        if tracking and t.side not in CASH_SIDES:
            continue
        cur, f = trade_currency(t, currencies)
        tl = t.gross * f * _fx_at(cur, t.date, closes)
        sign = {SIDE_BUY: -1, SIDE_DEP: -1, SIDE_SELL: 1, SIDE_DIV: 1, SIDE_WD: 1}[t.side]
        rows.append({"date": t.date, "label": t.label, "amount": sign * tl})
    return pd.DataFrame(rows, columns=["date", "label", "amount"])


def dividends_tl(trades: list[Trade], closes: pd.DataFrame, currencies: dict[str, str]) -> float:
    total = 0.0
    for t in trades:
        if t.side == SIDE_DIV:
            cur, f = trade_currency(t, currencies)
            total += t.amount * f * _fx_at(cur, t.date, closes)
    return total


def invested_series(flows: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Kümülatif net yatırılan tutar (portföye giren - çıkan para), TL."""
    if flows.empty:
        return pd.Series(0.0, index=index)
    daily = (-flows.set_index("date")["amount"]).groupby(level=0).sum()
    pos = index.searchsorted(daily.index)
    s = pd.Series(0.0, index=index)
    for p, v in zip(pos, daily.values):
        if p < len(index):
            s.iloc[p] += v
    return s.cumsum()


def xirr(flows: list[tuple[pd.Timestamp, float]]) -> float | None:
    """Yıllıklandırılmış iç verim oranı (XIRR). Hesaplanamazsa None."""
    flows = [(pd.Timestamp(d), float(a)) for d, a in flows if a]
    if len(flows) < 2 or not (any(a < 0 for _, a in flows) and any(a > 0 for _, a in flows)):
        return None
    t0 = min(d for d, _ in flows)
    years = np.array([(d - t0).days / 365.0 for d, _ in flows])
    amounts = np.array([a for _, a in flows])
    if years.max() < 1 / 365:
        return None

    def npv(r: float) -> float:
        return float(np.sum(amounts / (1 + r) ** years))

    from scipy.optimize import brentq

    lo, hi = -0.9999, 1.0
    try:
        while npv(lo) * npv(hi) > 0 and hi < 1e9:  # çok kısa dönemlerde oran çok büyük olabilir
            hi *= 10
        if npv(lo) * npv(hi) > 0:
            return None
        return float(brentq(npv, lo, hi, maxiter=1000))
    except (ValueError, OverflowError, ZeroDivisionError, FloatingPointError):
        return None


# --- Piyasa verisi ---------------------------------------------------------------


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


def _fund_series(p: Position, fund_history: dict[str, pd.Series] | None) -> pd.Series:
    s = fund_history.get(p.label, pd.Series(dtype=float)) if fund_history else pd.Series(dtype=float)
    s = s.copy()
    if p.manual_price:
        today = pd.Timestamp(date.today())
        if s.empty or today >= s.index.max():
            s.loc[today] = p.manual_price  # elle girilen güncel fiyat, bugünün fiyatı sayılır
    return s.sort_index()


def try_price_history(
    positions: list[Position],
    closes: pd.DataFrame,
    currencies: dict[str, str],
    fund_history: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    """Her pozisyonun TL cinsinden birim fiyat geçmişi (sütun = pozisyon etiketi)."""
    if closes.empty:  # yalnızca TL nakit / TEFAS fonu varsa piyasa verisi gerekmez
        closes = pd.DataFrame(index=pd.DatetimeIndex([pd.Timestamp(date.today())]))
    out: dict[str, pd.Series] = {}
    for p in positions:
        if p.ticker:
            if p.ticker not in closes or closes[p.ticker].dropna().empty:
                continue
            out[p.label] = closes[p.ticker] * _fx_series(closes, currencies.get(p.ticker, "USD"))
        elif p.kind == KIND_GOLD:
            if GOLD_FUTURES in closes and "USDTRY=X" in closes:
                out[p.label] = closes[GOLD_FUTURES] * closes["USDTRY=X"] / TROY_OUNCE_GRAMS
        elif p.kind == KIND_FUND:
            s = _fund_series(p, fund_history)
            if not s.empty:
                if not p.has_history:  # yalnızca elle güncel fiyat: tüm dönem için sabit kabul
                    s = pd.Series(float(s.iloc[-1]), index=closes.index.union(s.index))
                out[p.label] = s
        elif p.is_cash:
            out[p.label] = (_fx_series(closes, p.cash_currency) if p.cash_currency != "TRY"
                            else pd.Series(1.0, index=closes.index))
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out).sort_index()
    return df.ffill()


def _last_date(p: Position, closes: pd.DataFrame, fund_history: dict[str, pd.Series] | None):
    if p.ticker and p.ticker in closes:
        return closes[p.ticker].last_valid_index()
    if p.kind == KIND_GOLD and GOLD_FUTURES in closes:
        return closes[GOLD_FUTURES].last_valid_index()
    if p.kind == KIND_FUND:
        s = _fund_series(p, fund_history)
        return s.index.max() if not s.empty else None
    return None


def valuation(
    positions: list[Position],
    closes: pd.DataFrame,
    currencies: dict[str, str],
    try_prices: pd.DataFrame | None = None,
    fund_history: dict[str, pd.Series] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Güncel değerleme tablosu. Fiyatı bulunamayan pozisyonlar uyarı listesine yazılır."""
    if try_prices is None:
        try_prices = try_price_history(positions, closes, currencies, fund_history)
    rows, missing = [], []
    for p in positions:
        if p.label not in try_prices or try_prices[p.label].dropna().empty:
            missing.append(p.label)
            continue
        tl = try_prices[p.label].dropna()
        price_try = float(tl.iloc[-1])
        if p.ticker:
            s = closes[p.ticker].dropna()
            last_local, cur = float(s.iloc[-1]), currencies.get(p.ticker, "USD")
            daily = (price_try / float(tl.iloc[-2]) - 1) if len(tl) > 1 else np.nan
        elif p.is_cash:
            last_local, cur, daily = 1.0, p.cash_currency, (price_try / float(tl.iloc[-2]) - 1) if len(tl) > 1 else np.nan
        elif p.kind == KIND_FUND:
            s = _fund_series(p, fund_history)
            last_local, cur = float(s.iloc[-1]), "TRY"
            daily = (float(s.iloc[-1]) / float(s.iloc[-2]) - 1) if p.has_history and len(s) > 1 else np.nan
        else:  # gram altın (TL)
            last_local, cur = price_try, "TRY"
            daily = (price_try / float(tl.iloc[-2]) - 1) if len(tl) > 1 else np.nan
        value = p.quantity * price_try
        cost_value_try = pnl_pct = None
        if p.cost:
            # Maliyet varlığın kendi para biriminde girilir; TL karşılığı bugünkü kurla hesaplanır.
            fx_now = price_try / last_local if last_local else float("nan")
            cost_value_try = p.cost * p.quantity * fx_now
            pnl_pct = last_local / p.cost - 1
        last_d = _last_date(p, closes, fund_history)
        rows.append(
            {
                "Varlık": p.label,
                "Tür": p.kind,
                "Miktar": p.quantity,
                "Son fiyat": last_local,
                "Para birimi": cur,
                "Fiyat tarihi": pd.Timestamp(last_d).date() if last_d is not None else None,
                "Değer (TL)": value,
                "Günlük %": daily,
                "Maliyet (TL)": cost_value_try,
                "K/Z (TL)": value - cost_value_try if cost_value_try is not None else None,
                "K/Z %": pnl_pct,
            }
        )
    table = pd.DataFrame(rows)
    if not table.empty:
        for col in ("Maliyet (TL)", "K/Z (TL)", "K/Z %", "Günlük %"):
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
    fixed: set[str] | None = None,
) -> pd.DataFrame:
    """Hedef ağırlıklara ulaşmak için alım/satım miktarlarını hesaplar.

    target_weights: modele giren varlıklar için (toplam 1). Nakit hedefte 0 kabul edilir ve
    include_cash=True ise yatırıma kullanılır; False ise nakit olduğu gibi kalır.
    whole_units: yalnızca tam adet alınıp satılabilen varlıklar (ör. BIST hisseleri).
    fixed: olduğu gibi bırakılacak varlıklar (varsayılan: nakit ve TEFAS fonları).
    """
    whole_units = whole_units or set()
    values = table.set_index("Varlık")["Değer (TL)"]
    kinds = table.set_index("Varlık")["Tür"]
    is_cash = kinds.eq(KIND_CASH)
    if fixed is None:
        is_fixed = kinds.isin({KIND_CASH, KIND_FUND})
    else:
        is_fixed = values.index.isin(list(fixed)) | is_cash.values
        is_fixed = pd.Series(is_fixed, index=values.index)
    cash_total = values[is_cash].sum()
    investable = values[~is_fixed].sum() + (cash_total if include_cash else 0.0)

    rows = []
    for asset, w in target_weights.items():
        current = float(values.get(asset, 0.0))
        target = investable * float(w)
        price = float(prices_try[asset])
        units = (target - current) / price
        if asset in whole_units:
            # Alımlar aşağı, satışlar yukarı yuvarlanır: öneri hiçbir zaman eksi nakde düşürmez
            units = math.floor(units + 1e-9)
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
    """Yeniden dengeleme modelleri için fiyat geçmişi olan varlıkların TL getirileri."""
    risky = [p.label for p in positions if not p.is_fixed and p.label in try_prices]
    prices = try_prices[risky].dropna()
    return prices.pct_change().dropna().replace([np.inf, -np.inf], np.nan).dropna()
