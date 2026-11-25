"""Haftalık portföy özeti: hesaplama, HTML e-posta ve gönderim.

GitHub Actions'tan her pazartesi çalışır (`python -m portfolio_models.report`).
Yalnızca uygulamada "Haftalık e-posta özeti" kutusunu işaretleyen kullanıcılara gönderir.

Ortam değişkenleri:
    DB_URL         — veritabanı bağlantısı (uygulamayla aynı)
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM — e-posta sunucusu (ör. Gmail uygulama şifresi)
    APP_URL        — e-postadaki bağlantı (varsayılan: https://portfolio-models.streamlit.app)
"""

from __future__ import annotations

import argparse
import html
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import date
from email.message import EmailMessage

import pandas as pd

from . import store
from .i18n import get_lang, num_sep, set_lang, t
from .insights import pct
from .fund_prices import history_series
from .holdings import (
    KIND_CASH,
    KIND_FUND,
    KIND_GOLD,
    KIND_YAHOO,
    aggregate_trades,
    cash_balances,
    cash_tracking,
    display_label,
    fetch_market_data,
    make_position,
    merge_rows_with_trades,
    parse_positions,
    parse_trades,
    try_price_history,
    valuation,
)

SETTINGS_KIND = "settings"
WEEKLY_KEY = "weekly_email"
APP_URL = os.environ.get("APP_URL", "https://portfolio-models.streamlit.app").rstrip("/")


# --- Tercih ----------------------------------------------------------------------


def weekly_enabled(engine, email: str) -> bool:
    cfg = store.load_portfolio(engine, email, WEEKLY_KEY, kind=SETTINGS_KIND)
    return bool(cfg and cfg.get("enabled"))


def set_weekly(engine, email: str, enabled: bool, lang: str = "tr") -> None:
    """Aboneliği açar/kapatır; e-postanın gönderileceği dili de saklar."""
    store.save_portfolio(engine, email, WEEKLY_KEY, {"enabled": bool(enabled), "lang": lang}, kind=SETTINGS_KIND)


def weekly_lang(engine, email: str) -> str:
    cfg = store.load_portfolio(engine, email, WEEKLY_KEY, kind=SETTINGS_KIND) or {}
    return cfg.get("lang", "tr")


def subscribers(engine) -> list[str]:
    from sqlalchemy import select

    tbl = store.TABLES[SETTINGS_KIND]
    with engine.connect() as conn:
        rows = conn.execute(select(tbl.c.user_email, tbl.c.config).where(tbl.c.name == WEEKLY_KEY)).all()
    import json

    return sorted({r.user_email for r in rows if json.loads(r.config).get("enabled")})


# --- Hesaplama --------------------------------------------------------------------


@dataclass
class WeeklySummary:
    email: str
    portfolio: str
    total: float
    week_change: float | None
    table: pd.DataFrame
    stale_funds: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def week_pct(self) -> float | None:
        if self.week_change is None or self.total - self.week_change <= 0:
            return None
        return self.week_change / (self.total - self.week_change)


def _unpack(cfg) -> tuple[list[dict], list[dict]]:
    if isinstance(cfg, list):
        return cfg, []
    cfg = cfg or {}
    return cfg.get("positions", []), cfg.get("transactions", [])


