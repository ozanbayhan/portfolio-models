import numpy as np
import pandas as pd
import pytest

from portfolio_models import fit_weights
from portfolio_models.insights import (
    asset_facts,
    backtest_comment,
    black_litterman_comment,
    consensus,
    model_comment,
    num,
    pct,
    rebalance_comment,
    weight_metrics,
)
from portfolio_models.models import MODELS


@pytest.fixture(scope="module")
def returns():
    rng = np.random.default_rng(3)
    n = 500
    idx = pd.bdate_range("2024-01-01", periods=n)
    m = rng.normal(0.0004, 0.01, n)
    return pd.DataFrame({
        "SAKIN": 0.0002 + 0.2 * m + rng.normal(0, 0.003, n),
        "ORTA": 0.0004 + 0.8 * m + rng.normal(0, 0.008, n),
        "OYNAK": 0.0008 + 1.2 * m + rng.normal(0, 0.02, n),
        "BAGIMSIZ": 0.0003 + rng.normal(0, 0.009, n),
    }, index=idx)


def test_every_model_has_description():
    from portfolio_models.model_guide import GUIDE

    assert set(MODELS) <= set(GUIDE)


def test_pct_turkish():
    assert pct(0.1234) == "%12,3" and pct(-0.05, sign=True) == "−%5,0" and pct(float("nan")) == "—"


def test_metrics(returns):
    w = pd.Series({"SAKIN": 1.0, "ORTA": 0, "OYNAK": 0, "BAGIMSIZ": 0})
    m = weight_metrics(w, returns)
    assert m.top == "SAKIN" and m.eff_n == pytest.approx(1) and m.top_risk_share == pytest.approx(1)
    eq = weight_metrics(pd.Series(0.25, index=returns.columns), returns)
    assert eq.eff_n == pytest.approx(4) and eq.div_ratio > 1


def test_model_comments_reflect_data(returns):
    w = fit_weights(returns, ["equal_weighted", "min_variance", "max_sharpe"])
    base = weight_metrics(w["equal_weighted"], returns)
    mv = model_comment("min_variance", w["min_variance"], returns, base)
    assert "SAKIN" in mv and "Ne yapar" in mv and "Eşit ağırlığa göre oynaklık −" in mv and "puan" in mv
    ms = model_comment("max_sharpe", w["max_sharpe"], returns, base)
    assert "hata maksimizasyonu" in ms and ms.count("Geçmiş ortalama") == 1  # uyarı var, tekrar yok
    facts = " ".join(asset_facts(returns))
    assert "En sakin varlık **SAKIN**" in facts and "**OYNAK**" in facts
    cons = " ".join(consensus(w))
    assert "ayrışıyor" in cons and "ortalaması" in cons


def test_concentration_warning(returns):
    w = pd.Series({"SAKIN": 0.7, "ORTA": 0.1, "OYNAK": 0.1, "BAGIMSIZ": 0.1})
    assert "yarısından fazlası tek varlıkta (SAKIN)" in model_comment("hrp", w, returns)


def test_backtest_comment():
    table = pd.DataFrame(
        {"Yıllık getiri": [0.20, 0.30, 0.10], "Sharpe": [1.0, 1.4, 0.8], "Maks. düşüş": [0.15, 0.30, 0.08]},
        index=["equal_weighted", "max_sharpe", "min_variance"],
    )
    text = " ".join(backtest_comment(table))
    assert "**max_sharpe** (Sharpe 1,40)" in text
    assert "2 modelden 1 tanesi eşit ağırlığı" in text
    assert "En sığ düşüş: **min_variance**" in text
    assert "tekrar etmeyebilir" in text  # getiriye duyarlı model en iyi çıktı


def test_bl_and_rebalance_comments():
    base = pd.Series({"A": 0.5, "B": 0.5})
    bl = pd.Series({"A": 0.7, "B": 0.3})
    text = " ".join(black_litterman_comment(base, bl, ["A == 0.001"]))
    assert "**A** (%50,0 → %70,0)" in text and "%20,0" in text
    reb = pd.DataFrame({"Varlık": ["A", "B"], "Mevcut ağırlık": [0.8, 0.2], "Hedef ağırlık": [0.5, 0.5],
                        "İşlem": ["Sat", "Al"]})
    r = " ".join(rebalance_comment(reb, "hrp"))
    assert "**B**" in r and "**A**" in r and "Sapma yüksek" in r


def test_languages(returns):
    from portfolio_models.i18n import set_lang

    w = fit_weights(returns, ["equal_weighted", "min_variance"])
    try:
        set_lang("en")
        assert pct(0.1234) == "12.3%" and num(1.5) == "1.50"
        en = model_comment("min_variance", w["min_variance"], returns)
        assert "What it does" in en and "Effective number of assets" in en
        set_lang("de")
        assert pct(0.1234) == "12,3 %"
        de = " ".join(asset_facts(returns))
        assert "ruhigste Wert" in de
    finally:
        set_lang("tr")
