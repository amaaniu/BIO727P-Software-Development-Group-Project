"""
Database export helpers for visualisation.

This module extracts analysis-ready tables from the application database and computes
the unified Activity Score for each variant using WT control baselines per generation.

Returned objects are plain Python lists of dicts to make serialisation (e.g., JSON) straightforward.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from models import ControlData, Mutations, Variant, db

logger = logging.getLogger(__name__)


_WT_LABELS = {"wt", "wildtype", "wild_type", "wild-type", "control_wt"}


def _is_wt_control(control_type: Optional[str]) -> bool:
    """
    Check if a control label corresponds to a WT control.

    Parameters
    ----------
    control_type:
        Free-text label stored for a control row.

    Returns
    -------
    bool
        True if label looks like a WT control, else False.
    """
    if not control_type:
        return False
    return control_type.strip().lower() in _WT_LABELS


def fetch_variant_summary(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-variant summary table for an experiment.

    Includes:
    - raw yields (dna_yield, protein_yield)
    - WT-normalised yields per generation (dna_norm, protein_norm)
    - unified Activity Score (activity_score_log2)
    - mutation_count and protein_sequence for downstream visualisations

    Parameters
    ----------
    experiment_id:
        Experiment primary key.

    Returns
    -------
    list[dict[str, Any]]
        One dict per variant (JSON-serialisable).

    Notes
    -----
    If WT controls are missing (or yields are zero) for a generation, activity fields are left as None.
    """
    controls = ControlData.query.filter_by(experiment_id=experiment_id).all()

    wt_by_gen: dict[int, dict[str, float]] = {}
    for c in controls:
        if _is_wt_control(c.control_type):
            # Prefer last-seen WT row if there are duplicates; alternatively, you could average here.
            wt_by_gen[int(c.generation)] = {
                "wt_dna": float(c.dna_yield) if c.dna_yield is not None else 0.0,
                "wt_protein": float(c.protein_yield) if c.protein_yield is not None else 0.0,
            }

    variants = (
        Variant.query.filter_by(experiment_id=experiment_id)
        .order_by(Variant.generation.asc(), Variant.variant_id.asc())
        .all()
    )

    rows: List[Dict[str, Any]] = []

    for v in variants:
        gen = int(v.generation)

        wt = wt_by_gen.get(gen)
        dna_norm: Optional[float] = None
        protein_norm: Optional[float] = None
        activity_score_log2: Optional[float] = None

        if wt and wt["wt_dna"] and wt["wt_protein"]:
            if wt["wt_dna"] != 0 and wt["wt_protein"] != 0 and v.dna_yield is not None and v.protein_yield is not None:
                dna_norm = float(v.dna_yield) / wt["wt_dna"]
                protein_norm = float(v.protein_yield) / wt["wt_protein"]

                if protein_norm != 0:
                    raw = dna_norm / protein_norm
                    activity_score_log2 = math.log2(raw) if raw > 0 else None
        else:
            logger.debug("Missing WT baselines for generation=%s (experiment_id=%s)", gen, experiment_id)

        rows.append(
            {
                "variant_id": v.variant_id,
                "generation": gen,
                "plasmid_variant_index": v.plasmid_variant_index,
                "dna_yield": v.dna_yield,
                "protein_yield": v.protein_yield,
                "dna_norm": dna_norm,
                "protein_norm": protein_norm,
                "activity_score_log2": activity_score_log2,
                "mutation_count": v.mutation_count,
                "protein_sequence": v.protein_sequence,
            }
        )

    return rows


def fetch_mutations_table(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-mutation table joined to variant generation.

    Parameters
    ----------
    experiment_id:
        Experiment primary key.

    Returns
    -------
    list[dict[str, Any]]
        One dict per mutation, including generation for plotting.
    """
    q = (
        db.session.query(
            Mutations.variant_id,
            Variant.generation,
            Mutations.position,
            Mutations.wt_residue,
            Mutations.mutant_residue,
            Mutations.mutation_type,
            Mutations.codon_change,
        )
        .join(Variant, Variant.variant_id == Mutations.variant_id)
        .filter(Variant.experiment_id == experiment_id)
        .order_by(Variant.variant_id.asc(), Mutations.position.asc())
    )

    rows: List[Dict[str, Any]] = []
    for r in q.all():
        rows.append(
            {
                "variant_id": r.variant_id,
                "generation": int(r.generation),
                "position": r.position,
                "wt_residue": r.wt_residue,
                "mutant_residue": r.mutant_residue,
                "mutation_type": r.mutation_type,
                "codon_change": r.codon_change,
            }
        )

    return rows