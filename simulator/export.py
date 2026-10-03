"""Export des résultats."""

from __future__ import annotations

import pandas as pd


def table_to_csv(table: pd.DataFrame) -> bytes:
    """CSV lisible directement dans Excel français (séparateur ';', virgule décimale, UTF-8 BOM)."""
    return table.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
