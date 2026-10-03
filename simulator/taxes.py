"""Fiscalité à la sortie : PEA et compte-titres (CTO), règles françaises.

Hypothèses (taux 2026, modifiables dans l'interface) :
- CTO : flat tax = impôt sur le revenu (12,8 %) + prélèvements sociaux (18,6 %)
  sur les gains, soit 31,4 %.
- PEA détenu depuis 5 ans ou plus : seulement les prélèvements sociaux.
- PEA retiré avant 5 ans : flat tax comme le CTO (et clôture du plan).
- Le PEA est plafonné en versements (params.pea_ceiling, 150 000 € par défaut) : une fois
  le plafond atteint, les versements suivants sont placés sur un CTO (voir engine.py).
- L'impôt est calculé comme si l'on liquidait chaque compte à la date considérée, sur sa
  plus-value (valeur - versements). Pas d'impôt si moins-value, et pas de compensation
  entre les deux comptes.
"""

from __future__ import annotations

import numpy as np

PEA_HOLDING_MONTHS = 60  # ancienneté à partir de laquelle l'impôt sur le revenu disparaît


def tax_series(
    regime: str,
    gains: np.ndarray,
    months: np.ndarray,
    income_tax_pct: float,
    social_levy_pct: float,
) -> np.ndarray:
    """Impôt dû si l'on sortait à chaque mois d'un compte ("pea" ou "cto"), pour ses plus-values."""
    taxable = np.maximum(gains, 0.0)
    full_rate = (income_tax_pct + social_levy_pct) / 100
    if regime == "cto":
        rate = np.full_like(taxable, full_rate)
    elif regime == "pea":
        rate = np.where(months >= PEA_HOLDING_MONTHS, social_levy_pct / 100, full_rate)
    else:
        rate = np.zeros_like(taxable)
    return taxable * rate
