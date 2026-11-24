from datetime import date

import pandas as pd
import pytest

from portfolio_models import store
from portfolio_models.holdings import KIND_BIST, KIND_CASH, KIND_FUND
from portfolio_models.report import build_message, compute_summary, run, set_weekly, subscribers, weekly_enabled


def fake_market(positions, years=1):
    idx = pd.bdate_range("2026-11-02", "2026-11-20")
    closes = pd.DataFrame({"THYAO.IS": [300.0] * 10 + [330.0] * 5, "USDTRY=X": 40.0}, index=idx)
    return closes, {"THYAO.IS": "TRY", "USDTRY=X": "TRY"}


CFG = {
    "positions": [{"Tür": KIND_BIST, "Sembol": "THYAO", "Miktar": 100},
                  {"Tür": KIND_CASH, "Sembol": "TRY", "Miktar": 1000}],
    "transactions": [{"Tarih": "2026-11-03", "İşlem": "Al", "Tür": KIND_FUND, "Sembol": "TTE", "Adet": 1000,
                      "Fiyat": 2.0}],
}
FUNDS = {"TTE": {"2026-11-03": 2.0, "2026-11-10": 2.1, "2026-11-12": 2.2}}


def test_compute_summary_weekly_change():
    s = compute_summary("a@x.com", "Ana", CFG, FUNDS, market=fake_market, today=date(2026, 11, 20))
    t = s.table.set_index("Varlık")
    assert s.total == 100 * 330 + 1000 + 1000 * 2.2
    # 13.11 -> 20.11: THYAO 300 -> 330 (+3000), TTE 2.2 -> 2.2
    assert s.week_change == 100 * 30
    assert t.loc["THYAO", "Haftalık %"] == pytest.approx(0.1)
    assert s.stale_funds == ["TTE"]  # son fon fiyatı 12.11, 8 gün önce


def test_message_and_html():
    s = compute_summary("a@x.com", "Ana <portföy>", CFG, FUNDS, market=fake_market, today=date(2026, 11, 20))
    m = build_message(s, "bot@example.com")
    assert m["To"] == "a@x.com" and "₺" in m["Subject"]
    body = m.get_body(("html",)).get_content()
    assert "Ana &lt;portföy&gt;" in body  # HTML kaçışı
    assert "THYAO" in body and "Haftalık" in body


def test_subscriptions_and_dry_run(tmp_path):
    eng = store.make_engine(f"sqlite:///{tmp_path / 'r.db'}")
    assert subscribers(eng) == []
    set_weekly(eng, "a@x.com", True)
    set_weekly(eng, "b@x.com", True)
    set_weekly(eng, "b@x.com", False)
    set_weekly(eng, "c@x.com", True)  # aboneliği var ama portföyü yok
    assert weekly_enabled(eng, "a@x.com") and not weekly_enabled(eng, "b@x.com")
    assert subscribers(eng) == ["a@x.com", "c@x.com"]
    store.save_portfolio(eng, "a@x.com", "Ana", CFG, kind="holdings")
    for code, h in FUNDS.items():
        store.save_portfolio(eng, "a@x.com", code, h, kind="fund_prices")
    log = run(eng, "bot@example.com", dry_run=True, out_dir=str(tmp_path / "out"), market=fake_market)
    assert any(line.startswith("a@x.com: hazır") for line in log)
    assert any(line.startswith("c@x.com: kayıtlı portföy yok") for line in log)
    assert (tmp_path / "out" / "a_at_x.com.html").exists()
