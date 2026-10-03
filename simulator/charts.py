"""Graphiques Plotly. Aucune dépendance à Streamlit : chaque fonction renvoie une figure.

Couleurs : palette catégorielle de référence, attribuée dans un ordre fixe (la
couleur suit l'entité, pas son rang) et déclinée en deux jeux, clair et sombre.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
import plotly.graph_objects as go

from .formatting import eur
from .metrics import Summary

# Palette catégorielle (clair, sombre), ordre fixe.
_SERIES = {
    False: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    True: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
_INK = {
    False: dict(primary="#0b0b0b", secondary="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7", surface="#fcfcfb"),
    True: dict(primary="#ffffff", secondary="#c3c2b7", muted="#898781", grid="#2c2c2a", axis="#383835", surface="#1a1a19"),
}

# Une couleur par entité, quelle que soit la figure.
SLOT_INITIAL, SLOT_CONTRIBUTIONS, SLOT_INTEREST = 0, 1, 2
SLOT_PEA, SLOT_CTO = 3, 4
SLOT_TAX = 6
REGIME_SLOT = {"pea": SLOT_PEA, "cto": SLOT_CTO}
# Trajectoires de salaire : les trois premières couleurs de la palette sont validées pour tous les couples.
SCENARIO_SLOT = {"low": 1, "mid": 0, "high": 2}
SLOT_CUSTOM_SALARY = 4  # trajectoire « réglage personnalisé »

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
HEIGHT = 470

COMPARE_METRICS = {
    "total": "Capital final (avant impôt)",
    "net": "Net après impôt",
    "interest": "Intérêts cumulés",
    "invested": "Total investi",
}


def _base_layout(fig: go.Figure, dark: bool, y_title: str, hovermode: str = "x unified") -> go.Figure:
    ink = _INK[dark]
    axis = dict(linecolor=ink["axis"], tickfont=dict(color=ink["muted"]), title_font=dict(color=ink["secondary"]))
    fig.update_layout(
        height=HEIGHT,
        margin=dict(l=8, r=8, t=48, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=ink["secondary"]),
        separators=", ",  # virgule décimale, espace pour les milliers
        hovermode=hovermode,
        hoverlabel=dict(bgcolor=ink["surface"], font=dict(color=ink["primary"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=ink["secondary"])),
        xaxis=dict(title="Durée (années)", showgrid=False, hoverformat=".1f", zeroline=False, **axis),
        yaxis=dict(
            title=y_title, gridcolor=ink["grid"], zeroline=False, tickformat=",.0f", ticksuffix=" €", **axis
        ),
    )
    return fig


def _hover(name: str) -> str:
    return f"{name} : %{{customdata:,.0f}} €<extra></extra>"


def evolution_chart(
    df: pd.DataFrame,
    *,
    mode: str = "stacked",
    dark: bool = False,
    net_lines: Sequence[tuple[str, pd.Series, int]] = (),
    target: float | None = None,
    pea_full_year: float | None = None,
    real_terms: bool = False,
) -> go.Figure:
    """Capital de départ, investissement (versements) et intérêts, dans le temps.

    mode="stacked" : trois couches empilées dont la somme est le capital total.
    mode="lines"   : trois courbes superposées.
    net_lines      : courbes pointillées (libellé, série, couleur) du net après impôt.
    target         : trace une ligne horizontale à ce montant (objectif inversé).
    pea_full_year  : trace une ligne verticale à l'année où le PEA atteint son plafond.
    """
    colors, ink = _SERIES[dark], _INK[dark]
    stacked = mode == "stacked"
    fig = go.Figure()
    layers = [
        ("Capital de départ", "initial", SLOT_INITIAL),
        ("Investissement (versements cumulés)", "contributions", SLOT_CONTRIBUTIONS),
        ("Intérêts cumulés", "interest", SLOT_INTEREST),
    ]
    for name, column, slot in layers:
        common = dict(x=df["year"], y=df[column], name=name, customdata=df[column], hovertemplate=_hover(name))
        if stacked:
            fig.add_trace(
                go.Scatter(
                    mode="lines", stackgroup="capital", fillcolor=colors[slot],
                    line=dict(width=2, color=ink["surface"]), **common,
                )
            )
        else:
            fig.add_trace(go.Scatter(mode="lines", line=dict(width=2.5, color=colors[slot]), **common))

    fig.add_trace(
        go.Scatter(
            x=df["year"], y=df["total"], name="Capital total", mode="lines",
            line=dict(width=2, color=ink["primary"]), customdata=df["total"], hovertemplate=_hover("Capital total"),
        )
    )
    for label, series, slot in net_lines:
        # Liseré de la couleur du fond sous la courbe : elle reste lisible par-dessus les couches colorées.
        fig.add_trace(
            go.Scatter(
                x=df["year"], y=series, mode="lines", line=dict(width=7, color=ink["surface"]),
                showlegend=False, hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["year"], y=series, name=label, mode="lines", line=dict(width=3, color=colors[slot], dash="dash"),
                customdata=series, hovertemplate=_hover(label),
            )
        )

    last_year, last_total = float(df["year"].iloc[-1]), float(df["total"].iloc[-1])
    fig.add_annotation(
        x=last_year, y=last_total, text=eur(last_total), showarrow=False, xanchor="right", yanchor="bottom",
        yshift=6, font=dict(color=ink["primary"], size=13),
    )
    if pea_full_year is not None and pea_full_year <= last_year:
        fig.add_vline(
            x=pea_full_year, line=dict(color=ink["secondary"], dash="dot", width=1.5),
            annotation_text="PEA plein : le surplus part en CTO", annotation_position="top left",
            annotation_font=dict(color=ink["secondary"]),
        )
    if target is not None:
        fig.add_hline(
            y=target, line=dict(color=ink["secondary"], dash="dot", width=1.5),
            annotation_text=f"Objectif : {eur(target)}", annotation_position="top left",
            annotation_font=dict(color=ink["secondary"]),
        )
        top = max(target, last_total, *(float(s.max()) for _, s, _ in net_lines))
        fig.update_yaxes(range=[min(0.0, float(df["interest"].min())), top * 1.1])

    y_title = "Montant (€ constants, pouvoir d'achat d'aujourd'hui)" if real_terms else "Montant (€)"
    return _base_layout(fig, dark, y_title)


def lines_chart(
    frames: Mapping[str, pd.DataFrame],
    column: str,
    y_title: str,
    *,
    slots: Sequence[int] | None = None,
    dashed: Sequence[str] = (),
    thick: Sequence[str] = (),
    dark: bool = False,
) -> go.Figure:
    """Une courbe par entrée de `frames` (tableaux avec une colonne `year` et la colonne choisie).

    slots  : couleur de chaque courbe (indices de la palette) ; par défaut dans l'ordre de la palette.
    dashed : noms des courbes tracées en pointillés. thick : noms des courbes mises en avant (plus épaisses).
    """
    colors = _SERIES[dark]
    fig = go.Figure()
    for index, (name, df) in enumerate(frames.items()):
        slot = slots[index] if slots is not None else index
        fig.add_trace(
            go.Scatter(
                x=df["year"], y=df[column], name=name, mode="lines", customdata=df[column],
                line=dict(width=4 if name in thick else 2.5, color=colors[slot % len(colors)],
                          dash="dash" if name in dashed else "solid"),
                hovertemplate=_hover(name),
            )
        )
    return _base_layout(fig, dark, y_title)


def comparison_chart(
    frames: Mapping[str, pd.DataFrame], column: str = "total", *, dark: bool = False, real_terms: bool = False
) -> go.Figure:
    """Une courbe par scénario pour la grandeur choisie."""
    y_title = f"{COMPARE_METRICS[column]} ({'€ constants' if real_terms else '€'})"
    return lines_chart(frames, column, y_title, dark=dark)


def breakdown_chart(summaries: Mapping[str, Summary], *, dark: bool = False) -> go.Figure:
    """Répartition du capital final de chaque scénario : départ, versements, intérêts nets d'impôt, impôt."""
    colors, ink = _SERIES[dark], _INK[dark]
    names = list(summaries)
    segments = [
        ("Capital de départ", [s.initial for s in summaries.values()], SLOT_INITIAL),
        ("Versements", [s.contributions for s in summaries.values()], SLOT_CONTRIBUTIONS),
        ("Intérêts (nets d'impôt)", [s.interest - s.tax for s in summaries.values()], SLOT_INTEREST),
        ("Impôt à la sortie", [s.tax for s in summaries.values()], SLOT_TAX),
    ]
    fig = go.Figure()
    for name, values, slot in segments:
        if name == "Impôt à la sortie" and not any(values):
            continue
        fig.add_trace(
            go.Bar(
                x=names, y=values, name=name, customdata=values, hovertemplate=_hover(name),
                marker=dict(color=colors[slot], line=dict(color=ink["surface"], width=2)),
            )
        )
    labels = [f"Net {eur(s.net)}" if s.tax else eur(s.total) for s in summaries.values()]
    fig.add_trace(
        go.Scatter(
            x=names, y=[s.total for s in summaries.values()], mode="text", text=labels,
            textposition="top center", textfont=dict(color=ink["primary"], size=13), showlegend=False, hoverinfo="skip",
        )
    )
    fig.update_layout(barmode="relative", bargap=0.45)
    fig.update_yaxes(range=[min(0.0, min(s.interest - s.tax for s in summaries.values())), max(s.total for s in summaries.values()) * 1.15])
    _base_layout(fig, dark, "Capital final (€)", hovermode="closest")
    fig.update_layout(xaxis_title=None, height=420)
    return fig
