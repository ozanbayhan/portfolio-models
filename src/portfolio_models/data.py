"""Fiyat verisi yükleme ve getiri hesaplama."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from skfolio.preprocessing import prices_to_returns


def bist(*symbols: str) -> list[str]:
    """BIST sembollerine Yahoo Finance son ekini (.IS) ekler: bist("THYAO") -> ["THYAO.IS"]."""
    return [s if s.upper().endswith(".IS") else f"{s.upper()}.IS" for s in symbols]


def load_prices(
    tickers: list[str],
    start: str = "2019-01-01",
    end: str | None = None,
) -> pd.DataFrame:
    """Yahoo Finance'ten düzeltilmiş kapanış fiyatlarını indirir."""
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False, threads=False)
    prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices.dropna(axis=1, how="all")
    missing = sorted(set(tickers) - set(prices.columns))
    if missing:
        print(f"Uyarı: veri bulunamadı, atlandı: {', '.join(missing)}")
    return clean_prices(prices)


def load_csv(path: str | Path) -> pd.DataFrame:
    """İlk sütunu tarih, diğer sütunları varlık fiyatları olan bir CSV okur."""
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    return clean_prices(prices)


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.sort_index().ffill().dropna()
    if prices.shape[1] < 2:
        raise ValueError("Portföy için en az 2 varlık gerekli.")
    return prices


def to_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Fiyatlardan doğrusal (lineer) günlük getirilere geçer."""
    return prices_to_returns(prices)
