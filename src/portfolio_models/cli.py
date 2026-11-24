"""Komut satırı: portfolio-models list | weights | backtest"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .backtest import backtest, fit_weights, summarize
from .data import bist, load_csv, load_prices, to_returns
from .models import list_models


def _load(args) -> pd.DataFrame:
    if args.csv:
        prices = load_csv(args.csv)
    else:
        tickers = list(args.tickers or [])
        if args.bist:
            tickers += bist(*args.bist)
        if len(tickers) < 2:
            raise SystemExit("En az 2 sembol verin: --tickers AAPL MSFT veya --bist THYAO ASELS")
        prices = load_prices(tickers, start=args.start, end=args.end)
    print(f"{prices.shape[1]} varlık, {len(prices)} gün ({prices.index[0]:%Y-%m-%d} → {prices.index[-1]:%Y-%m-%d})")
    return to_returns(prices)


def _add_data_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tickers", nargs="+", help="Yahoo Finance sembolleri (örn. AAPL MSFT GLD)")
    p.add_argument("--bist", nargs="+", help="BIST sembolleri, .IS eki otomatik (örn. THYAO ASELS)")
    p.add_argument("--csv", help="Kendi fiyat dosyanız: ilk sütun tarih, diğerleri fiyat")
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--models", nargs="+", help="Sadece bu modeller (varsayılan: hepsi)")
    p.add_argument("--out", default="results", help="Çıktı klasörü")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="portfolio-models", description="Portföy modelleri")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Mevcut modelleri listele")

    w = sub.add_parser("weights", help="Güncel veriyle her modelin ağırlıklarını hesapla")
    _add_data_args(w)

    b = sub.add_parser("backtest", help="Walk-forward backtest ile modelleri karşılaştır")
    _add_data_args(b)
    b.add_argument("--train", type=int, default=252, help="Eğitim penceresi (gün)")
    b.add_argument("--test", type=int, default=21, help="Yeniden dengeleme aralığı (gün)")

    args = parser.parse_args(argv)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)

    if args.cmd == "list":
        for name, desc in list_models():
            print(f"{name:28s} {desc}")
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    returns = _load(args)

    if args.cmd == "weights":
        weights = fit_weights(returns, args.models)
        print((weights * 100).round(1).to_string())
        weights.to_csv(out / "weights.csv")
        print(f"\nKaydedildi: {out / 'weights.csv'}")

    elif args.cmd == "backtest":
        population = backtest(returns, args.models, train_size=args.train, test_size=args.test)
        table = summarize(population)
        print(table.round(3).to_string())
        table.to_csv(out / "backtest_summary.csv")
        fig = population.plot_cumulative_returns()
        fig.write_html(out / "cumulative_returns.html")
        print(f"\nKaydedildi: {out / 'backtest_summary.csv'}, {out / 'cumulative_returns.html'}")


if __name__ == "__main__":
    main()
