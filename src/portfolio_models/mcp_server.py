"""MCP sunucusu: Claude, ChatGPT, Cursor gibi yapay zekâ asistanlarını Portfolio Models'e bağlar.

    portfolio-models mcp                 # stdio (Claude Desktop, Claude Code, Cursor …)
    portfolio-models mcp --http          # Streamable HTTP, http://127.0.0.1:8765/mcp

Asistan; modelleri listeleyebilir, sembollerle optimizasyon ve backtest çalıştırabilir, enflasyon verisi alabilir,
kayıtlı portföyü okuyabilir ve (salt-okunur mod kapalıysa) pozisyon/işlem ekleyip çıkarabilir.

Ortam değişkenleri:
    PM_DATABASE_URL   — veritabanı (varsayılan: PM_DATA_DIR/portfolios.db, yani web arayüzüyle aynı dosya)
    PM_DATA_DIR       — varsayılan ~/.portfolio-models
    PM_MCP_USER       — hangi kullanıcının portföyü (varsayılan: yerel mod kullanıcısı)
    PM_MCP_READ_ONLY  — 1 ise yazma araçları hiç sunulmaz
    PM_EVDS_API_KEY   — güncel Türkiye TÜFE için (yoksa OECD)
"""

from __future__ import annotations

import math
import os
from datetime import date
from pathlib import Path
from typing import Any, Literal, TypedDict

import pandas as pd

from . import store
from .holdings import (
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
    asset_label,
    parse_trades,
)

LOCAL_USER = "yerel@localhost"  # web arayüzünün yerel modundaki kullanıcı
DEFAULT_PORTFOLIO = "Portföyüm"
HOLDINGS = "holdings"
FUNDS = "fund_prices"

Kind = Literal["bist", "fund", "yahoo", "gold", "cash"]
Side = Literal["buy", "sell", "dividend", "deposit", "withdraw"]
Region = Literal["TR", "US", "DE"]

KIND_MAP = {"bist": KIND_BIST, "fund": KIND_FUND, "yahoo": KIND_YAHOO, "gold": KIND_GOLD, "cash": KIND_CASH}
SIDE_MAP = {"buy": SIDE_BUY, "sell": SIDE_SELL, "dividend": SIDE_DIV, "deposit": SIDE_DEP, "withdraw": SIDE_WD}
KIND_NAMES = {v: k for k, v in KIND_MAP.items()}

INSTRUCTIONS = """\
Portfolio Models: portfolio optimisation and tracking for Turkish (BIST, TEFAS funds), US/global stocks and ETFs,
gold, crypto and cash. Values are in Turkish lira (TRY) unless stated otherwise.

Symbols: BIST stocks without suffix in `bist_symbols` (THYAO, ASELS). Yahoo Finance has no price history for
BIST-listed ETFs (e.g. GLDTR), so they cannot be tracked; use gold/cash kinds or the underlying instead. Everything on Yahoo
Finance in `symbols` (AAPL, VOO, QQQ, SPY, IWDA.AS, BTC-USD, GC=F, USDTRY=X).
Asset kinds for positions: bist, fund (TEFAS fund code, price must be supplied), yahoo (US/global stock, ETF, crypto),
gold (gram gold, no symbol), cash (currency code TRY/USD/EUR as symbol).

Model portfolios: investment firms and banks in any country publish model portfolios (asset + target weight).
Track them with save_model_portfolio (each call with a new `as_of` date adds a revision; history is kept so the
performance reflects every change) and compare them with compare_model_portfolios. When the user asks you to add or
update one, read the firm's own published page, then save exactly the holdings and weights it lists, the date the
firm gives for the change, and the page URL as `source_url`. Do not invent or estimate weights; if the page does not
give them, say so. Only save content the user is allowed to use; prefer official pages.

This is an educational tool, not investment advice. Say so when presenting optimisation results.
Before calling a tool that changes saved data, tell the user exactly what will change."""


# --- Yardımcılar -----------------------------------------------------------------


def _engine():
    url = os.environ.get("PM_DATABASE_URL") or os.environ.get("DB_URL")
    if not url:
        data_dir = Path(os.environ.get("PM_DATA_DIR", "~/.portfolio-models")).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{data_dir / 'portfolios.db'}"
    return store.make_engine(url)


def _user() -> str:
    return os.environ.get("PM_MCP_USER", LOCAL_USER)


