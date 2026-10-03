"""Profils de salaire : salaire de départ et trajectoires d'augmentation (données pures).

Les augmentations sont NOMINALES (inflation comprise), en % par an, et dépendent de la phase de carrière :
- phase 1 : années 1 à 5 (promotions rapides en début de carrière) ;
- phase 2 : années 6 à 15 ;
- phase 3 : année 16 et suivantes (la progression ralentit).
Le salaire augmente une fois par an, à chaque anniversaire.

Trois scénarios par profil : peu favorable, moyenne, très favorable. Ce sont des hypothèses
INDICATIVES. Les ingénieurs sont calibrés sur des données publiques (voir `basis`), les autres profils
sont des extrapolations plus prudentes. Tout est modifiable dans l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass

EARLY_END = 5  # dernière année de la phase 1
MID_END = 15  # dernière année de la phase 2

PHASE_LABELS = ("Années 1 à 5", "Années 6 à 15", "Année 16 et suivantes")

SCENARIOS = {"low": "Peu favorable", "mid": "Moyenne", "high": "Très favorable"}
SCENARIO_DESCRIPTIONS = {
    "low": "Peu de promotions, peu de mobilité : essentiellement les augmentations générales, proches de l'inflation.",
    "mid": "Augmentations générales et promotions habituelles : trajectoire proche de la médiane des carrières.",
    "high": "Promotions rapides, changements d'employeur ou de poste, passage à des fonctions de management.",
}


@dataclass(frozen=True)
class SalaryProfile:
    label: str
    start_net_monthly: float  # salaire net mensuel à l'embauche, hors primes variables (€)
    growth: dict[str, tuple[float, float, float]]  # scénario -> (phase 1, phase 2, phase 3), en % par an
    basis: str  # origine des chiffres, affichée dans l'interface


PROFILES: dict[str, SalaryProfile] = {
    "engineer": SalaryProfile(
        label="Ingénieur (diplôme d'école d'ingénieurs)",
        start_net_monthly=2_600.0,
        growth={"low": (2.5, 1.8, 1.0), "mid": (3.5, 3.2, 2.2), "high": (5.5, 4.0, 2.5)},
        basis=(
            "Embauche : environ 39 800 € brut/an hors primes (ingénieurs UTT promotion 2024 ; "
            "39 100 € pour l'ensemble des ingénieurs, enquête CGE 2025), soit environ 2 600 € net/mois. "
            "Progression « moyenne » calée sur les salaires médians par tranche d'âge de l'enquête IESF 2025."
        ),
    ),
    "master": SalaryProfile(
        label="Master universitaire (bac+5)",
        start_net_monthly=2_100.0,
        growth={"low": (2.3, 1.6, 1.0), "mid": (3.2, 2.7, 1.9), "high": (5.0, 3.6, 2.2)},
        basis=(
            "Embauche : environ 2 100 à 2 170 € net/mois (salaire médian 18 à 30 mois après le diplôme, "
            "enquêtes SIES). Progression extrapolée à partir de celle des ingénieurs, moins documentée."
        ),
    ),
    "bachelor": SalaryProfile(
        label="Licence pro / BUT (bac+3)",
        start_net_monthly=1_750.0,
        growth={"low": (2.0, 1.5, 0.9), "mid": (2.8, 2.3, 1.6), "high": (4.5, 3.2, 1.9)},
        basis=(
            "Embauche : environ 1 600 à 1 800 € net/mois (salaire médian 30 mois après le diplôme, "
            "enquêtes SIES). Progression extrapolée, moins documentée."
        ),
    ),
    "custom": SalaryProfile(
        label="Autre profil (valeurs génériques)",
        start_net_monthly=2_200.0,
        growth={"low": (2.3, 1.7, 1.0), "mid": (3.0, 2.5, 1.8), "high": (4.8, 3.5, 2.2)},
        basis="Valeurs génériques : à ajuster selon votre secteur, votre poste et votre ancienneté.",
    ),
}

DEFAULT_PROFILE = "engineer"
DEFAULT_SCENARIO = "mid"


def preset_rates(profile: str, scenario: str) -> tuple[float, float, float]:
    """Augmentations annuelles (phase 1, 2, 3) d'un profil pour un scénario."""
    return PROFILES[profile].growth[scenario]
