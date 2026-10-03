"""Mise en forme des nombres à la française (espaces fines, virgule décimale)."""

from __future__ import annotations

NARROW_NBSP = " "
NBSP = " "


def eur(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}".replace(",", NARROW_NBSP).replace(".", ",")
    return f"{text}{NBSP}€"


def pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",") + f"{NBSP}%"


def multiplier(value: float) -> str:
    return "×" + f"{value:.2f}".replace(".", ",")


def duration(months: int) -> str:
    years, rest = divmod(int(months), 12)
    parts = []
    if years:
        parts.append(f"{years} an{'s' if years > 1 else ''}")
    if rest:
        parts.append(f"{rest} mois")
    return " et ".join(parts) or "0 mois"
