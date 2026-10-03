"""État de l'interface : valeurs des widgets, chargement d'un scénario, messages."""

from __future__ import annotations

from dataclasses import asdict, fields

import streamlit as st

from simulator.params import BOUNDS, SimulationParams

# Clé de session de chaque paramètre (une clé = un widget de la barre latérale).
KEYS = {field.name: f"p_{field.name}" for field in fields(SimulationParams)}

UI_DEFAULTS = {
    "chart_mode": "stacked",
    "goal_mode": "contribution",
    "goal_target": 100_000.0,
    "goal_basis": "gross",
    "cmp_choices": [],
    "cmp_current": True,
    "cmp_unit": "own",
    "cmp_metric": "total",
    "salary_view": "salary",
    "save_name": "",
    "load_choice": None,
}


def _widget_value(name: str, value):
    """Convertit une valeur de paramètre au type attendu par son widget."""
    if name == "years":  # le curseur de durée attend un entier dans ses bornes
        low, high = BOUNDS["years"]
        return int(min(max(round(value), low), high))
    if isinstance(value, bool) or isinstance(value, str):
        return value
    return float(value)


def init_state() -> None:
    for name, value in asdict(SimulationParams()).items():
        st.session_state.setdefault(KEYS[name], _widget_value(name, value))
    for key, value in UI_DEFAULTS.items():
        st.session_state.setdefault(key, value)
    # Streamlit oublie la valeur d'un widget qui n'est pas affiché pendant une exécution (ex. le versement
    # fixe quand on passe en mode « % du salaire »). Réaffecter la clé la conserve pour le retour.
    for key in KEYS.values():
        st.session_state[key] = st.session_state[key]


def params_from_state() -> SimulationParams:
    return SimulationParams(**{name: st.session_state[key] for name, key in KEYS.items()})


def load_params_into_state(params: SimulationParams) -> None:
    """À appeler depuis un callback (avant que les widgets ne soient recréés)."""
    for name, value in asdict(params).items():
        st.session_state[KEYS[name]] = _widget_value(name, value)


def flash(kind: str, message: str) -> None:
    """Message affiché au prochain rendu ('success', 'error', 'info' ou 'warning')."""
    st.session_state["flash"] = (kind, message)


def show_flash(container) -> None:
    item = st.session_state.pop("flash", None)
    if item:
        kind, message = item
        getattr(container, kind)(message)
