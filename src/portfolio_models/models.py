"""Tüm portföy modellerinin tek bir kayıt defteri.

Yeni model eklemek için MODELS sözlüğüne bir satır eklemeniz yeterli:
    "ad": (lambda: Tahminci(...), "kısa açıklama"),
Tahminci, skfolio arayüzüne uyan (fit(X) sonrası weights_ veren) herhangi bir nesne olabilir.
"""

from __future__ import annotations

from typing import Callable

from skfolio import RiskMeasure
from skfolio.optimization import (
    DistributionallyRobustCVaR,
    EqualWeighted,
    HierarchicalEqualRiskContribution,
    HierarchicalRiskParity,
    InverseVolatility,
    MaximumDiversification,
    MeanRisk,
    NestedClustersOptimization,
    ObjectiveFunction,
    RiskBudgeting,
    SchurComplementary,
    StackingOptimization,
)
from skfolio.prior import EmpiricalPrior
from skfolio.moments import ShrunkMu, LedoitWolf

from .adapters import ExternalOptimization

Factory = Callable[[], object]


def _stacking():
    return StackingOptimization(
        estimators=[
            ("hrp", HierarchicalRiskParity()),
            ("min_var", MeanRisk()),
            ("risk_parity", RiskBudgeting()),
            ("max_div", MaximumDiversification()),
        ],
        final_estimator=MeanRisk(
            objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
            risk_measure=RiskMeasure.CVAR,
        ),
    )


MODELS: dict[str, tuple[Factory, str]] = {
    # --- Basit referanslar
    "equal_weighted": (EqualWeighted, "Eşit ağırlık (1/N)"),
    "inverse_volatility": (InverseVolatility, "Volatilitenin tersiyle ağırlık"),
    # --- Ortalama-risk (Markowitz ailesi)
    "min_variance": (
        lambda: MeanRisk(risk_measure=RiskMeasure.VARIANCE),
        "Minimum varyans (Markowitz)",
    ),
    "max_sharpe": (
        lambda: MeanRisk(
            objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
            risk_measure=RiskMeasure.VARIANCE,
        ),
        "Maksimum Sharpe oranı",
    ),
    "max_sharpe_shrunk": (
        lambda: MeanRisk(
            objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
            prior_estimator=EmpiricalPrior(mu_estimator=ShrunkMu(), covariance_estimator=LedoitWolf()),
        ),
        "Maks. Sharpe, büzülmüş (shrinkage) beklenti ve Ledoit-Wolf kovaryans",
    ),
    "min_cvar": (lambda: MeanRisk(risk_measure=RiskMeasure.CVAR), "Minimum CVaR (%95)"),
    "max_sortino": (
        lambda: MeanRisk(
            objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
            risk_measure=RiskMeasure.SEMI_VARIANCE,
        ),
        "Maksimum Sortino oranı",
    ),
    "min_cdar": (lambda: MeanRisk(risk_measure=RiskMeasure.CDAR), "Minimum CDaR (drawdown riski)"),
    "min_max_drawdown": (
        lambda: MeanRisk(risk_measure=RiskMeasure.MAX_DRAWDOWN),
        "Minimum maksimum düşüş",
    ),
    "max_diversification": (MaximumDiversification, "Maksimum çeşitlendirme oranı"),
    "dro_cvar": (
        lambda: DistributionallyRobustCVaR(wasserstein_ball_radius=0.001),
        "Dağılımsal olarak dayanıklı CVaR (Wasserstein)",
    ),
    # --- Risk bütçeleme
    "risk_parity": (
        lambda: RiskBudgeting(risk_measure=RiskMeasure.VARIANCE),
        "Risk paritesi (eşit risk katkısı, varyans)",
    ),
    "risk_parity_cvar": (
        lambda: RiskBudgeting(risk_measure=RiskMeasure.CVAR),
        "Risk paritesi (CVaR)",
    ),
    # --- Hiyerarşik / kümeleme
    "hrp": (HierarchicalRiskParity, "Hiyerarşik risk paritesi (Lopez de Prado)"),
    "hrp_cdar": (
        lambda: HierarchicalRiskParity(risk_measure=RiskMeasure.CDAR),
        "HRP, CDaR risk ölçüsüyle",
    ),
    "herc": (HierarchicalEqualRiskContribution, "Hiyerarşik eşit risk katkısı"),
    "nco": (NestedClustersOptimization, "İç içe kümeler optimizasyonu"),
    "schur": (SchurComplementary, "Schur tamamlayıcı tahsis (HRP ile min. varyans arası)"),
    # --- Topluluk
    "stacking": (_stacking, "Stacking: HRP + min var + risk paritesi + maks. çeşitlendirme"),
    # --- Diğer kütüphaneler (adaptör üzerinden)
    "riskfolio_hrp": (lambda: ExternalOptimization("riskfolio_hrp"), "Riskfolio-Lib HRP (ward)"),
    "riskfolio_max_sharpe_cvar": (
        lambda: ExternalOptimization("riskfolio_max_sharpe_cvar"),
        "Riskfolio-Lib maks. getiri/CVaR",
    ),
    "riskfolio_min_cdar": (
        lambda: ExternalOptimization("riskfolio_min_cdar"),
        "Riskfolio-Lib minimum CDaR",
    ),
    "pypfopt_max_sharpe": (
        lambda: ExternalOptimization("pypfopt_max_sharpe"),
        "PyPortfolioOpt maks. Sharpe (Ledoit-Wolf)",
    ),
    "pypfopt_cla_min_vol": (
        lambda: ExternalOptimization("pypfopt_cla_min_vol"),
        "PyPortfolioOpt Critical Line Algorithm min. volatilite",
    ),
    # pypfopt_hrp: PyPortfolioOpt 1.6.0 güncel scipy ile bozuk (scipy _LINKAGE_METHODS kaldırıldı).
    # Düzeltilince açın: "pypfopt_hrp": (lambda: ExternalOptimization("pypfopt_hrp"), "PyPortfolioOpt HRP"),
}


def get_model(name: str):
    try:
        factory, _ = MODELS[name]
    except KeyError:
        raise KeyError(f"Bilinmeyen model: {name}. Liste için: portfolio-models list") from None
    return factory()


def list_models() -> list[tuple[str, str]]:
    return [(name, desc) for name, (_, desc) in MODELS.items()]
