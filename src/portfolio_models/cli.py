"""Komut satırı: portfolio-models list | weights | backtest"""

from __future__ import annotations

import argparse
import os
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


THEME = {
    "theme.primaryColor": "#4F46E5",
    "theme.font": "sans serif",
}


def serve(args) -> None:
    """Streamlit'i paketle gelen web arayüzüyle başlatır."""
    import subprocess
    import sys

    app = Path(__file__).resolve().parent / "web" / "app.py"
    env = dict(os.environ)
    data_dir = Path(args.data_dir).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    env["PM_DATA_DIR"] = str(data_dir)
    if not args.multi_user:
        env.setdefault("PM_LOCAL_MODE", "1")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port),
           "--server.address", args.host, "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    for k, v in THEME.items():
        cmd += [f"--{k}", v]
    print(f"Portföy Modelleri → http://{'localhost' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}")
    print(f"Veri klasörü: {data_dir}" + ("" if args.multi_user else "  (yerel mod: giriş yok, tek kullanıcı)"))
    raise SystemExit(subprocess.call(cmd, env=env))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="portfolio-models", description="Portföy modelleri")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Mevcut modelleri listele")

    sv = sub.add_parser("serve", help="Web arayüzünü başlat (varsayılan: yerel mod, giriş gerektirmez)")
    sv.add_argument("--port", type=int, default=8501)
    sv.add_argument("--host", default="localhost", help="Sunucuda dışarıya açmak için 0.0.0.0")
    sv.add_argument("--data-dir", default=os.environ.get("PM_DATA_DIR", "~/.portfolio-models"),
                    help="Yerel veritabanı klasörü (varsayılan ~/.portfolio-models)")
    sv.add_argument("--multi-user", action="store_true",
                    help="Yerel modu kapat (Google girişi ve veritabanı .streamlit/secrets.toml ya da ortam "
                         "değişkenleriyle ayarlanmalı; bkz. docs/self-hosting.md)")

    rp = sub.add_parser("report", help="Haftalık e-posta özetlerini gönder (cron/zamanlayıcı için)")
    rp.add_argument("--dry-run", action="store_true", help="Göndermeden yalnızca hesapla")
    rp.add_argument("--out", help="E-posta HTML'lerini bu klasöre de yaz")

    mc = sub.add_parser("mcp", help="Yapay zekâ asistanları için MCP sunucusu (Claude, ChatGPT, Cursor …)")
    mc.add_argument("--http", action="store_true", help="stdio yerine Streamable HTTP (http://HOST:PORT/mcp)")
    mc.add_argument("--host", default="127.0.0.1")
    mc.add_argument("--port", type=int, default=8765)
    mc.add_argument("--data-dir", default=None, help="Web arayüzüyle aynı klasör (varsayılan ~/.portfolio-models)")
    mc.add_argument("--read-only", action="store_true", help="Portföyü değiştiren araçları sunma")

    w = sub.add_parser("weights", help="Güncel veriyle her modelin ağırlıklarını hesapla")
    _add_data_args(w)

    b = sub.add_parser("backtest", help="Walk-forward backtest ile modelleri karşılaştır")
    _add_data_args(b)
    b.add_argument("--train", type=int, default=252, help="Eğitim penceresi (gün)")
    b.add_argument("--test", type=int, default=21, help="Yeniden dengeleme aralığı (gün)")

    args = parser.parse_args(argv)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)

    if args.cmd == "serve":
        serve(args)
        return
    if args.cmd == "mcp":
        if args.data_dir:
            os.environ["PM_DATA_DIR"] = str(Path(args.data_dir).expanduser())
        if args.read_only:
            os.environ["PM_MCP_READ_ONLY"] = "1"
        from .mcp_server import run as run_mcp

        run_mcp(http=args.http, host=args.host, port=args.port)
        return
    if args.cmd == "report":
        from .report import main as report_main

        report_main((["--dry-run"] if args.dry_run else []) + (["--out", args.out] if args.out else []))
        return

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