def _clean(v: Any) -> Any:
    """JSON'a uygun sade değer (NaN → None, numpy → float, tarih → metin)."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        v = v.item()
        return None if isinstance(v, float) and math.isnan(v) else v
    if isinstance(v, (date, pd.Timestamp)):
        return str(v)[:10]
    return v


def _pct(v: Any, digits: int = 2) -> float | None:
    v = _clean(v)
    return None if v is None else round(float(v) * 100, digits)


def _tickers(symbols: list[str] | None, bist_symbols: list[str] | None) -> list[str]:
    from .data import bist

    out = list(dict.fromkeys([s.strip() for s in symbols or [] if s.strip()]
                             + bist(*[s.strip() for s in bist_symbols or [] if s.strip()])))
    if len(out) < 2:
        raise ValueError("Give at least 2 symbols (symbols and/or bist_symbols).")
    return out


def _returns(symbols, bist_symbols, start: str, end: str | None):
    from .data import load_prices, to_returns

    tickers = _tickers(symbols, bist_symbols)
    prices = load_prices(tickers, start=start, end=end)
    missing = sorted(set(tickers) - set(prices.columns))
    return to_returns(prices), prices, missing


def _resolve_name(engine, name: str | None, create: bool = False) -> str:
    if name:
        return name
    saved = store.list_portfolios(engine, _user(), kind=HOLDINGS)
    if saved:
        return saved[0]["name"]
    if create:
        return DEFAULT_PORTFOLIO
    raise ValueError("No saved portfolio yet. Add a position first or save one in the web app.")


def _load(engine, name: str) -> dict:
    cfg = store.load_portfolio(engine, _user(), name, kind=HOLDINGS)
    if cfg is None:
        return {"positions": [], "transactions": []}
    if isinstance(cfg, list):  # eski kayıt biçimi: yalnızca pozisyonlar
        return {"positions": cfg, "transactions": []}
    return {"positions": cfg.get("positions", []), "transactions": cfg.get("transactions", [])}


def _label(kind: str, symbol: str | None) -> str:
    label = asset_label(KIND_MAP[kind], symbol)
    if label is None:
        raise ValueError(f"Invalid symbol {symbol!r} for kind {kind!r}.")
    return label


def _row_label(row: dict) -> str | None:
    return asset_label(row.get("Tür"), row.get("Sembol"))


def _position_view(row: dict) -> dict:
    return {"kind": KIND_NAMES.get(row.get("Tür"), row.get("Tür")), "symbol": row.get("Sembol") or None,
            "quantity": row.get("Miktar"), "avg_cost": row.get("Ort. maliyet"),
            "current_price": row.get("Güncel fiyat")}


def _txn_view(row: dict) -> dict:
    sides = {v: k for k, v in SIDE_MAP.items()}
    return {"date": row.get("Tarih"), "side": sides.get(row.get("İşlem"), row.get("İşlem")),
            "kind": KIND_NAMES.get(row.get("Tür"), row.get("Tür")), "symbol": row.get("Sembol") or None,
            "quantity": row.get("Adet"), "price": row.get("Fiyat"), "amount": row.get("Tutar")}


# --- Araçlar (saf fonksiyonlar; testler doğrudan çağırır) --------------------------


def list_models() -> list[dict]:
    """All 24 optimisation models with a one-line description."""
    from .i18n import get_lang, set_lang
    from .models import list_models as _list

    prev = get_lang()
    set_lang("en")
    try:
        return [{"name": n, "description": d} for n, d in _list()]
    finally:
        set_lang(prev)


def optimize_portfolio(symbols: list[str] | None = None, bist_symbols: list[str] | None = None,
                       start: str = "2020-01-01", end: str | None = None, models: list[str] | None = None,
                       max_weight_pct: float | None = None) -> dict:
    """Fit optimisation models on daily returns and return each model's weights in percent.

    symbols: Yahoo Finance symbols (AAPL, VOO, BTC-USD, GC=F). bist_symbols: Borsa Istanbul codes (THYAO, ASELS).
    models: model names from list_models (default: a representative set of 6). max_weight_pct: cap per asset.
    """
    from .backtest import fit_weights

    returns, _, missing = _returns(symbols, bist_symbols, start, end)
    chosen = models or ["equal_weighted", "min_variance", "max_sharpe_shrunk", "risk_parity", "hrp", "max_diversification"]
    errors: dict[str, str] = {}
    weights = fit_weights(returns, chosen, on_error=lambda n, e: errors.__setitem__(n, str(e)),
                          max_weight=max_weight_pct / 100 if max_weight_pct else None)
    return {
        "period": f"{returns.index[0]:%Y-%m-%d} → {returns.index[-1]:%Y-%m-%d}",
        "weights_pct": {m: {a: round(float(w) * 100, 2) for a, w in weights[m].items() if abs(w) > 1e-4}
                        for m in weights.columns},
        "missing_symbols": missing,
        "failed_models": errors,
        "note": "Educational output, not investment advice. Weights are fitted on past returns.",
    }


def backtest_models(symbols: list[str] | None = None, bist_symbols: list[str] | None = None,
                    start: str = "2019-01-01", end: str | None = None, models: list[str] | None = None,
                    train_days: int = 252, rebalance_days: int = 21) -> dict:
    """Walk-forward backtest: train on `train_days`, hold `rebalance_days`, roll forward. Ranked by Sharpe."""
    from .backtest import backtest, summarize

    returns, _, missing = _returns(symbols, bist_symbols, start, end)
    if len(returns) <= train_days + rebalance_days:
        raise ValueError(f"Only {len(returns)} days of data; start earlier or shorten train_days.")
    errors: dict[str, str] = {}
    pop = backtest(returns, models, train_size=train_days, test_size=rebalance_days,
                   on_error=lambda n, e: errors.__setitem__(n, str(e)))
    table = summarize(pop)
    cols = {"Yıllık getiri": "annual_return_pct", "Yıllık volatilite": "annual_volatility_pct",
            "Maks. düşüş": "max_drawdown_pct", "CVaR %95": "cvar95_pct"}
    rows = []
    for name, r in table.iterrows():
        row = {"model": name, "sharpe": round(float(r["Sharpe"]), 3) if pd.notna(r.get("Sharpe")) else None,
               "sortino": round(float(r["Sortino"]), 3) if pd.notna(r.get("Sortino")) else None}
        row |= {v: _pct(r.get(k)) for k, v in cols.items()}
        rows.append(row)
    return {"period": f"{returns.index[0]:%Y-%m-%d} → {returns.index[-1]:%Y-%m-%d}", "results": rows,
            "missing_symbols": missing, "failed_models": errors,
            "note": "Past performance does not predict future returns. Not investment advice."}


def get_prices(symbols: list[str] | None = None, bist_symbols: list[str] | None = None,
               start: str = "2024-01-01") -> dict:
    """Latest close and simple returns (1 month, 1 year, since start) for each symbol, in its own currency."""
    from .data import bist, load_prices

    tickers = list(symbols or []) + bist(*(bist_symbols or []))
    if not tickers:
        raise ValueError("Give at least one symbol.")
    prices = load_prices(tickers + (["USDTRY=X"] if len(tickers) == 1 else []), start=start)
    out = {}
    for c in prices.columns:
        if c not in tickers:
            continue
        s = prices[c].dropna()
        last = s.index[-1]

        def ret(days: int) -> float | None:
            past = s[s.index <= last - pd.Timedelta(days=days)]
            return _pct(s.iloc[-1] / past.iloc[-1] - 1) if not past.empty else None

        out[c] = {"last_close": round(float(s.iloc[-1]), 4), "date": f"{last:%Y-%m-%d}",
                  "return_1m_pct": ret(30), "return_1y_pct": ret(365),
                  "return_since_start_pct": _pct(s.iloc[-1] / s.iloc[0] - 1)}
    return {"prices": out, "missing_symbols": sorted(set(tickers) - set(out))}


def get_inflation(region: Region = "TR", months: int = 12) -> dict:
    """Official CPI: year-over-year inflation per month. TR: TCMB EVDS/OECD, US: FRED/BLS, DE: Bundesbank."""
    from .benchmarks import fetch_cpi_best

    start = f"{date.today().year - max(2, months // 12 + 2)}-01"
    cpi, source = fetch_cpi_best(os.environ.get("PM_EVDS_API_KEY"), start=start, region=region)
    yoy = (cpi / cpi.shift(12) - 1).dropna().tail(months)
    return {"region": region, "source": source, "latest_month": f"{cpi.index.max():%Y-%m}",
            "yoy_inflation_pct": {f"{d:%Y-%m}": _pct(v) for d, v in yoy.items()}}


def list_portfolios() -> list[dict]:
    """Saved portfolios (positions and transactions) of the configured user, most recently changed first."""
    engine = _engine()
    return [{"name": p["name"], "updated": str(p["updated_at"])[:19]}
            for p in store.list_portfolios(engine, _user(), kind=HOLDINGS)]


def get_portfolio(name: str | None = None, include_valuation: bool = True) -> dict:
    """A saved portfolio: raw positions and transactions, plus live valuation in TRY (value, weight, P&L, weekly %).

    name: portfolio name from list_portfolios (default: most recently saved).
    """
    from .report import compute_summary

    engine = _engine()
    name = _resolve_name(engine, name)
    cfg = _load(engine, name)
    out: dict[str, Any] = {"name": name, "positions": [_position_view(r) for r in cfg["positions"]],
                           "transactions": [_txn_view(r) for r in cfg["transactions"]]}
    if not include_valuation:
        return out
    fund_hist = {f["name"]: store.load_portfolio(engine, _user(), f["name"], kind=FUNDS) or {}
                 for f in store.list_portfolios(engine, _user(), kind=FUNDS)}
    s = compute_summary(_user(), name, cfg, fund_hist)
    holdings = []
    for _, r in s.table.iterrows():
        holdings.append({"asset": r["Varlık"], "kind": KIND_NAMES.get(r["Tür"], r["Tür"]),
                         "quantity": _clean(r["Miktar"]), "last_price": _clean(r["Son fiyat"]),
                         "currency": r["Para birimi"], "price_date": _clean(r["Fiyat tarihi"]),
                         "value_try": round(float(r["Değer (TL)"]), 2), "weight_pct": _pct(r.get("Ağırlık")),
                         "pnl_try": _clean(r.get("K/Z (TL)")), "pnl_pct": _pct(r.get("K/Z %")),
                         "daily_pct": _pct(r.get("Günlük %")), "weekly_pct": _pct(r.get("Haftalık %"))})
    out["valuation"] = {"total_try": round(s.total, 2),
                        "week_change_try": None if s.week_change is None else round(s.week_change, 2),
                        "week_change_pct": _pct(s.week_pct), "holdings": holdings,
                        "stale_fund_prices": s.stale_funds, "warnings": s.warnings}
    return out


def add_position(kind: Kind, quantity: float, symbol: str | None = None, avg_cost: float | None = None,
                 current_price: float | None = None, portfolio: str | None = None) -> dict:
    """Add or update a current holding (no date). If the asset is already there, its quantity/cost are replaced.

    kind: bist (THYAO, ASELS), yahoo (AAPL, VOO, BTC-USD), fund (TEFAS code; give current_price in TRY),
    gold (gram gold; no symbol), cash (symbol = TRY/USD/EUR). avg_cost: per unit, in the asset's own currency.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive.")
    engine = _engine()
    name = _resolve_name(engine, portfolio, create=True)
    cfg = _load(engine, name)
    label = _label(kind, symbol)
    row = {"Tür": KIND_MAP[kind], "Sembol": "" if kind == "gold" else (symbol or "TRY").strip().upper(),
           "Miktar": float(quantity), "Ort. maliyet": avg_cost, "Güncel fiyat": current_price}
    positions = [r for r in cfg["positions"] if _row_label(r) != label]
    replaced = len(positions) != len(cfg["positions"])
    positions.append(row)
    store.save_portfolio(engine, _user(), name, {**cfg, "positions": positions}, kind=HOLDINGS)
    return {"portfolio": name, "asset": label, "action": "updated" if replaced else "added",
            "positions": [_position_view(r) for r in positions]}


def remove_position(symbol: str, kind: Kind | None = None, portfolio: str | None = None) -> dict:
    """Remove a holding from the positions list (transactions are kept). symbol: THYAO, AAPL, TTE, USD, gold …"""
    engine = _engine()
    name = _resolve_name(engine, portfolio)
    cfg = _load(engine, name)
    if kind:
        targets = {_label(kind, symbol)}
    else:
        s = symbol.strip().upper()
        targets = {_label(k, s) for k in ("bist", "yahoo", "fund")} | {f"Nakit {s}"}
        if s in ("GOLD", "ALTIN", "GRAM ALTIN", "XAU"):
            targets.add("Gram altın")
    positions = [r for r in cfg["positions"] if _row_label(r) not in targets]
    removed = len(cfg["positions"]) - len(positions)
    if not removed:
        in_txns = any(asset_label(r.get("Tür"), r.get("Sembol")) in targets for r in cfg["transactions"])
        hint = " It comes from transactions; add a 'sell' transaction instead." if in_txns else ""
        raise ValueError(f"{symbol!r} is not in the positions of {name!r}.{hint}")
    store.save_portfolio(engine, _user(), name, {**cfg, "positions": positions}, kind=HOLDINGS)
    return {"portfolio": name, "removed": removed, "positions": [_position_view(r) for r in positions]}


def add_transaction(side: Side, kind: Kind, trade_date: str, symbol: str | None = None,
                    quantity: float | None = None, price: float | None = None, amount: float | None = None,
                    portfolio: str | None = None) -> dict:
    """Record a dated transaction. buy/sell: quantity + unit price (asset's own currency).
    dividend: amount (net). deposit/withdraw: kind=cash, symbol=currency, amount. trade_date: YYYY-MM-DD.
    """
    engine = _engine()
    name = _resolve_name(engine, portfolio, create=True)
    cfg = _load(engine, name)
    row = {"Tarih": trade_date, "İşlem": SIDE_MAP[side], "Tür": KIND_MAP[kind],
           "Sembol": "" if kind == "gold" else (symbol or "").strip().upper(),
           "Adet": quantity, "Fiyat": price, "Tutar": amount}
    trades, warns = parse_trades([row])
    if not trades:
        raise ValueError("Invalid transaction: " + "; ".join(warns or ["check the fields"]))
    txns = cfg["transactions"] + [row]
    store.save_portfolio(engine, _user(), name, {**cfg, "transactions": txns}, kind=HOLDINGS)
    return {"portfolio": name, "added": _txn_view(row), "transaction_count": len(txns)}


# --- Model portföyler (kurumların yayımladığı) --------------------------------------------


