"""
Top-performer variants table.

Produces a top 10 ranking of variants based on the
log2-transformed activity score.

The top 10 table is used to:
- Identify the highest-performing variants
- Select a representative variant for downstream visualisations
  (e.g. mutation fingerprint)

Explicit tie-breakers are applied when activity scores are identical.
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
    Compute the top 10 variants ranked by activity score (log2).

    Args:
    
    variants_df : pandas.DataFrame
        DataFrame containing variant-level data. Must include
        at least the columns listed in REQUIRED_COLS.

    Returns:
    
    pandas.DataFrame
        A dataframe containing the top 10 ranked variants,
        sorted deterministically by:

        1. activity_score_log2 (descending)
        2. generation (descending)
        3. variant_id (ascending)

        Deterministic tie-breaking ensures stable behaviour across
        repeated analysis runs and prevents random switching of the
        selected top variant in downstream visualisations.

    Raises
    ------
    ValueError
        If required columns are missing from the input dataframe.

    Notes
    -----
    - activity_score_log2 values are coerced to numeric to ensure
      robustness against mixed-type inputs.
    - Rows with missing activity scores are excluded.
    - A stable sorting algorithm (mergesort) is used to preserve
      reproducibility when ties occur.
    """

    # ---- Validation ----
    missing = set(REQUIRED_COLS) - set(variants_df.columns)
    if missing:
        raise ValueError(f"Missing required columns for top10: {sorted(missing)}")

    df = variants_df[REQUIRED_COLS].copy()

    # ---- Ensure numeric activity score ----
    df["activity_score_log2"] = pd.to_numeric(
        df["activity_score_log2"],
        errors="coerce",
    )

    # Remove rows without valid scores
    df = df.dropna(subset=["activity_score_log2"])

    # ---- Deterministic sorting ----
    top10 = (
        df.sort_values(
            by=["activity_score_log2", "generation", "variant_id"],
            ascending=[False, False, True],
            kind="mergesort",  # stable sorting for reproducibility
        )
        .head(10)
        .reset_index(drop=True)
    )

    return top10