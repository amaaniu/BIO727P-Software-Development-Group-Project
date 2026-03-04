from __future__ import annotations
import math
from typing import Dict, Optional, Any, Mapping, Tuple

def _get_wt_for_generation(
    generation: int,
    wt_by_generation: Mapping[int, Tuple[float, float]],
) -> Optional[Tuple[float, float]]:
    """Pick the WT baseline (WT DNA, WT protein) for a given generation."""
    # Validate generation

    if generation is None:
        return None
    try:
        g = int(generation)
    except (TypeError, ValueError):
            return None
    if g <= 0:
            return None

    # Baseline rule: Gen 1 uses Gen 1 WT, Gen g uses Gen (g-1) WT
    baseline_generation = 1 if g == 1 else (g - 1)

    # Lookup returns (wt_dna_yield, wt_protein_yield) or None if missing
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
    # Missing inputs converted into cannot compute 
    if dna_yield is None or protein_yield is None:
            return None
    
    if wt_dna_yield is None or wt_protein_yield is None:
        return None

    # Avoid divsion by zero
    if wt_dna_yield == 0 or wt_protein_yield == 0:
        return None

    # Normalise to WT (dimensionless ratios)
    dna_norm = dna_yield / wt_dna_yield
    protein_norm = protein_yield / wt_protein_yield

    # Avoid invalid ratio/log values
    if protein_norm == 0:
        return None

    ratio = dna_norm / protein_norm

    if ratio <= 0:
        return None

    # Return intermediates for transparency/debuggin + fianl score
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
    """Compute activity score using WT baseline selected from the generation rule."""
    # Select correct WT baseline for this generation
    wt_values = _get_wt_for_generation(generation, wt_by_generation)
    if wt_values is None:
        return None

    wt_dna_yield, wt_protein_yield = wt_values

    # Compute score using the chosen baseline
    return compute_activity_score_log2(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )