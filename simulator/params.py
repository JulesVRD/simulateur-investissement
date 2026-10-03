"""Paramètres d'une simulation : valeurs par défaut, bornes et validation.

Les taux sont exprimés en pourcentage (7.0 = 7 %) pour rester lisibles dans les
fichiers de scénarios sauvegardés.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any

from .salary_profiles import DEFAULT_PROFILE, DEFAULT_SCENARIO, PROFILES, SCENARIOS, preset_rates

TAX_REGIMES = {
    "none": "Aucune (montants bruts)",
    "pea": "PEA",
    "cto": "Compte-titres (CTO)",
}

CONTRIBUTION_MODES = {
    "fixed": "Montant fixe",
    "salary": "% de mon salaire",
}

_EARLY, _MID, _LATE = preset_rates(DEFAULT_PROFILE, DEFAULT_SCENARIO)

# Bornes uniques : utilisées par la validation ET par les widgets de l'interface.
BOUNDS: dict[str, tuple[float, float]] = {
    "initial_capital": (0.0, 10_000_000.0),
    "monthly_contribution": (0.0, 1_000_000.0),
    "years": (1, 60),
    "annual_return_pct": (-10.0, 30.0),
    "contribution_growth_pct": (0.0, 20.0),
    "annual_fees_pct": (0.0, 5.0),
    "inflation_pct": (0.0, 15.0),
    "income_tax_pct": (0.0, 50.0),
    "social_levy_pct": (0.0, 50.0),
    "pea_ceiling": (0.0, 1_000_000.0),
    "salary_monthly": (0.0, 100_000.0),
    "salary_share_pct": (0.0, 50.0),
    "salary_growth_early_pct": (0.0, 15.0),
    "salary_growth_mid_pct": (0.0, 15.0),
    "salary_growth_late_pct": (0.0, 15.0),
}

LABELS = {
    "initial_capital": "Capital de départ",
    "monthly_contribution": "Versement mensuel",
    "years": "Durée",
    "annual_return_pct": "Rendement annuel",
    "contribution_growth_pct": "Hausse annuelle des versements",
    "annual_fees_pct": "Frais annuels",
    "inflation_pct": "Inflation",
    "real_terms": "Euros constants",
    "tax_regime": "Enveloppe fiscale",
    "compare_taxes": "Comparer PEA et CTO",
    "income_tax_pct": "Impôt sur le revenu (gains)",
    "social_levy_pct": "Prélèvements sociaux",
    "pea_ceiling": "Plafond de versements du PEA",
    "contribution_mode": "Mode de versement",
    "salary_monthly": "Salaire net mensuel de départ",
    "salary_share_pct": "Part du salaire investie",
    "salary_profile": "Profil de salaire",
    "salary_scenario": "Scénario d'évolution du salaire",
    "salary_growth_early_pct": "Augmentation annuelle (années 1 à 5)",
    "salary_growth_mid_pct": "Augmentation annuelle (années 6 à 15)",
    "salary_growth_late_pct": "Augmentation annuelle (année 16 et suivantes)",
}


@dataclass(frozen=True)
class SimulationParams:
    initial_capital: float = 10_000.0
    monthly_contribution: float = 300.0
    years: float = 20.0
    annual_return_pct: float = 7.0  # rendement brut, avant frais
    contribution_growth_pct: float = 0.0  # hausse du versement à chaque anniversaire
    annual_fees_pct: float = 0.0
    inflation_pct: float = 2.0
    real_terms: bool = False  # True : tout est converti en euros d'aujourd'hui
    tax_regime: str = "none"
    compare_taxes: bool = False  # affichage seulement : comparatif PEA / CTO
    income_tax_pct: float = 12.8
    social_levy_pct: float = 18.6
    pea_ceiling: float = 150_000.0  # versements cumulés maximum dans le PEA (le surplus va en CTO)
    # Mode "salary" : on investit un % du salaire, qui augmente selon une trajectoire de carrière.
    # Dans ce mode, monthly_contribution et contribution_growth_pct sont ignorés.
    contribution_mode: str = "fixed"
    salary_monthly: float = 2_600.0  # salaire net mensuel à l'embauche (€)
    salary_share_pct: float = 10.0  # part du salaire investie chaque mois
    salary_profile: str = DEFAULT_PROFILE  # profil choisi (informatif : les taux ci-dessous font foi)
    salary_scenario: str = DEFAULT_SCENARIO
    salary_growth_early_pct: float = _EARLY  # augmentation annuelle, années 1 à 5
    salary_growth_mid_pct: float = _MID  # années 6 à 15
    salary_growth_late_pct: float = _LATE  # année 16 et suivantes

    @property
    def months(self) -> int:
        return max(1, round(self.years * 12))

    def with_(self, **changes: Any) -> SimulationParams:
        return replace(self, **changes)

    def validate(self) -> list[str]:
        errors = []
        for name, (low, high) in BOUNDS.items():
            value = getattr(self, name)
            if not low <= value <= high:
                errors.append(f"« {LABELS[name]} » doit être compris entre {low:g} et {high:g}.")
        for name, allowed in (
            ("tax_regime", TAX_REGIMES),
            ("contribution_mode", CONTRIBUTION_MODES),
            ("salary_profile", PROFILES),
            ("salary_scenario", SCENARIOS),
        ):
            if getattr(self, name) not in allowed:
                errors.append(f"« {LABELS[name]} » inconnu : {getattr(self, name)!r}.")
        return errors

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if float(data["years"]).is_integer():
            data["years"] = int(data["years"])
        return data

    @classmethod
    def from_dict(cls, data: Any) -> SimulationParams:
        """Reconstruit des paramètres depuis un dict (fichier JSON).

        Les clés absentes prennent leur valeur par défaut, les clés inconnues
        sont ignorées (compatibilité entre versions). Lève ValueError si une
        valeur est invalide.
        """
        if not isinstance(data, dict):
            raise ValueError("Le contenu des paramètres est invalide.")
        defaults = cls()
        kwargs: dict[str, Any] = {}
        for field in fields(cls):
            if field.name not in data:
                continue
            raw, default = data[field.name], getattr(defaults, field.name)
            label = LABELS[field.name]
            if isinstance(default, bool):
                if not isinstance(raw, bool):
                    raise ValueError(f"Valeur invalide pour « {label} ».")
                kwargs[field.name] = raw
            elif isinstance(default, str):
                kwargs[field.name] = str(raw)
            else:
                try:
                    kwargs[field.name] = float(raw)
                except (TypeError, ValueError):
                    raise ValueError(f"Valeur invalide pour « {label} ».") from None
        params = cls(**kwargs)
        errors = params.validate()
        if errors:
            raise ValueError(" ".join(errors))
        return params
