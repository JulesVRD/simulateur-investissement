"""Simulateur d'investissement : point d'entrée Streamlit.

Lancement :  streamlit run app.py
"""

import streamlit as st

from ui import sidebar, tab_compare, tab_goal, tab_salary, tab_simulation
from ui.state import init_state, params_from_state

st.set_page_config(page_title="Simulateur d'investissement", layout="wide")

init_state()
sidebar.render()
params = params_from_state()

st.title("Simulateur d'investissement")

errors = params.validate()
if errors:
    st.error("Paramètres invalides : " + " ".join(errors))
    st.stop()

simulation, salary, goal, comparison = st.tabs(
    ["Simulation", "Salaire et épargne", "Objectif inversé", "Comparaison de scénarios"]
)
with simulation:
    tab_simulation.render(params)
with salary:
    tab_salary.render(params)
with goal:
    tab_goal.render(params)
with comparison:
    tab_compare.render(params)