def compute_summary(email: str, name: str, cfg, fund_hist: dict[str, dict[str, float]],
                    market=fetch_market_data, today: date | None = None) -> WeeklySummary:
    """Son kaydedilen portföy için güncel değer ve son 7 günün değişimi (bugünkü miktarlarla)."""
    today = pd.Timestamp(today or date.today())
    rows, txns = _unpack(cfg)
    trades, w1 = parse_trades(txns, today=today.date())
    summary, w2 = aggregate_trades(trades)
    real_hist = {c: history_series(h) for c, h in fund_hist.items() if h}
    fund_pricing = dict(real_hist)
    for tr in trades:
        if tr.kind == KIND_FUND and tr.is_trade:
            s = fund_pricing.get(tr.label, pd.Series(dtype=float))
            if tr.date not in s.index:
                s = pd.concat([s, pd.Series({tr.date: tr.price})]).sort_index()
            fund_pricing[tr.label] = s
    sets = dict(funds_with_history=set(real_hist), funds_with_price=set(fund_pricing))
    positions, w3 = parse_positions(merge_rows_with_trades(rows, summary), **sets)
    cash_curs = {tr.symbol for tr in trades if tr.kind == KIND_CASH and tr.symbol != "TRY"}
    probe = positions + [make_position(KIND_CASH, c, 0.0) for c in cash_curs]
    closes, currencies = market([p for p in probe if p.kind != KIND_FUND], years=1)
    if cash_tracking(trades):
        positions, w3 = parse_positions(merge_rows_with_trades(rows, summary, cash_balances(trades, currencies)),
                                        **sets)
    prices = try_price_history(positions, closes, currencies, fund_pricing)
    table, missing = valuation(positions, closes, currencies, prices, fund_pricing)
    warnings = w1 + w2 + w3 + ([t("Fiyat bulunamadı: {assets}", assets=", ".join(missing))] if missing else [])
    if table.empty:
        return WeeklySummary(email, name, 0.0, None, table, warnings=warnings)

    # Haftalık değişim: bugünkü miktarlarla, 7 gün önceki (ya da önceki ilk) fiyatlara göre
    week_ago = today - pd.Timedelta(days=7)
    past = prices[prices.index <= week_ago]
    week_change = None
    weekly_pct = {}
    if not past.empty:
        then = past.iloc[-1]
        now = prices.ffill().iloc[-1]
        change = 0.0
        for p in positions:
            if p.label in then and pd.notna(then[p.label]) and then[p.label] > 0:
                change += p.quantity * (now[p.label] - then[p.label])
                weekly_pct[p.label] = now[p.label] / then[p.label] - 1
        week_change = change
    table = table.copy()
    table["Haftalık %"] = table["Varlık"].map(weekly_pct)
    stale = [r["Varlık"] for _, r in table.iterrows()
             if r["Tür"] == KIND_FUND and r["Fiyat tarihi"] and (today.date() - r["Fiyat tarihi"]).days > 7]
    return WeeklySummary(email, name, float(table["Değer (TL)"].sum()), week_change, table, stale, warnings)


# --- E-posta ----------------------------------------------------------------------


def _tl(x: float) -> str:
    dec, thou = num_sep()
    return "₺" + f"{x:,.0f}".replace(",", thou)


def _pct(x) -> str:
    return "—" if x is None or pd.isna(x) else pct(x, 2, sign=True)


def _asset(name: str) -> str:
    return display_label(name)


def render_html(s: WeeklySummary, app_url: str = APP_URL) -> str:
    lang = get_lang()
    color = "#2e9e5b" if (s.week_change or 0) >= 0 else "#d9534f"
    head = (f"<p style='font-size:28px;margin:0'><b>{_tl(s.total)}</b></p>"
            f"<p style='margin:4px 0 16px;color:{color}'>{t('Bu hafta')}: "
            f"{_tl(s.week_change) if s.week_change is not None else '—'} ({_pct(s.week_pct)})</p>")
    rows = ""
    tb = s.table.sort_values("Değer (TL)", ascending=False) if not s.table.empty else s.table
    for _, r in tb.iterrows():
        wk = r.get("Haftalık %")
        c = "#2e9e5b" if pd.notna(wk) and wk >= 0 else ("#d9534f" if pd.notna(wk) else "#888")
        rows += (f"<tr><td style='padding:4px 8px'>{html.escape(_asset(r['Varlık']))}</td>"
                 f"<td style='padding:4px 8px;text-align:right'>{_tl(r['Değer (TL)'])}</td>"
                 f"<td style='padding:4px 8px;text-align:right'>{pct(r['Ağırlık'])}</td>"
                 f"<td style='padding:4px 8px;text-align:right;color:{c}'>{_pct(wk)}</td></tr>")
    notes = ""
    if s.stale_funds:
        notes += ("<p style='color:#b8860b'>" + html.escape(t(
            "⚠️ Fiyatı 7 günden eski fonlar: {funds}. Uygulamada Fon fiyatları sekmesinden güncelleyebilirsiniz.",
            funds=", ".join(s.stale_funds))) + "</p>")
    th = "padding:4px 8px"
    return f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;color:#222">
