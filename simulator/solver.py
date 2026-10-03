"""Objectif inversé : trouver le paramètre qui permet d'atteindre un capital visé.

Trois questions possibles, toutes les autres valeurs étant fixées :
- quel versement mensuel ?  (dichotomie, le capital final croît avec le versement ;
                             en mode salaire : quelle part du salaire ?)
- quelle durée ?            (premier mois où le capital atteint l'objectif)
- quel rendement ?          (dichotomie, le capital final croît avec le rendement)

L'objectif peut porter sur le capital brut ("gross") ou net d'impôt ("net"),
dans l'unité choisie par params.real_terms (euros courants ou constants).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .engine import run
from .formatting import pct
from .params import BOUNDS, SimulationParams

_ITERATIONS = 80
RETURN_SEARCH_RANGE = (-20.0, 100.0)


@dataclass(frozen=True)
class SolveResult:
    reachable: bool
    value: float | None  # €/mois, durée en mois, ou rendement en %, selon la question
    params: SimulationParams | None  # scénario qui atteint l'objectif
    message: str


def _final(params: SimulationParams, basis: str) -> float:
    arrays = run(params)
    return float((arrays["net"] if basis == "net" else arrays["total"])[-1])


def _unreachable(message: str) -> SolveResult:
    return SolveResult(False, None, None, message)


def solve_contribution(params: SimulationParams, target: float, basis: str = "gross") -> SolveResult:
    def gap(contribution: float) -> float:
        return _final(params.with_(monthly_contribution=contribution), basis) - target

    if gap(0.0) >= 0:
        return SolveResult(
            True, 0.0, params.with_(monthly_contribution=0.0),
            "Votre capital de départ suffit : aucun versement mensuel n'est nécessaire.",
        )
    low, high = 0.0, max(100.0, params.monthly_contribution * 2)
    for _ in range(60):
        if gap(high) >= 0:
            break
        high *= 2
    else:
        return _unreachable("Objectif hors de portée avec ces paramètres.")
    for _ in range(_ITERATIONS):
        middle = (low + high) / 2
        low, high = (low, middle) if gap(middle) >= 0 else (middle, high)
    value = math.ceil(high * 100) / 100  # arrondi au centime supérieur : l'objectif est tenu
    return SolveResult(True, value, params.with_(monthly_contribution=value), "")


def solve_share(params: SimulationParams, target: float, basis: str = "gross") -> SolveResult:
    """Part du salaire à investir (mode "salary") ; la réponse est en % du salaire."""
    low, high = 0.0, BOUNDS["salary_share_pct"][1]

    def gap(share: float) -> float:
        return _final(params.with_(salary_share_pct=share), basis) - target

    if gap(low) >= 0:
        return SolveResult(
            True, 0.0, params.with_(salary_share_pct=0.0),
            "Votre capital de départ suffit : vous n'avez rien à prélever sur votre salaire.",
        )
    if gap(high) < 0:
        return _unreachable(f"Objectif hors de portée, même en investissant {pct(high, 0)} de votre salaire.")
    for _ in range(_ITERATIONS):
        middle = (low + high) / 2
        low, high = (low, middle) if gap(middle) >= 0 else (middle, high)
    value = math.ceil(high * 100) / 100  # arrondi au centième de point supérieur : l'objectif est tenu
    return SolveResult(True, value, params.with_(salary_share_pct=value), "")


def solve_effort(params: SimulationParams, target: float, basis: str = "gross") -> SolveResult:
    """Effort d'épargne nécessaire : versement mensuel (mode fixe, en €) ou part du salaire (mode salaire, en %)."""
    solver = solve_share if params.contribution_mode == "salary" else solve_contribution
    return solver(params, target, basis)


def solve_duration(params: SimulationParams, target: float, basis: str = "gross") -> SolveResult:
    horizon = int(BOUNDS["years"][1])
    arrays = run(params.with_(years=horizon))
    series = arrays["net"] if basis == "net" else arrays["total"]
    hits = np.flatnonzero(series >= target)
    if not len(hits):
        return _unreachable(f"Objectif non atteint en {horizon} ans avec ces paramètres.")
    months = int(hits[0])
    if months == 0:
        return SolveResult(True, 0.0, params, "Objectif déjà atteint dès le départ.")
    return SolveResult(True, float(months), params.with_(years=months / 12), "")


def solve_return(params: SimulationParams, target: float, basis: str = "gross") -> SolveResult:
    low, high = RETURN_SEARCH_RANGE

    def gap(rate: float) -> float:
        return _final(params.with_(annual_return_pct=rate), basis) - target

    if gap(high) < 0:
        return _unreachable(f"Objectif hors de portée, même avec {pct(high, 0)} par an.")
    if gap(low) >= 0:
        return SolveResult(True, low, params.with_(annual_return_pct=low), "")
    for _ in range(_ITERATIONS):
        middle = (low + high) / 2
        low, high = (low, middle) if gap(middle) >= 0 else (middle, high)
    value = math.ceil(high * 100) / 100
    return SolveResult(True, value, params.with_(annual_return_pct=value), "")


def effort_by_years(
    params: SimulationParams, target: float, basis: str, years_list: list[int]
) -> list[tuple[int, SolveResult]]:
    """Effort d'épargne requis (versement ou part du salaire) pour plusieurs durées : tableau de sensibilité."""
    return [(y, solve_effort(params.with_(years=y), target, basis)) for y in years_list]
