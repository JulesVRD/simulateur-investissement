"""Onglet Salaire et épargne : trois trajectoires de salaire et leur effet sur le capital."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from simulator import SimulationParams, simulate, summarize
from simulator.charts import SCENARIO_SLOT, SLOT_CUSTOM_SALARY, breakdown_chart, lines_chart
from simulator.formatting import eur, multiplier, pct
from simulator.salary import RATE_FIELDS, matches_preset, salary_frame, scenario_variants
from simulator.salary_profiles import PHASE_LABELS, PROFILES, SCENARIO_DESCRIPTIONS, SCENARIOS

from .theme import DISCLAIMER, PLOT_CONFIG, is_dark

VIEWS = {"salary": "Salaire net mensuel", "monthly_invested": "Versement mensuel", "capital": "Capital accumulé"}
CUSTOM = "Votre réglage"
CODE_OF_LABEL = {label: code for code, label in SCENARIOS.items()}


def _trajectories(params: SimulationParams, custom: bool) -> dict[str, SimulationParams]:
    """Les trois scénarios du profil, plus « Votre réglage » si les augmentations ont été modifiées."""
    variants = {SCENARIOS[code]: variant for code, variant in scenario_variants(params).items()}
    if custom:
        variants[CUSTOM] = params
    return variants


def _assumptions(trajectories: dict[str, SimulationParams], selected: str, years: float) -> None:
    rows = []
    for label, variant in trajectories.items():
        rows.append(
            {
                "Scénario": label,
                **{phase: pct(getattr(variant, field)) for phase, field in zip(PHASE_LABELS, RATE_FIELDS)},
                f"Salaire après {years:g} ans": eur(salary_frame(variant)["salary"].iloc[-1]),
                "Choisi": "oui" if label == selected else "",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Augmentations annuelles nominales (inflation comprise), accordées une fois par an, à chaque anniversaire.")


def _kpis(params: SimulationParams) -> None:
    frame = salary_frame(params)
    cards = [
        ("Salaire au départ", eur(frame["salary"].iloc[0]), "Salaire net mensuel du premier mois."),
        ("Salaire à la fin", eur(frame["salary"].iloc[-1]), "Salaire net mensuel du dernier mois simulé."),
        ("Versement au départ", eur(frame["monthly_invested"].iloc[0]), f"Versement mensuel : {pct(params.salary_share_pct)} du salaire."),
        ("Versement à la fin", eur(frame["monthly_invested"].iloc[-1]), "Versement mensuel du dernier mois : il suit votre salaire."),
    ]
    for column, (label, value, help_text) in zip(st.columns(4), cards):
        column.metric(label, value, help=help_text, border=True)


def _results_table(trajectories: dict[str, SimulationParams], summaries: dict) -> pd.DataFrame:
    rows = []
    for label, variant in trajectories.items():
        s = summaries[label]
        rows.append(
            {
                "Scénario": label,
                "Salaire à la fin": eur(salary_frame(variant)["salary"].iloc[-1]),
                "Total investi": eur(s.invested),
                "Intérêts": eur(s.interest),
                "Capital final": eur(s.total),
                "Net après impôt": eur(s.net),
                "Multiplicateur": multiplier(s.multiplier) if s.multiplier is not None else "—",
            }
        )
    return pd.DataFrame(rows)


def render(params: SimulationParams) -> None:
    st.subheader("Salaire et épargne")
    if params.contribution_mode != "salary":
        st.info(
            "Choisissez **« % de mon salaire »** dans « Mode de versement » (panneau de gauche) pour investir une "
            "part de votre salaire et voir comment il évolue selon trois trajectoires de carrière."
        )
        return

    dark = is_dark()
    custom = not matches_preset(params)
    selected = CUSTOM if custom else SCENARIOS[params.salary_scenario]
    profile = PROFILES[params.salary_profile]
    unit = "euros constants" if params.real_terms else "euros courants"
    st.write(
        f"Vous investissez **{pct(params.salary_share_pct)}** de votre salaire net chaque mois. "
        f"Profil : **{profile.label}**, salaire de départ {eur(params.salary_monthly)} net par mois. "
        f"Montants en {unit}."
    )
    st.caption(profile.basis)
    if params.real_terms:
        st.caption("En euros constants, un salaire qui suit l'inflation apparaît plat : son pouvoir d'achat ne change pas.")

    trajectories = _trajectories(params, custom)
    st.markdown("**Les trois trajectoires**")
    _assumptions(trajectories, selected, params.years)
    if custom:
        st.info("Vous avez modifié les augmentations : votre réglage est tracé en pointillés à côté des trois scénarios.")
    else:
        st.caption(f"Scénario choisi : **{selected}**. {SCENARIO_DESCRIPTIONS[params.salary_scenario]}")

    _kpis(params)

    view = st.radio("Afficher", list(VIEWS), format_func=VIEWS.get, horizontal=True, key="salary_view")
    unit_symbol = "€ constants" if params.real_terms else "€"
    if view == "capital":
        frames = {label: simulate(variant) for label, variant in trajectories.items()}
        column, y_title = "total", f"Capital accumulé avant impôt ({unit_symbol})"
    else:
        frames = {label: salary_frame(variant) for label, variant in trajectories.items()}
        column, y_title = view, f"{VIEWS[view]} ({unit_symbol})"
    slots = [SCENARIO_SLOT[CODE_OF_LABEL[label]] if label in CODE_OF_LABEL else SLOT_CUSTOM_SALARY for label in frames]
    st.plotly_chart(
        lines_chart(frames, column, y_title, slots=slots, dashed=[CUSTOM], thick=[selected], dark=dark),
        width="stretch", key="salary_chart", config=PLOT_CONFIG,
    )

    st.markdown("**Ce que ça change sur votre capital**")
    summaries = {label: summarize(simulate(variant)) for label, variant in trajectories.items()}
    st.dataframe(_results_table(trajectories, summaries), hide_index=True, width="stretch")
    low, high = summaries[SCENARIOS["low"]], summaries[SCENARIOS["high"]]
    if low.total > 0:
        st.success(
            f"Entre le scénario le moins et le plus favorable, votre capital final varie de {eur(low.total)} à "
            f"{eur(high.total)} ({multiplier(high.total / low.total)}) : c'est l'effet cumulé des augmentations sur "
            f"{params.years:g} ans."
        )
    st.plotly_chart(breakdown_chart(summaries, dark=dark), width="stretch", key="salary_breakdown", config=PLOT_CONFIG)
    st.caption(
        "Valeurs indicatives : votre carrière réelle dépendra de votre secteur, de votre employeur et de vos choix. "
        "Les trajectoires sont modifiables dans « Ajuster les augmentations de salaire »."
    )
    st.caption(DISCLAIMER)
