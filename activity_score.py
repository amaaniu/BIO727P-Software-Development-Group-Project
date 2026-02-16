from __future__ import annotations
import math
from typing import Dict, Optional, Any


def compute_activity_score_raw(
    dna_value: float,
    protein_value: float,
    wt_dna: float,
    wt_protein: float
) -> Optional[Dict[str, Any]]:
    """
    Returns normalised DNA/protein and the raw activity score:
      activity_score_raw = (dna_value / wt_dna) / (protein_value / wt_protein)
    """

    if dna_value is None or protein_value is None or wt_dna is None or wt_protein is None:
        return None
    if wt_dna == 0 or wt_protein == 0:
        return None

    dna_norm = dna_value / wt_dna
    protein_norm = protein_value / wt_protein

    if protein_norm == 0:
        return None

    raw = dna_norm / protein_norm

    return {
        "dna_norm": dna_norm,
        "protein_norm": protein_norm,
        "activity_score_raw": raw,
    }


def compute_activity_score_log2(
    dna_value: float,
    protein_value: float,
    wt_dna: float,
    wt_protein: float
) -> Optional[Dict[str, Any]]:
    """
    Returns normalised DNA/protein and both raw + log2 activity scores:
      activity_score_log2 = log2(activity_score_raw)
    """

    out = compute_activity_score_raw(dna_value, protein_value, wt_dna, wt_protein)
    if out is None:
        return None

    raw = out["activity_score_raw"]
    out["activity_score_log2"] = math.log2(raw) if raw > 0 else None
    return out


def compute_activity_scores(
    dna_value: float,
    protein_value: float,
    wt_dna: float,
    wt_protein: float
) -> Optional[Dict[str, Any]]:
    """
    Convenience wrapper: returns dna_norm, protein_norm, activity_score_raw, activity_score_log2.
    """
    return compute_activity_score_log2(dna_value, protein_value, wt_dna, wt_protein)