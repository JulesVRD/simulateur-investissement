"""Indicateurs de synthèse calculés à partir du résultat d'une simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import run
from .params import SimulationParams


@dataclass(frozen=True)
class Summary:
    years: float
    initial: float
    contributions: float
    invested: float  # capital de départ + versements
    interest: float  # intérêts cumulés, nets de frais
    total: float  # capital final avant impôt
    fees: float
    tax: float
    net: float  # capital final après impôt
    multiplier: float | None  # total / investi (None si rien n'est investi)
    interest_over_invested_month: int | None  # intérêts cumulés > total investi
    interest_over_contribution_month: int | None  # intérêts du mois > versement du mois
    pea_total: float  # valeur finale du PEA (0 hors enveloppe "pea")
    pea_invested: float
    pea_tax: float
    cto_total: float  # valeur finale du compte-titres (surplus du PEA, ou tout avec l'enveloppe "cto")
    cto_invested: float
    cto_tax: float


def _first_month(df: pd.DataFrame, mask: pd.Series) -> int | None:
    hits = np.flatnonzero(mask.to_numpy())
    return int(df["month"].iloc[hits[0]]) if len(hits) else None


def summarize(df: pd.DataFrame) -> Summary:
    last = df.iloc[-1]
    invested = float(last["invested"])
    if df["month_contribution"].max() > 0:
        snowball = _first_month(df, df["month_interest"] > df["month_contribution"])
    else:
        snowball = None
    return Summary(
        years=float(last["year"]),
        initial=float(last["initial"]),
        contributions=float(last["contributions"]),
        invested=invested,
        interest=float(last["interest"]),
        total=float(last["total"]),
        fees=float(last["fees"]),
        tax=float(last["tax"]),
        net=float(last["net"]),
        multiplier=float(last["total"]) / invested if invested > 0 else None,
        interest_over_invested_month=_first_month(df, df["interest"] > df["invested"]),
        interest_over_contribution_month=snowball,
        pea_total=float(last["pea_total"]),
        pea_invested=float(last["pea_invested"]),
        pea_tax=float(last["tax_pea"]),
        cto_total=float(last["cto_total"]),
        cto_invested=float(last["cto_invested"]),
        cto_tax=float(last["tax_cto"]),
    )


def yearly_table(
    df: pd.DataFrame, *, with_fees: bool = False, with_tax: bool = False, with_split: bool = False
) -> pd.DataFrame:
    """Tableau annuel (une ligne par anniversaire, plus la dernière ligne), en euros.

    with_split ajoute la valeur du PEA et celle du compte-titres (surplus du PEA).
    """
    keep = (df["month"] > 0) & ((df["month"] % 12 == 0) | (df["month"] == df["month"].max()))
    rows = df[keep]
    table = pd.DataFrame(
        {
            "Année": rows["year"].round(2).map(lambda y: int(y) if float(y).is_integer() else y),
            "Capital de départ": rows["initial"],
            "Versements cumulés": rows["contributions"],
            "Intérêts cumulés": rows["interest"],
            "Total": rows["total"],
        }
    )
    if with_split:
        table["Dont PEA"] = rows["pea_total"]
        table["Dont compte-titres"] = rows["cto_total"]
    if with_fees:
        table["Frais cumulés"] = rows["fees"]
    if with_tax:
        table["Impôt si retrait"] = rows["tax"]
        table["Net après impôt"] = rows["net"]
    return table.round(2).reset_index(drop=True)


def pea_full_month(params: SimulationParams) -> int | None:
    """Premier mois où le PEA atteint son plafond de versements (None s'il n'est jamais plein).

    Calculé comme si l'enveloppe était un PEA, quel que soit params.tax_regime : sert aussi au comparatif.
    """
    arrays = run(params.with_(tax_regime="pea", real_terms=False))
    hits = np.flatnonzero(arrays["pea_invested"] >= params.pea_ceiling - 1e-6)
    return int(hits[0]) if len(hits) else None