class Holding(TypedDict):
    kind: Kind
    symbol: str | None
    weight: float


def _mp_view(name: str, cfg: dict) -> dict:
    from .model_portfolios import current_holdings

    revs = cfg.get("revisions", [])
    return {"name": name, "provider": cfg.get("provider"), "country": cfg.get("country"),
            "source_url": cfg.get("source_url"), "note": cfg.get("note"),
            "first_date": revs[0]["date"] if revs else None, "last_update": revs[-1]["date"] if revs else None,
            "revision_count": len(revs), "current_holdings": current_holdings(cfg)}


def list_model_portfolios() -> list[dict]:
    """Saved model portfolios of investment firms: provider, country, source, last update and current weights."""
    from .model_portfolios import load_all

    return [_mp_view(n, c) for n, c in load_all(_engine(), _user()).items()]


def get_model_portfolio(name: str) -> dict:
    """One model portfolio with its full revision history (every dated change of holdings and weights)."""
    from .model_portfolios import STORE_KIND

    cfg = store.load_portfolio(_engine(), _user(), name, kind=STORE_KIND)
    if cfg is None:
        raise ValueError(f"No model portfolio named {name!r}. Use list_model_portfolios.")
    return _mp_view(name, cfg) | {"revisions": cfg.get("revisions", [])}


def save_model_portfolio(name: str, holdings: list[Holding], as_of: str | None = None,
                         provider: str | None = None, country: str | None = None, source_url: str | None = None,
                         note: str | None = None) -> dict:
    """Create a model portfolio or record a new revision of it.

    name: short unique name, e.g. "Acme Securities · Equity model". holdings: [{kind, symbol, weight}] with weight in
    percent (scaled to 100 if needed); kinds: bist (THYAO), yahoo (AAPL, VOO, ALV.DE), fund (TEFAS code), gold, cash.
    as_of: YYYY-MM-DD the firm's change took effect (default today); a revision on the same date is replaced, an
    earlier revision history is kept. provider / country (ISO code, e.g. TR, US, DE) / source_url / note: metadata.
    """
    from .model_portfolios import STORE_KIND, add_revision

    engine = _engine()
    name = name.strip()
    old = store.load_portfolio(engine, _user(), name, kind=STORE_KIND)
    cfg, warns = add_revision(old, as_of or f"{date.today():%Y-%m-%d}", [dict(h) for h in holdings],
                              provider=provider, country=country.upper() if country else None,
                              source_url=source_url, note=note)
    store.save_portfolio(engine, _user(), name, cfg, kind=STORE_KIND)
    return {"action": "revision added" if old else "created", "warnings": warns} | _mp_view(name, cfg)


def delete_model_portfolio(name: str) -> dict:
    """Delete a model portfolio and its whole revision history. Cannot be undone."""
    from .model_portfolios import STORE_KIND

    if not store.delete_portfolio(_engine(), _user(), name, kind=STORE_KIND):
        raise ValueError(f"No model portfolio named {name!r}.")
    return {"deleted": name}


