"""Salaire et versements : trajectoire du salaire, calendrier des versements, scénarios.

Deux modes de versement (params.contribution_mode) :
- "fixed"  : montant mensuel fixe, augmenté de x % à chaque anniversaire ;
- "salary" : un pourcentage du salaire net mensuel, qui évolue selon une trajectoire de carrière.

Le salaire augmente une fois par an, à chaque anniversaire. Le taux de l'augmentation dépend de la
phase de carrière (voir salary_profiles) : la progression est rapide au début, puis ralentit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .params import SimulationParams
from .salary_profiles import EARLY_END, MID_END, SCENARIOS, preset_rates

RATE_FIELDS = ("salary_growth_early_pct", "salary_growth_mid_pct", "salary_growth_late_pct")


def raise_pct(params: SimulationParams, career_year: int) -> float:
    """Augmentation (en %) accordée à la fin de l'année de carrière `career_year` (1, 2, 3…)."""
    if career_year <= EARLY_END:
        return params.salary_growth_early_pct
    if career_year <= MID_END:
        return params.salary_growth_mid_pct
    return params.salary_growth_late_pct


def monthly_salary(params: SimulationParams) -> np.ndarray:
    """Salaire net mensuel de chaque mois (indices 0..n ; le mois 0 reprend le salaire de départ)."""
    n = params.months
    last_year = max(n - 1, 0) // 12  # dernière année de carrière atteinte (0 = première année)
    factors = np.ones(last_year + 1)
    for year in range(1, last_year + 1):
        factors[year] = factors[year - 1] * (1 + raise_pct(params, year) / 100)
    year_of_month = np.maximum(np.arange(n + 1) - 1, 0) // 12
    return params.salary_monthly * factors[year_of_month]


def contribution_schedule(params: SimulationParams) -> np.ndarray:
    """Versement de chaque mois (indices 0..n ; rien n'est versé au mois 0)."""
    n = params.months
    year_of_month = np.maximum(np.arange(n + 1) - 1, 0) // 12
    if params.contribution_mode == "salary":
        amounts = params.salary_share_pct / 100 * monthly_salary(params)
    else:
        amounts = params.monthly_contribution * (1 + params.contribution_growth_pct / 100) ** year_of_month
    amounts = np.asarray(amounts, dtype=float).copy()
    amounts[0] = 0.0
    return amounts


def salary_frame(params: SimulationParams) -> pd.DataFrame:
    """Salaire et versement de chaque mois (mois 1 à n), pour les graphiques.

    Avec params.real_terms, les montants sont convertis en euros d'aujourd'hui, comme dans le moteur.
    """
    months = np.arange(1, params.months + 1)
    salary = monthly_salary(params)[1:]
    contribution = contribution_schedule(params)[1:]
    if params.real_terms:
        deflator = (1 + params.inflation_pct / 100) ** (months / 12)
        salary, contribution = salary / deflator, contribution / deflator
    return pd.DataFrame(
        {"month": months, "year": (months - 1) / 12, "salary": salary, "monthly_invested": contribution}
    )


def scenario_variants(params: SimulationParams) -> dict[str, SimulationParams]:
    """Le même scénario déroulé avec les trois trajectoires du profil choisi (peu favorable, moyenne, très favorable)."""
    variants = {}
    for code in SCENARIOS:
        rates = dict(zip(RATE_FIELDS, preset_rates(params.salary_profile, code)))
        variants[code] = params.with_(contribution_mode="salary", salary_scenario=code, **rates)
    return variants


def matches_preset(params: SimulationParams) -> bool:
    """Les taux d'augmentation sont-ils exactement ceux du scénario choisi (sinon : réglage personnalisé) ?"""
    expected = preset_rates(params.salary_profile, params.salary_scenario)
    return all(abs(getattr(params, field) - rate) < 1e-9 for field, rate in zip(RATE_FIELDS, expected))