<h2 style="margin:0 0 4px">💼 {html.escape(t('Haftalık portföy özeti'))}</h2>
<p style="margin:0 0 16px;color:#666">{html.escape(s.portfolio)} · {date.today():%d.%m.%Y}</p>
{head}
<table style="border-collapse:collapse;width:100%;font-size:14px">
<tr style="background:#f3f3f3"><th style="text-align:left;{th}">{t('Varlık')}</th>
<th style="text-align:right;{th}">{t('Değer')}</th><th style="text-align:right;{th}">{t('Ağırlık')}</th>
<th style="text-align:right;{th}">{t('Haftalık')}</th></tr>
{rows}</table>
{notes}
<p style="margin-top:16px"><a href="{app_url}/portfoyum?lang={lang}">{t('Portföyümü aç →')}</a></p>
<p style="font-size:12px;color:#888">{html.escape(t(
    "Haftalık değişim bugünkü miktarlarla hesaplanır. Eğitim amaçlıdır, yatırım tavsiyesi değildir. Bu e-postaları "
    "almak istemiyorsanız uygulamada Portföyüm sayfasındaki \"Haftalık e-posta özeti\" anahtarını kapatın."))}</p></div>"""


def build_message(s: WeeklySummary, sender: str, app_url: str = APP_URL) -> EmailMessage:
    msg = EmailMessage()
    change = f" ({_pct(s.week_pct)})" if s.week_pct is not None else ""
    msg["Subject"] = t("Portföy özeti: {value}", value=_tl(s.total)) + change
    msg["From"] = sender
    msg["To"] = s.email
    msg.set_content(t("Portföy değeri: {value}. Bu hafta: {change}. Ayrıntılar: {url}",
                      value=_tl(s.total), change=_pct(s.week_pct), url=f"{app_url}/portfoyum?lang={get_lang()}"))
    msg.add_alternative(render_html(s, app_url), subtype="html")
    return msg


def send(messages: list[EmailMessage]) -> None:
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "465"))
    user, password = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=60) as smtp:
        smtp.login(user, password)
        for m in messages:
            smtp.send_message(m)


def run(engine, sender: str, dry_run: bool = False, out_dir: str | None = None, market=fetch_market_data) -> list[str]:
    """Abonelerin özetlerini oluşturur ve gönderir. Döner: işlenen e-postalar ve durumları."""
    log, messages = [], []
    for email in subscribers(engine):
        saved = store.list_portfolios(engine, email, kind="holdings")
        if not saved:
            log.append(f"{email}: kayıtlı portföy yok, atlandı")
            continue
        name = saved[0]["name"]
        cfg = store.load_portfolio(engine, email, name, kind="holdings")
        fund_hist = {f["name"]: store.load_portfolio(engine, email, f["name"], kind="fund_prices") or {}
                     for f in store.list_portfolios(engine, email, kind="fund_prices")}
        set_lang(weekly_lang(engine, email))  # e-posta, kullanıcının seçtiği dilde
        try:
            s = compute_summary(email, name, cfg, fund_hist, market=market)
        except Exception as exc:  # noqa: BLE001 - bir kullanıcının hatası diğerlerini durdurmasın
            log.append(f"{email}: hesaplanamadı ({exc.__class__.__name__})")
            continue
        if s.table.empty:
            log.append(f"{email}: değerlenecek varlık yok, atlandı")
            continue
        messages.append(build_message(s, sender))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, f"{email.replace('@', '_at_')}.html"), "w", encoding="utf-8") as f:
                f.write(render_html(s))
        log.append(f"{email}: hazır ({_tl(s.total)})")
    set_lang("tr")
    if messages and not dry_run:
        send(messages)
        log.append(f"{len(messages)} e-posta gönderildi")
    return log


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Haftalık portföy özeti e-postası")
    ap.add_argument("--dry-run", action="store_true", help="Göndermeden yalnızca hesapla")
    ap.add_argument("--out", help="E-posta HTML'lerini bu klasöre de yaz")
    args = ap.parse_args(argv)
    engine = store.make_engine(os.environ["DB_URL"])
    sender = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER", "")
    for line in run(engine, sender, dry_run=args.dry_run, out_dir=args.out):
        # e-posta adresleri Actions loglarında görünmesin
        user, _, rest = line.partition(":")
        print(("***" + user[user.find("@"):] if "@" in user else user) + (":" + rest if rest else ""))


if __name__ == "__main__":
    main()
