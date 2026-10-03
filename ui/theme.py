"""Réglages d'affichage partagés par les onglets."""

from __future__ import annotations

import streamlit as st

PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

DISCLAIMER = (
    "Simulation pédagogique fondée sur des hypothèses (rendement régulier, taux fiscaux constants). "
    "Ce n'est ni une prévision, ni une garantie de rendement, ni un conseil en investissement : "
    "les marchés fluctuent et le capital peut diminuer."
)


def is_dark() -> bool:
    """Thème sombre actif dans Streamlit (clair par défaut si l'information manque)."""
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False
