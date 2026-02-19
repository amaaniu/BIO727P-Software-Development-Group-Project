from __future__ import annotations
import math
from typing import Dict, Optional, Any


def compute_activity_score_raw(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:
    """
    Compute activity score using database-aligned variable names.
    """

    if dna_yield is None or protein_yield is None:
        return None

    if wt_dna_yield is None or wt_protein_yield is None:
        return None

    if wt_dna_yield == 0 or wt_protein_yield == 0:
        return None

    dna_norm = dna_yield / wt_dna_yield

    protein_norm = protein_yield / wt_protein_yield

    if protein_norm == 0:
        return None

    activity_score_raw = dna_norm / protein_norm

    return {
        "dna_norm": dna_norm,
        "protein_norm": protein_norm,
        "activity_score_raw": activity_score_raw,
    }


def compute_activity_score_log2(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:
    """
    Compute raw and log2 activity scores using DB-aligned variable names.
    """

    result = compute_activity_score_raw(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )

    if result is None:
        return None

    raw = result["activity_score_raw"]

    result["activity_score_log2"] = (
        math.log2(raw) if raw > 0 else None
    )

    return result


def compute_activity_scores(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:
    """
    Main function to call from database pipeline.
    """

    return compute_activity_score_log2(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )