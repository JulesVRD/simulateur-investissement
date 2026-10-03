"""Onglet Comparaison : plusieurs scénarios (enregistrés ou en cours) côte à côte."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from simulator import SimulationParams, TAX_REGIMES, simulate, storage, summarize
from simulator.charts import COMPARE_METRICS, breakdown_chart, comparison_chart
from simulator.formatting import eur, multiplier, pct

from .theme import DISCLAIMER, PLOT_CONFIG, is_dark

CURRENT = "Scénario en cours"
MAX_SAVED = 5
UNITS = {"own": "Selon chaque scénario", "nominal": "Euros courants", "real": "Euros constants"}


def _collect(params: SimulationParams, names: list[str], include_current: bool) -> dict[str, SimulationParams]:
    scenarios: dict[str, SimulationParams] = {CURRENT: params} if include_current else {}
    for name in names:
        try:
            scenarios[name if name not in scenarios else f"{name} (enregistré)"] = storage.load(name)
        except ValueError as error:
            st.warning(str(error))
    return scenarios


def _table(scenarios: dict[str, SimulationParams], summaries: dict) -> pd.DataFrame:
    rows = []
    for name, p in scenarios.items():
        s = summaries[name]
        rows.append(
            {
                "Scénario": name,
                "Capital de départ": eur(p.initial_capital),
                "Versement mensuel": (
                    f"{pct(p.salary_share_pct)} de {eur(p.salary_monthly)}"
                    if p.contribution_mode == "salary"
                    else eur(p.monthly_contribution)
                ),
                "Durée": f"{p.years:g} ans",
                "Rendement": pct(p.annual_return_pct),
                "Frais": pct(p.annual_fees_pct, 2),
                "Fiscalité": TAX_REGIMES[p.tax_regime].split(" (")[0],
                "Total investi": eur(s.invested),
                "Intérêts": eur(s.interest),
                "Capital final": eur(s.total),
                "Net après impôt": eur(s.net),
                "Multiplicateur": multiplier(s.multiplier) if s.multiplier is not None else "—",
            }
        )
    return pd.DataFrame(rows)


def render(params: SimulationParams) -> None:
    dark = is_dark()
    st.subheader("Comparaison de scénarios")
    saved = [info.name for info in storage.list_scenarios()]
    st.session_state["cmp_choices"] = [n for n in st.session_state["cmp_choices"] if n in saved]

    left, right = st.columns([3, 2])
    chosen = left.multiselect(
        "Scénarios enregistrés à comparer", saved, max_selections=MAX_SAVED, key="cmp_choices",
        placeholder="Choisir un ou plusieurs scénarios…",
    )
    include_current = right.checkbox("Inclure le scénario en cours (panneau de gauche)", key="cmp_current")
    unit = st.radio("Unité des montants", list(UNITS), format_func=UNITS.get, horizontal=True, key="cmp_unit")

    scenarios = _collect(params, chosen, include_current)
    if unit != "own":
        scenarios = {name: p.with_(real_terms=unit == "real") for name, p in scenarios.items()}
    if len(scenarios) < 2:
        st.info(
            "Sélectionnez au moins deux scénarios. Pour en créer : réglez les paramètres à gauche, "
            "donnez un nom au scénario puis cliquez sur « Enregistrer » ; modifiez ensuite un paramètre et "
            "enregistrez sous un autre nom."
        )
        return

    frames = {name: simulate(p) for name, p in scenarios.items()}
    summaries = {name: summarize(df) for name, df in frames.items()}
    real_terms = unit == "real" or (unit == "own" and all(p.real_terms for p in scenarios.values()))

    best = max(summaries, key=lambda name: summaries[name].net)
    st.success(f"Meilleur résultat net : **{best}** avec {eur(summaries[best].net)} après impôt.")

    metric = st.radio(
        "Grandeur comparée", list(COMPARE_METRICS), format_func=COMPARE_METRICS.get, horizontal=True, key="cmp_metric"
    )
    st.plotly_chart(
        comparison_chart(frames, metric, dark=dark, real_terms=real_terms), width="stretch", key="cmp_chart",
        config=PLOT_CONFIG,
    )
    st.dataframe(_table(scenarios, summaries), hide_index=True, width="stretch")
    st.markdown("**Répartition du capital final**")
    st.plotly_chart(breakdown_chart(summaries, dark=dark), width="stretch", key="cmp_breakdown", config=PLOT_CONFIG)
    if unit == "own" and len({p.real_terms for p in scenarios.values()}) > 1:
        st.warning("Certains scénarios sont en euros constants et d'autres en euros courants : choisissez une unité commune.")
    st.caption(DISCLAIMER)
