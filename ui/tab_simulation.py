"""Onglet Simulation : indicateurs, graphique principal, comparatif PEA / CTO, tableau."""

from __future__ import annotations

import streamlit as st

from simulator import Summary, SimulationParams, TAX_REGIMES, simulate, summarize
from simulator.charts import REGIME_SLOT, breakdown_chart, evolution_chart
from simulator.export import table_to_csv
from simulator.formatting import duration, eur, multiplier, pct
from simulator.metrics import pea_full_month, yearly_table
from simulator.salary import matches_preset, salary_frame
from simulator.salary_profiles import PROFILES, SCENARIOS
from simulator.taxes import PEA_HOLDING_MONTHS

from .theme import DISCLAIMER, PLOT_CONFIG, is_dark

CHART_MODES = {"stacked": "Empilé", "lines": "Lignes superposées"}


def _contribution_caption(params: SimulationParams) -> str:
    if params.contribution_mode != "salary":
        return ""
    scenario = SCENARIOS[params.salary_scenario] if matches_preset(params) else "réglage personnalisé"
    return (
        f" Versements : {pct(params.salary_share_pct)} d'un salaire net de {eur(params.salary_monthly)}/mois au départ, "
        f"qui évolue selon le scénario « {scenario} » ({PROFILES[params.salary_profile].label})."
    )


def _uses_pea(params: SimulationParams) -> bool:
    return params.tax_regime == "pea" or params.compare_taxes


def _notices(params: SimulationParams) -> None:
    if _uses_pea(params):
        month = pea_full_month(params)
        if month is not None:
            when = "dès le départ" if month == 0 else f"au bout de {duration(month)}"
            st.info(
                f"**Le PEA est plein {when}** (plafond de versements : {eur(params.pea_ceiling)}). "
                "Au-delà, les nouveaux versements sont placés sur un compte-titres, "
                f"taxé à {pct(params.income_tax_pct + params.social_levy_pct)} sur ses gains."
            )
        if params.years * 12 < PEA_HOLDING_MONTHS:
            st.info(
                "Avant 5 ans, un retrait du PEA est taxé comme un compte-titres (et clôture le plan) : "
                "l'avantage fiscal du PEA n'apparaît qu'au-delà de 5 ans."
            )


def _kpis(params: SimulationParams, s: Summary) -> None:
    share = f"{s.interest / s.total * 100:.0f} % du capital final" if s.total > 0 else None
    cards = [
        ("Capital final", eur(s.total), "Valeur du portefeuille à la fin, avant impôt.", None),
        ("Total investi", eur(s.invested), "Capital de départ + tous les versements.", None),
        ("Intérêts gagnés", eur(s.interest), "Gains cumulés, nets de frais.", share),
        (
            "Multiplicateur",
            multiplier(s.multiplier) if s.multiplier is not None else "—",
            "Capital final ÷ total investi : chaque euro investi en vaut combien à la fin.",
            None,
        ),
    ]
    extra = []
    if params.tax_regime != "none":
        label = TAX_REGIMES[params.tax_regime]
        extra += [
            (f"Impôt à la sortie ({label})", eur(s.tax), "Impôt si vous retiriez tout à la fin.", None),
            ("Net après impôt", eur(s.net), "Ce qu'il vous reste après impôt.", None),
        ]
    if params.tax_regime == "pea" and s.cto_invested > 0:
        extra.append(
            (
                "Dont surplus sur compte-titres",
                eur(s.cto_total),
                f"Valeur finale des {eur(s.cto_invested)} versés au-delà du plafond du PEA.",
                None,
            )
        )
    if params.contribution_mode == "salary":
        frame = salary_frame(params)
        extra += [
            ("Salaire final", eur(frame["salary"].iloc[-1]), "Salaire net mensuel du dernier mois simulé.", None),
            ("Versement final", eur(frame["monthly_invested"].iloc[-1]), "Versement mensuel du dernier mois : la part de votre salaire investie.", None),
        ]
    if s.fees > 0:
        extra.append(("Frais cumulés", eur(s.fees), "Total des frais annuels prélevés sur la période.", None))
    for start in range(0, len(cards + extra), 4):  # quatre cartes par ligne
        for column, (label, value, help_text, delta) in zip(st.columns(4), (cards + extra)[start:start + 4]):
            column.metric(
                label, value, delta=delta, delta_color="off", delta_arrow="off", help=help_text, border=True
            )


def _milestones(s: Summary) -> None:
    lines = []
    if s.interest_over_contribution_month is not None:
        lines.append(
            f"**Effet boule de neige** : à partir de {duration(s.interest_over_contribution_month)}, "
            "les intérêts gagnés en un mois dépassent votre versement mensuel."
        )
    if s.interest_over_invested_month is not None:
        lines.append(
            f"**Les intérêts dépassent ce que vous avez investi** à partir de {duration(s.interest_over_invested_month)}."
        )
    if lines:
        st.info("\n\n".join(lines))


def _net_lines(params: SimulationParams, df) -> list:
    if params.compare_taxes:
        return [
            (f"Net après impôt ({TAX_REGIMES[regime]})", simulate(params.with_(tax_regime=regime))["net"], REGIME_SLOT[regime])
            for regime in ("pea", "cto")
        ]
    if params.tax_regime != "none":
        return [(f"Net après impôt ({TAX_REGIMES[params.tax_regime]})", df["net"], REGIME_SLOT[params.tax_regime])]
    return []


def _tax_comparison(params: SimulationParams, dark: bool) -> None:
    st.subheader("PEA ou compte-titres ?")
    pea = summarize(simulate(params.with_(tax_regime="pea")))
    cto = summarize(simulate(params.with_(tax_regime="cto")))
    columns = st.columns(2)
    for column, name, s in zip(columns, ("PEA", "Compte-titres (CTO)"), (pea, cto)):
        column.metric(f"{name} : net après impôt", eur(s.net), border=True)
        column.metric(f"{name} : impôt à la sortie", eur(s.tax), border=True)
    if pea.cto_invested > 0:
        columns[0].caption(
            f"PEA plafonné à {eur(params.pea_ceiling)} de versements : {eur(pea.cto_invested)} placés sur "
            f"compte-titres, dont l'impôt ({eur(pea.cto_tax)}) est inclus ci-dessus."
        )

    gap = pea.net - cto.net
    if abs(gap) < 1:
        st.info("Sur cette durée, les deux enveloppes sont équivalentes (le PEA ne devient avantageux qu'après 5 ans).")
    else:
        winner = "Le PEA" if gap > 0 else "Le compte-titres"
        st.success(f"{winner} vous laisse **{eur(abs(gap))}** de plus après impôt.")
    st.plotly_chart(
        breakdown_chart({"PEA": pea, "Compte-titres (CTO)": cto}, dark=dark), width="stretch", key="tax_breakdown",
        config=PLOT_CONFIG,
    )
    full = params.income_tax_pct + params.social_levy_pct
    st.caption(
        f"Hypothèses : compte-titres taxé à {pct(full)} sur les gains (flat tax) ; PEA de plus de 5 ans taxé à "
        f"{pct(params.social_levy_pct)} (prélèvements sociaux seulement), avant 5 ans comme le compte-titres. "
        f"Le PEA accepte {eur(params.pea_ceiling)} de versements au maximum, le surplus va en compte-titres. "
        "Rendement et frais identiques dans les deux enveloppes (le PEA impose des actions européennes). "
        "Taux et plafond modifiables dans « Fiscalité »."
    )


def _table(params: SimulationParams, df) -> None:
    with st.expander("Tableau année par année"):
        table = yearly_table(
            df,
            with_fees=params.annual_fees_pct > 0,
            with_tax=params.tax_regime != "none",
            with_split=params.tax_regime == "pea" and df["cto_invested"].iloc[-1] > 0,
        )
        shown = table.copy()
        for column in shown.columns[1:]:
            shown[column] = shown[column].map(eur)
        st.dataframe(shown, hide_index=True, width="stretch")
        st.download_button("Télécharger en CSV", table_to_csv(table), "simulation.csv", "text/csv")


def render(params: SimulationParams) -> None:
    dark = is_dark()
    df = simulate(params)
    s = summarize(df)

    unit = "en euros constants (pouvoir d'achat d'aujourd'hui)" if params.real_terms else "en euros courants"
    st.caption(f"Montants {unit}. Modifiez les paramètres dans le panneau de gauche.{_contribution_caption(params)}")
    _notices(params)
    _kpis(params, s)
    _milestones(s)

    mode = st.radio(
        "Affichage", list(CHART_MODES), format_func=CHART_MODES.get, horizontal=True, key="chart_mode",
        label_visibility="collapsed",
    )
    full_month = pea_full_month(params) if _uses_pea(params) else None
    st.plotly_chart(
        evolution_chart(
            df, mode=mode, dark=dark, net_lines=_net_lines(params, df), real_terms=params.real_terms,
            pea_full_year=full_month / 12 if full_month else None,
        ),
        width="stretch", key="evolution", config=PLOT_CONFIG,
    )
    if params.compare_taxes:
        _tax_comparison(params, dark)
    _table(params, df)
    st.caption(DISCLAIMER)
