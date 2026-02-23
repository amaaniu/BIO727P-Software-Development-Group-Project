"""
Top-performer variants table.

Required output:
- A top 10 table sorted by the unified activity metric, including essential fields and mutation count. 
"""

from __future__ import annotations

from typing import Final, List

import pandas as pd

REQUIRED_COLS: Final[List[str]] = [
    "variant_id",
    "generation",
    "activity_score_log2",
    "mutation_count",
    "protein_yield",
    "dna_yield",
]


def compute_top10(variants_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the top 10 variants by Activity Score (log2).

    Parameters
    ----------
    variants_df:
        Variants dataframe containing at least REQUIRED_COLS.

    Returns
    -------
    pandas.DataFrame
        Top 10 rows, sorted descending by activity_score_log2.

    Raises
    ------
    ValueError
        If required columns are missing.
    """
    missing = set(REQUIRED_COLS) - set(variants_df.columns)
    if missing:
        raise ValueError(f"Missing required columns for top10: {sorted(missing)}")

    top10 = (
        variants_df[REQUIRED_COLS]
        .copy()
        .assign(activity_score_log2=pd.to_numeric(variants_df["activity_score_log2"], errors="coerce"))
        .dropna(subset=["activity_score_log2"])
        .sort_values("activity_score_log2", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    return top10