"""Black-Litterman: kendi piyasa görüşlerinizi modele katın.

Çalıştır:  uv run python examples/black_litterman.py
"""

from skfolio import RiskMeasure
from skfolio.optimization import MeanRisk, ObjectiveFunction
from skfolio.prior import BlackLitterman

from portfolio_models import bist, load_prices, to_returns

tickers = bist("THYAO", "ASELS", "EREGL", "GARAN", "BIMAS")
returns = to_returns(load_prices(tickers, start="2021-01-01"))

# Görüşler GÜNLÜK getiri cinsinden yazılır; yıllık oranı 252'ye bölüyoruz.
views = [
    f"THYAO.IS == {0.25 / 252:.6f}",            # THYAO yıllık ~%25 getirir
    f"ASELS.IS - GARAN.IS == {0.10 / 252:.6f}",  # ASELS, GARAN'ı yıllık ~%10 geçer
]

model = MeanRisk(
    objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
    risk_measure=RiskMeasure.VARIANCE,
    prior_estimator=BlackLitterman(views=views),
)
model.fit(returns)

for name, w in zip(returns.columns, model.weights_):
    print(f"{name:10s} {w:6.1%}")
