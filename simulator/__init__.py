"""Simulateur d'investissement : moteur de calcul, objectif inversé et sauvegarde."""

from .engine import simulate
from .metrics import Summary, summarize
from .params import TAX_REGIMES, SimulationParams

__all__ = ["SimulationParams", "Summary", "TAX_REGIMES", "simulate", "summarize"]
