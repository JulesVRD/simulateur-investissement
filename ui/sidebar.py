"""Barre latérale : paramètres de la simulation et gestion des scénarios."""

from __future__ import annotations

import streamlit as st

from simulator import storage
from simulator.params import BOUNDS, CONTRIBUTION_MODES, TAX_REGIMES
from simulator.salary import RATE_FIELDS, matches_preset
from simulator.salary_profiles import PHASE_LABELS, PROFILES, SCENARIOS, preset_rates

from .state import KEYS, flash, load_params_into_state, params_from_state, show_flash


def _save() -> None:
    name = st.session_state["save_name"]
    try:
        existed = storage.exists(name)
        storage.save(name, params_from_state())
    except ValueError as error:
        flash("error", str(error))
        return
    flash("success", f"Scénario « {storage.clean_name(name)} » {'mis à jour' if existed else 'enregistré'}.")


def _open() -> None:
    name = st.session_state["load_choice"]
    if not name:
        return
    try:
        load_params_into_state(storage.load(name))
    except ValueError as error:
        flash("error", str(error))
        return
    st.session_state["save_name"] = name
    flash("success", f"Scénario « {name} » ouvert.")


def _delete() -> None:
    name = st.session_state["load_choice"]
    if name:
        storage.delete(name)
        st.session_state["load_choice"] = None
        flash("info", f"Scénario « {name} » supprimé.")


