# data sources for visualisation
# - dummy data for development
# - db export loaders for integration

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


# generate dummy variants (one row per variant)
def make_dummy_variants(
    n_generations: int = 6,
    variants_per_generation: int = 80,
    seed: int = 42
) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    rows = []
    variant_id = 1

    # dummy WT baselines per generation
    
    wt_dna_by_gen = {g: 30 + g * 3 for g in range(1, n_generations + 1)}
    wt_protein_by_gen = {g: 50 + g * 5 for g in range(1, n_generations + 1)}

    for gen in range(1, n_generations + 1):
        for _ in range(variants_per_generation):

            mutation_count = int(max(0, rng.normal(loc=gen * 1.2, scale=1.5)))

            protein_yield = float(max(0.0, rng.normal(loc=50 + gen * 5, scale=10)))
            dna_yield = float(max(0.0, rng.normal(loc=30 + gen * 3, scale=8)))

            # compute log2 activity using the same logic as the pipeline definition:
            # activity_score_raw = (dna_yield / wt_dna) / (protein_yield / wt_protein)
            # activity_score_log2 = log2(activity_score_raw) if raw > 0
            wt_dna = wt_dna_by_gen[gen]
            wt_protein = wt_protein_by_gen[gen]

            dna_norm = dna_yield / wt_dna if wt_dna else None
            protein_norm = protein_yield / wt_protein if wt_protein else None

            activity_raw = None
            activity_log2 = None

            if dna_norm is not None and protein_norm and protein_norm != 0:
                activity_raw = dna_norm / protein_norm
                activity_log2 = math.log2(activity_raw) if activity_raw and activity_raw > 0 else None

            rows.append(
                {
                    "variant_id": variant_id,
                    "generation": gen,
                    "dna_yield": dna_yield,
                    "protein_yield": protein_yield,
                    "dna_norm": dna_norm,
                    "protein_norm": protein_norm,
                    "activity_score_raw": activity_raw,
                    "activity_score_log2": activity_log2,
                    "mutation_count": mutation_count,
                }
            )

            variant_id += 1

    return pd.DataFrame(rows)


# load variants summary exported from backend/db (json)
def load_variants_from_json(path: str) -> pd.DataFrame:
    df = pd.read_json(path)

    # basic typing / safety
    if "generation" in df.columns:
        df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    if "activity_score_log2" in df.columns:
        df["activity_score_log2"] = pd.to_numeric(df["activity_score_log2"], errors="coerce")
    if "mutation_count" in df.columns:
        df["mutation_count"] = pd.to_numeric(df["mutation_count"], errors="coerce")

    return df


# load mutations exported from backend/db (json)
def load_mutations_from_json(path: str) -> pd.DataFrame:
    df = pd.read_json(path)

    # basic typing / safety
    if "generation" in df.columns:
        df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    if "position" in df.columns:
        df["position"] = pd.to_numeric(df["position"], errors="coerce")

    return df


# get variants (single entry point)
# - source="dummy": generate dummy data
# - source="db_export": load backend-exported json
def get_variants(
    experiment_id: int | None = None,
    source: str = "dummy",
    variants_json_path: Optional[str] = None,
) -> pd.DataFrame:

    if source == "dummy":
        return make_dummy_variants()

    if source == "db_export":
        if not variants_json_path:
            raise ValueError("variants_json_path must be provided when source='db_export'")
        return load_variants_from_json(variants_json_path)

    raise ValueError(f"Unknown source: {source}")


# get mutations (for bonus visuals)
def get_mutations(
    experiment_id: int | None = None,
    source: str = "db_export",
    mutations_json_path: Optional[str] = None,
) -> pd.DataFrame:

    if source == "db_export":
        if not mutations_json_path:
            raise ValueError("mutations_json_path must be provided when source='db_export'")
        return load_mutations_from_json(mutations_json_path)

    raise ValueError(f"Unknown source: {source}")
