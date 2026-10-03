"""Onglet Objectif inversé : quel effort d'épargne, quelle durée ou quel rendement pour atteindre un capital ?"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from simulator import SimulationParams, TAX_REGIMES, simulate, summarize
from simulator.charts import REGIME_SLOT, evolution_chart
from simulator.formatting import duration, eur, pct
from simulator.solver import SolveResult, effort_by_years, solve_duration, solve_effort, solve_return

from .theme import DISCLAIMER, PLOT_CONFIG, is_dark

# « contribution » désigne l'effort d'épargne : versement mensuel (mode fixe) ou part du salaire (mode salaire).
GOAL_MODES = {"contribution": "Le versement mensuel", "duration": "La durée", "return": "Le rendement annuel"}
SALARY_GOAL_MODES = {**GOAL_MODES, "contribution": "La part de salaire à investir"}
IGNORED = {
    "contribution": "le versement mensuel",
    "duration": "la durée",
    "return": "le rendement annuel",
}
SALARY_IGNORED = {**IGNORED, "contribution": "la part du salaire investie"}
BASES = {"gross": "brut (avant impôt)", "net": "net (après impôt)"}
SENSITIVITY_YEARS = (5, 10, 15, 20, 25, 30, 35, 40)
AMBITIOUS_RETURN_PCT = 10.0


def _starting_contribution(params: SimulationParams) -> float:
    """Versement du premier mois."""
    if params.contribution_mode == "salary":
        return params.salary_share_pct / 100 * params.salary_monthly
    return params.monthly_contribution


@st.cache_data(show_spinner=False)
def _sensitivity(params: SimulationParams, target: float, basis: str) -> pd.DataFrame:
    salary_mode = params.contribution_mode == "salary"
    years_list = sorted({*SENSITIVITY_YEARS, int(params.years)})
    rows = []
    for years, result in effort_by_years(params, target, basis, years_list):
        if not result.reachable:
            continue
        s = summarize(simulate(result.params))
        start = _starting_contribution(result.params)
        row = {"Durée": f"{years} ans"}
        if salary_mode:
            row["Part du salaire requise"] = pct(result.value, 1)
            row["Versement mensuel de départ"] = eur(start, 2 if start < 100 else 0)
        else:
            row["Versement mensuel requis"] = eur(result.value, 2 if result.value < 100 else 0)
        row["Total investi"] = eur(s.invested)
        row["Part des intérêts"] = pct(s.interest / s.total * 100, 0) if s.total > 0 else "—"
        rows.append(row)
    return pd.DataFrame(rows)


def _solve(mode: str, params: SimulationParams, target: float, basis: str) -> SolveResult:
    if mode == "contribution":
        return solve_effort(params, target, basis)
    if mode == "duration":
        return solve_duration(params, target, basis)
    return solve_return(params, target, basis)


def _headline(mode: str, params: SimulationParams, result: SolveResult) -> tuple[str, str]:
    if mode == "contribution":
        if params.contribution_mode == "salary":
            return "Part du salaire à investir", pct(result.value, 2) + " du salaire"
        return "Versement mensuel requis", eur(result.value, 2 if result.value < 100 else 0) + " / mois"
    if mode == "duration":
        return "Durée nécessaire", duration(int(result.value)) if result.value else "0 mois"
    return "Rendement annuel brut requis", pct(result.value, 2) + " / an"


def render(params: SimulationParams) -> None:
    dark = is_dark()
    salary_mode = params.contribution_mode == "salary"
    modes = SALARY_GOAL_MODES if salary_mode else GOAL_MODES
    st.subheader("Objectif inversé")
    st.write(
        "Fixez un capital à atteindre : le simulateur calcule ce qu'il faut pour y arriver, "
        "à partir des autres paramètres du panneau de gauche."
    )
    mode = st.radio("Je cherche…", list(modes), format_func=modes.get, horizontal=True, key="goal_mode")
    left, right = st.columns(2)
    target = left.number_input(
        "Capital à atteindre (€)", min_value=1_000.0, max_value=100_000_000.0, step=5_000.0, format="%.0f",
        key="goal_target",
    )
    basis = right.radio("Ce capital est…", list(BASES), format_func=BASES.get, horizontal=True, key="goal_basis")
    if basis == "net" and params.tax_regime == "none":
        st.caption("Aucune enveloppe fiscale n'est choisie (panneau « Fiscalité ») : net et brut sont identiques.")
    if params.real_terms:
        st.caption("Le capital visé est exprimé en euros constants (pouvoir d'achat d'aujourd'hui).")
    ignored = (SALARY_IGNORED if salary_mode else IGNORED)[mode]
    st.caption(f"Pour cette question, {ignored} du panneau de gauche est ignoré : c'est ce qui est calculé.")

    result = _solve(mode, params, target, basis)
    if not result.reachable:
        st.warning(result.message)
        return
    if result.message:
        st.info(result.message)

    solved = result.params
    s = summarize(simulate(solved))
    label, value = _headline(mode, params, result)
    cards = [(label, value)]
    if salary_mode:
        cards.append(("Versement mensuel au départ", eur(_starting_contribution(solved), 2)))
    cards += [
        ("Total investi", eur(s.invested)),
        ("Dont intérêts", f"{eur(s.interest)} ({s.interest / s.total * 100:.0f} %)" if s.total > 0 else "—"),
    ]
    for column, (title, text) in zip(st.columns(len(cards)), cards):
        column.metric(title, text, border=True)
    if mode == "return" and result.value > AMBITIOUS_RETURN_PCT:
        st.warning(
            f"Un rendement durablement supérieur à {pct(AMBITIOUS_RETURN_PCT, 0)} par an est très ambitieux, "
            "et suppose de prendre un risque élevé. Essayez plutôt d'allonger la durée ou d'augmenter les versements."
        )

    df = simulate(solved)
    net_lines = []
    if basis == "net" and params.tax_regime != "none":
        net_lines = [(f"Net après impôt ({TAX_REGIMES[params.tax_regime]})", df["net"], REGIME_SLOT[params.tax_regime])]
    st.plotly_chart(
        evolution_chart(df, dark=dark, net_lines=net_lines, target=target, real_terms=params.real_terms),
        width="stretch", key="goal_chart", config=PLOT_CONFIG,
    )

    if mode == "contribution":
        title = "Quelle part de salaire investir selon la durée ?" if salary_mode else "Combien verser selon la durée ?"
        with st.expander(title, expanded=True):
            st.dataframe(_sensitivity(params, target, basis), hide_index=True, width="stretch")
            st.caption("Plus la durée est longue, moins l'effort est important : les intérêts travaillent plus longtemps.")
    st.caption(DISCLAIMER)