def _import() -> None:
    uploaded = st.session_state.get("import_file")
    if uploaded is None:
        flash("info", "Choisissez d'abord un fichier .json.")
        return
    try:
        name, params = storage.from_json(uploaded.getvalue().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        flash("error", str(error))
        return
    load_params_into_state(params)
    st.session_state["save_name"] = name
    flash("success", f"Scénario « {name} » importé. Cliquez sur « Enregistrer » pour le garder.")


def _apply_scenario() -> None:
    """Remplit les trois augmentations avec celles du profil et du scénario choisis."""
    profile = st.session_state[KEYS["salary_profile"]]
    scenario = st.session_state[KEYS["salary_scenario"]]
    for field, rate in zip(RATE_FIELDS, preset_rates(profile, scenario)):
        st.session_state[KEYS[field]] = float(rate)


def _apply_profile() -> None:
    """Changer de profil remplit aussi le salaire de départ (modifiable ensuite)."""
    st.session_state[KEYS["salary_monthly"]] = float(PROFILES[st.session_state[KEYS["salary_profile"]]].start_net_monthly)
    _apply_scenario()


def _salary_inputs() -> None:
    st.selectbox(
        "Profil de salaire", list(PROFILES), format_func=lambda key: PROFILES[key].label,
        key=KEYS["salary_profile"], on_change=_apply_profile,
        help="Remplit le salaire de départ et les augmentations avec des valeurs indicatives pour ce diplôme. "
        "Tout reste modifiable ensuite.",
    )
    low, high = BOUNDS["salary_monthly"]
    st.number_input(
        "Salaire net mensuel de départ (€)", min_value=low, max_value=high, step=50.0, format="%.0f",
        key=KEYS["salary_monthly"],
        help="Net à payer avant impôt sur le revenu, hors primes variables. "
        "Pour un cadre : environ salaire brut annuel × 0,78 ÷ 12.",
    )
    low, high = BOUNDS["salary_share_pct"]
    st.slider(
        "Part du salaire investie chaque mois (%)", low, high, step=0.5, key=KEYS["salary_share_pct"],
        help="Pourcentage de votre salaire net placé chaque mois : il augmente avec votre salaire.",
    )
    st.radio(
        "Évolution de mon salaire", list(SCENARIOS), format_func=SCENARIOS.get, key=KEYS["salary_scenario"],
        on_change=_apply_scenario, help="Trois trajectoires de carrière : voir l'onglet « Salaire et épargne ».",
    )
    with st.expander("Ajuster les augmentations de salaire"):
        for field, label in zip(RATE_FIELDS, PHASE_LABELS):
            low, high = BOUNDS[field]
            st.slider(f"{label} (% par an)", low, high, step=0.1, key=KEYS[field])
        if not matches_preset(params_from_state()):
            st.caption("Réglage personnalisé : différent du scénario choisi.")


def _parameters() -> None:
    st.subheader("Paramètres")
    low, high = BOUNDS["initial_capital"]
    st.number_input(
        "Capital de départ (€)", min_value=low, max_value=high, step=1_000.0, format="%.0f",
        key=KEYS["initial_capital"], help="Somme investie dès le premier jour.",
    )
    st.radio(
        "Mode de versement", list(CONTRIBUTION_MODES), format_func=CONTRIBUTION_MODES.get, horizontal=True,
        key=KEYS["contribution_mode"],
        help="Montant fixe : la même somme chaque mois. % de mon salaire : vous investissez une part de votre "
        "salaire, qui augmente au fil de votre carrière.",
    )
    if st.session_state[KEYS["contribution_mode"]] == "salary":
        _salary_inputs()
    else:
        low, high = BOUNDS["monthly_contribution"]
        st.number_input(
            "Versement mensuel (€)", min_value=low, max_value=high, step=50.0, format="%.0f",
            key=KEYS["monthly_contribution"], help="Somme ajoutée chaque mois (en fin de mois).",
        )
    low, high = BOUNDS["years"]
    st.slider("Durée (années)", int(low), int(high), step=1, key=KEYS["years"])
    low, high = BOUNDS["annual_return_pct"]
    st.slider(
        "Rendement annuel brut (%)", low, high, step=0.1, key=KEYS["annual_return_pct"],
        help="Rendement moyen par an avant frais, supposé régulier. Il ne s'agit pas d'une garantie.",
    )

    with st.expander("Options avancées"):
        if st.session_state[KEYS["contribution_mode"]] == "fixed":
            low, high = BOUNDS["contribution_growth_pct"]
            st.slider(
                "Hausse annuelle des versements (%)", low, high, step=0.5, key=KEYS["contribution_growth_pct"],
                help="Le versement mensuel augmente de ce pourcentage à chaque anniversaire.",
            )
        else:
            st.caption("La hausse des versements suit votre salaire (voir « Évolution de mon salaire »).")
        low, high = BOUNDS["annual_fees_pct"]
        st.slider(
            "Frais annuels (%)", low, high, step=0.05, key=KEYS["annual_fees_pct"],
            help="Frais de gestion, de courtage ou de fonds, prélevés chaque année sur le capital.",
        )
        low, high = BOUNDS["inflation_pct"]
        st.slider("Inflation annuelle (%)", low, high, step=0.1, key=KEYS["inflation_pct"])
        st.checkbox(
            "Afficher en euros constants", key=KEYS["real_terms"],
            help="Convertit tous les montants en pouvoir d'achat d'aujourd'hui (divisés par l'inflation cumulée).",
        )

    with st.expander("Fiscalité"):
        st.selectbox(
            "Enveloppe fiscale", list(TAX_REGIMES), format_func=TAX_REGIMES.get, key=KEYS["tax_regime"],
            help="Impôt calculé comme si vous retiriez tout le capital à la date considérée.",
        )
        st.checkbox("Comparer PEA et compte-titres", key=KEYS["compare_taxes"])
        low, high = BOUNDS["pea_ceiling"]
        st.number_input(
            "Plafond de versements du PEA (€)", min_value=low, max_value=high, step=5_000.0, format="%.0f",
            key=KEYS["pea_ceiling"],
            help="150 000 € pour un PEA classique. Une fois ce total de versements atteint (capital de départ "
            "compris), le PEA n'accepte plus rien : les versements suivants sont placés sur un compte-titres.",
        )
        low, high = BOUNDS["income_tax_pct"]
        st.number_input(
            "Impôt sur le revenu sur les gains (%)", min_value=low, max_value=high, step=0.1, format="%.1f",
            key=KEYS["income_tax_pct"], help="Flat tax : 12,8 % (taux 2026).",
        )
        low, high = BOUNDS["social_levy_pct"]
        st.number_input(
            "Prélèvements sociaux (%)", min_value=low, max_value=high, step=0.1, format="%.1f",
            key=KEYS["social_levy_pct"], help="18,6 % depuis le 1er janvier 2026 (17,2 % auparavant).",
        )


def _scenarios() -> None:
    st.subheader("Scénarios")
    st.text_input("Nom du scénario", key="save_name", placeholder="Ex. Retraite 2050")
    st.button("Enregistrer", on_click=_save, width="stretch", type="primary")

    names = [info.name for info in storage.list_scenarios()]
    st.selectbox("Scénarios enregistrés", names, index=None, placeholder="Choisir un scénario…", key="load_choice")
    opened = st.session_state["load_choice"] is not None
    open_col, delete_col = st.columns(2)
    open_col.button("Ouvrir", on_click=_open, disabled=not opened, width="stretch")
    with delete_col.popover("Supprimer", disabled=not opened, width="stretch"):
        st.write(f"Supprimer définitivement « {st.session_state['load_choice']} » ?")
        st.button("Oui, supprimer", on_click=_delete, type="primary")

    with st.expander("Exporter / importer un fichier"):
        try:
            data = storage.to_json(st.session_state["save_name"] or "scenario", params_from_state())
            file_name = f"{storage.slugify(st.session_state['save_name'] or 'scenario')}.json"
            st.download_button("Exporter le scénario en cours", data, file_name, "application/json", width="stretch")
        except ValueError:
            st.caption("Donnez un nom valide au scénario pour l'exporter.")
        st.file_uploader("Importer un scénario (.json)", type=["json"], key="import_file")
        st.button("Importer ce fichier", on_click=_import, width="stretch")


def render() -> None:
    with st.sidebar:
        show_flash(st)
        _parameters()
        st.divider()
        _scenarios()
