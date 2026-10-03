"""Moteur de simulation : calcul mois par mois, sans aucune dépendance à l'interface.

Modèle :
- le rendement annuel est converti en taux mensuel équivalent ((1+r)^(1/12));
- les frais annuels sont prélevés chaque mois sur le capital (même conversion);
- chaque versement est effectué en fin de mois, après les intérêts du mois;
- le versement est soit fixe (avec une hausse annuelle optionnelle), soit un pourcentage d'un salaire
  qui évolue au fil de la carrière : voir salary.contribution_schedule;
- avec l'enveloppe "pea", les versements vont dans le PEA jusqu'à son plafond (calculé
  sur les versements cumulés), puis le surplus est placé sur un compte-titres;
  les deux comptes ont les mêmes rendement et frais;
- l'impôt est celui d'une sortie totale à la date considérée, compte par compte;
- en "euros constants", tout montant du mois t est divisé par (1+inflation)^(t/12)
  (le plafond du PEA, lui, est toujours appliqué en euros courants).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .params import SimulationParams
from .salary import contribution_schedule
from .taxes import tax_series

_MONEY = (
    "initial",
    "contributions",
    "interest",
    "total",
    "fees",
    "tax",
    "net",
    "month_contribution",
    "month_interest",
    "pea_total",
    "pea_invested",
    "cto_total",
    "cto_invested",
    "tax_pea",
    "tax_cto",
)


def run(params: SimulationParams) -> dict[str, np.ndarray]:
    """Exécute la simulation et renvoie des tableaux indexés par mois (0..n)."""
    n = params.months
    growth = (1 + params.annual_return_pct / 100) ** (1 / 12)
    keep = (1 - params.annual_fees_pct / 100) ** (1 / 12)
    net_growth = growth * keep
    schedule = contribution_schedule(params)  # versement de chaque mois (fixe, ou % du salaire)
    use_pea = params.tax_regime == "pea"

    # Deux comptes : le PEA (vide hors enveloppe "pea") et le compte-titres, qui reçoit tout le reste.
    pea_total, pea_invested = np.zeros(n + 1), np.zeros(n + 1)
    cto_total, cto_invested = np.zeros(n + 1), np.zeros(n + 1)
    month_contribution = np.zeros(n + 1)
    month_interest = np.zeros(n + 1)
    month_fees = np.zeros(n + 1)

    pea_in = min(params.initial_capital, params.pea_ceiling) if use_pea else 0.0
    cto_in = params.initial_capital - pea_in
    pea, cto = pea_in, cto_in
    pea_total[0], pea_invested[0] = pea, pea_in
    cto_total[0], cto_invested[0] = cto, cto_in

    for t in range(1, n + 1):
        contribution = schedule[t]
        before = pea + cto
        grown = before * growth
        month_fees[t] = grown * (1 - keep)
        month_interest[t] = grown * keep - before
        month_contribution[t] = contribution

        to_pea = min(contribution, max(params.pea_ceiling - pea_in, 0.0)) if use_pea else 0.0
        pea = pea * net_growth + to_pea
        cto = cto * net_growth + (contribution - to_pea)
        pea_in = min(pea_in + to_pea, params.pea_ceiling) if use_pea else 0.0
        cto_in += contribution - to_pea

        pea_total[t], pea_invested[t] = pea, pea_in
        cto_total[t], cto_invested[t] = cto, cto_in

    months = np.arange(n + 1)
    total = pea_total + cto_total
    initial = np.full(n + 1, params.initial_capital)
    contributions = np.cumsum(month_contribution)
    interest = total - initial - contributions

    zeros = np.zeros(n + 1)
    tax_args = (months, params.income_tax_pct, params.social_levy_pct)
    tax_pea = tax_series("pea", pea_total - pea_invested, *tax_args) if use_pea else zeros
    tax_cto = tax_series("cto", cto_total - cto_invested, *tax_args) if params.tax_regime != "none" else zeros
    tax = tax_pea + tax_cto

    arrays = {
        "month": months,
        "initial": initial,
        "contributions": contributions,
        "interest": interest,
        "total": total,
        "fees": np.cumsum(month_fees),
        "tax": tax,
        "net": total - tax,
        "month_contribution": month_contribution,
        "month_interest": month_interest,
        "pea_total": pea_total,
        "pea_invested": pea_invested,
        "cto_total": cto_total,
        "cto_invested": cto_invested,
        "tax_pea": tax_pea,
        "tax_cto": tax_cto,
    }
    if params.real_terms:
        deflator = (1 + params.inflation_pct / 100) ** (months / 12)
        for name in _MONEY:
            arrays[name] = arrays[name] / deflator
    return arrays


def simulate(params: SimulationParams) -> pd.DataFrame:
    """Simulation complète sous forme de tableau : une ligne par mois (0 = départ)."""
    arrays = run(params)
    df = pd.DataFrame(arrays)
    df.insert(1, "year", df["month"] / 12)
    df.insert(5, "invested", df["initial"] + df["contributions"])
    return df
