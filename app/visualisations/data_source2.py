from __future__ import annotations

import pandas as pd

from app.models import db, Variant, Mutations


# =========================
# LIVE DB LOADERS
# =========================

def load_variants_from_db(experiment_id: int) -> pd.DataFrame:
    """
    Load variants from the SQL database for a given experiment_id and return
    a plot-friendly DataFrame.

    Note: DB stores Variant.activity_score (log2) but plotting code expects
    "activity_score_log2", so we map it here.
    """
    rows = (Variant.query
            .filter_by(experiment_id=experiment_id)
            .order_by(Variant.generation.asc(), Variant.plasmid_variant_index.asc())
            .all())

    data = []

    for v in rows:
        data.append({
            "variant_id": v.variant_id,
            "experiment_id": v.experiment_id,
            "generation": v.generation,
            "plasmid_variant_index": v.plasmid_variant_index,
            "dna_yield": v.dna_yield,
            "protein_yield": v.protein_yield,
            "mutation_count": v.mutation_count,

            # IMPORTANT: DB field name -> plot field name
            "activity_score_log2": v.activity_score,
        })

    df = pd.DataFrame(data)

    # basic typing / safety
    if not df.empty:
        if "generation" in df.columns:
            df["generation"] = pd.to_numeric(df["generation"], errors="coerce")

        if "mutation_count" in df.columns:
            df["mutation_count"] = pd.to_numeric(df["mutation_count"], errors="coerce")

        for col in ("dna_yield", "protein_yield", "activity_score_log2"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_mutations_from_db(experiment_id: int) -> pd.DataFrame:
    """
    Load mutations for a given experiment_id by joining:
    Mutations -> Variant (to filter by Variant.experiment_id).

    Returns a DataFrame suitable for mutation-level visuals or tables.
    """
    q = (db.session.query(
            Mutations.mutation_id,
            Mutations.variant_id,
            Mutations.position,
            Mutations.wt_residue,
            Mutations.mutant_residue,
            Mutations.mutation_type,
            Mutations.generation,
            Mutations.codon_change,
        )
        .join(Variant, Variant.variant_id == Mutations.variant_id)
        .filter(Variant.experiment_id == experiment_id)
        .order_by(Mutations.variant_id.asc(), Mutations.position.asc())
    )

    rows = q.all()

    data = []

    for r in rows:
        data.append({
            "mutation_id": r.mutation_id,
            "variant_id": r.variant_id,
            "position": r.position,
            "wt_residue": r.wt_residue,
            "mutant_residue": r.mutant_residue,
            "mutation_type": r.mutation_type,
            "generation": r.generation,
            "codon_change": r.codon_change,
        })

    df = pd.DataFrame(data)

    # basic typing / safety
    if not df.empty:
        if "generation" in df.columns:
            df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
        if "position" in df.columns:
            df["position"] = pd.to_numeric(df["position"], errors="coerce")

    return df


# =========================
# ENTRY POINTS
# =========================

def get_variants(experiment_id: int) -> pd.DataFrame:
    """
    Single entry point for variants for plotting.
    """
    if not experiment_id:
        raise ValueError("experiment_id must be provided")
    return load_variants_from_db(experiment_id)


def get_mutations(experiment_id: int) -> pd.DataFrame:
    """
    Single entry point for mutations (optional visuals / tables).
    """
    if not experiment_id:
        raise ValueError("experiment_id must be provided")
    return load_mutations_from_db(experiment_id)