def compare_model_portfolios(names: list[str] | None = None, currency: Literal["TRY", "USD", "EUR"] = "TRY",
                             benchmarks: list[Literal["BIST100", "S&P 500", "DAX", "Gram altın", "USD", "EUR"]]
                             | None = None) -> dict:
    """Compare model portfolios with end-of-day prices: returns for 1 day, 1 week, 1/3 months, year-to-date, 1 year
    and since inception, annualised return and volatility, max drawdown. Each revision is applied on its date.

    names: default all. currency: the view (TRY, or USD/EUR = TRY index divided by the FX rate).
    benchmarks: optional reference series (default BIST100).
    """
    from .model_portfolios import compare_models, load_all, market_for

    engine = _engine()
    configs = load_all(engine, _user())
    if names:
        unknown = sorted(set(names) - set(configs))
        if unknown:
            raise ValueError(f"Unknown model portfolios: {', '.join(unknown)}.")
        configs = {n: configs[n] for n in names}
    if not configs:
        raise ValueError("No model portfolios saved yet. Use save_model_portfolio first.")
    benchmarks = ["BIST100"] if benchmarks is None else benchmarks
    fund_hist = {}
    from .fund_prices import history_series

    for f in store.list_portfolios(engine, _user(), kind=FUNDS):
        fund_hist[f["name"]] = history_series(store.load_portfolio(engine, _user(), f["name"], kind=FUNDS) or {})
    try_prices, closes = market_for(configs, benchmarks, fund_history=fund_hist)
    comp = compare_models(configs, try_prices, closes, currency, benchmarks)
    keys = {"1G": "return_1d_pct", "1H": "return_1w_pct", "1A": "return_1m_pct", "3A": "return_3m_pct",
            "YB": "return_ytd_pct", "1Y": "return_1y_pct", "total": "return_since_inception_pct",
            "annual": "annualised_return_pct", "vol": "annualised_volatility_pct", "max_dd": "max_drawdown_pct"}
    rows = []
    for r in sorted(comp.table, key=lambda r: (r["is_benchmark"], -(r["total"] or -9e9))):
        rows.append({"name": r["name"], "provider": r["provider"], "benchmark": r["is_benchmark"],
                     "last_update": r["updated"], "since": _clean(r["since"])}
                    | {v: _pct(r.get(k)) for k, v in keys.items()})
    return {"currency": currency, "price_date": _clean(comp.price_date), "results": rows,
            "warnings": comp.warnings,
            "note": "Benchmarks start on the earliest model's start date. Past performance is no guarantee; "
                    "not investment advice."}


# --- Sunucu ----------------------------------------------------------------------


def _read_only() -> bool:
    return os.environ.get("PM_MCP_READ_ONLY", "").strip().lower() in ("1", "true", "yes", "on")


def build_server(read_only: bool | None = None):
    from mcp.server.mcpserver import MCPServer
    from mcp.types import ToolAnnotations

    from importlib.metadata import version

    _v = version("portfolio-models")

    read_only = _read_only() if read_only is None else read_only
    server = MCPServer("portfolio-models", title="Portfolio Models", instructions=INSTRUCTIONS,
                       website_url="https://github.com/ozanbayhan/portfolio-models", version=_v)
    ro = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
    local_ro = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    for fn, ann in ((list_models, local_ro), (optimize_portfolio, ro), (backtest_models, ro), (get_prices, ro),
                    (get_inflation, ro), (list_portfolios, local_ro), (get_portfolio, ro),
                    (list_model_portfolios, local_ro), (get_model_portfolio, local_ro),
                    (compare_model_portfolios, ro)):
        server.tool(annotations=ann)(fn)
    if not read_only:
        server.tool(annotations=write)(add_position)
        server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                                                openWorldHint=False))(remove_position)
        server.tool(annotations=write)(add_transaction)
        server.tool(annotations=write)(save_model_portfolio)
        server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                                                openWorldHint=False))(delete_model_portfolio)
    return server


def run(http: bool = False, host: str = "127.0.0.1", port: int = 8765) -> None:
    from .i18n import set_lang

    set_lang("tr")  # dil sabitlenir; Streamlit oturumu aranmaz (stderr uyarılarını önler)
    server = build_server()
    if http:
        server.run("streamable-http", host=host, port=port)
    else:
        server.run("stdio")
