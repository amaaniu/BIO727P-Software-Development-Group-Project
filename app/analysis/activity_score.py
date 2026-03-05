from __future__ import annotations
import math
from typing import Dict, Optional, Any, Mapping, Tuple

def _get_wt_for_generation(
    generation: int,
    wt_by_generation: Mapping[int, Tuple[float, float]],
) -> Optional[Tuple[float, float]]:
    """
    Baseline rule:
      - Gen 1 uses Gen 1 WT
      - Gen g (g>=2) uses Gen (g-1) WT
    """
    if generation is None:
        return None

    try:
        g = int(generation)
    except (TypeError, ValueError):
        return None

    if g <= 0:
        return None

    baseline_generation = 1 if g == 1 else (g - 1)

    return wt_by_generation.get(baseline_generation)

def compute_activity_score_log2(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:
    """
    Compute log2 activity scores only.
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

    ratio = dna_norm / protein_norm

    if ratio <= 0:
        return None

    return {
        "dna_norm": dna_norm,
        "protein_norm": protein_norm,
        "activity_score_log2": math.log2(ratio),
    }


def compute_activity_scores(
    dna_yield: float,
    protein_yield: float,
    generation: int,
    wt_by_generation: Mapping[int, Tuple[float, float]]
) -> Optional[Dict[str, Any]]:
    """
    Automatically selects correct WT baseline based on generation.
    """

    wt_values = _get_wt_for_generation(generation, wt_by_generation)

    if wt_values is None:
        return None

    wt_dna_yield, wt_protein_yield = wt_values

    return compute_activity_score_log2(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )