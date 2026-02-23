"""
Data access layer for the visualisation package.

Supports:
- 'dummy' synthetic data for development/demo
- 'db_export' JSON files exported from the backend

"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SourceType = Literal["dummy", "db_export"]


def make_dummy_variants(
    n_generations: int = 6,
    variants_per_generation: int = 80,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a synthetic variants table (one row per variant) for development.

    The dummy data simulates gradual improvement across generations and computes an Activity Score
    using the same WT-normalised ratio used in the real pipeline.

    Parameters
    ----------
    n_generations:
        Number of directed evolution generations to simulate.
    variants_per_generation:
        Number of variants per generation.
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    pandas.DataFrame
        Columns include:
        - variant_id, generation, dna_yield, protein_yield
        - dna_norm, protein_norm, activity_score_raw, activity_score_log2
        - mutation_count
    """
    rng = np.random.default_rng(seed)

    rows = []
    variant_id = 1

    wt_dna_by_gen = {g: 30 + g * 3 for g in range(1, n_generations + 1)}
    wt_protein_by_gen = {g: 50 + g * 5 for g in range(1, n_generations + 1)}

    for gen in range(1, n_generations + 1):
        wt_dna = float(wt_dna_by_gen[gen])
        wt_protein = float(wt_protein_by_gen[gen])

        for _ in range(variants_per_generation):
            mutation_count = int(max(0, rng.normal(loc=gen * 1.2, scale=1.5)))

            protein_yield = float(max(0.0, rng.normal(loc=50 + gen * 5, scale=10)))
            dna_yield = float(max(0.0, rng.normal(loc=30 + gen * 3, scale=8)))

            dna_norm = dna_yield / wt_dna if wt_dna else None
            protein_norm = protein_yield / wt_protein if wt_protein else None

            activity_raw = None
            activity_log2 = None
            if dna_norm is not None and protein_norm not in (None, 0):
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


def load_variants_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the variants summary exported from the backend.

    Parameters
    ----------
    path:
        JSON file path produced by the backend exporter.

    Returns
    -------
    pandas.DataFrame
        Variants table with basic type coercion applied.
    """
    path = Path(path)
    df = pd.read_json(path)

    for col in ("generation", "activity_score_log2", "mutation_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_mutations_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the mutations table exported from the backend.

    Parameters
    ----------
    path:
        JSON file path produced by the backend exporter.

    Returns
    -------
    pandas.DataFrame
        Mutations table with basic type coercion applied.
    """
    path = Path(path)
    df = pd.read_json(path)

    for col in ("generation", "position"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_variants(
    experiment_id: int | None = None,
    source: SourceType = "dummy",
    variants_json_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Single entry point to obtain a variants dataframe for plotting.

    Parameters
    ----------
    experiment_id:
        Reserved for future direct DB access (not used in the JSON-based visualisation flow).
    source:
        'dummy' or 'db_export'.
    variants_json_path:
        Required if source='db_export'.

    Returns
    -------
    pandas.DataFrame
    """
    if source == "dummy":
        return make_dummy_variants()

    if source == "db_export":
        if not variants_json_path:
            raise ValueError("variants_json_path must be provided when source='db_export'")
        return load_variants_from_json(variants_json_path)

    raise ValueError(f"Unknown source: {source}")


def get_mutations(
    experiment_id: int | None = None,
    source: SourceType = "db_export",
    mutations_json_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Single entry point to obtain a mutations dataframe for bonus plots.

    Parameters
    ----------
    experiment_id:
        Reserved for future direct DB access (not used in the JSON-based visualisation flow).
    source:
        Currently only 'db_export' is supported.
    mutations_json_path:
        Required if source='db_export'.

    Returns
    -------
    pandas.DataFrame
    """
    if source == "db_export":
        if not mutations_json_path:
            raise ValueError("mutations_json_path must be provided when source='db_export'")
        return load_mutations_from_json(mutations_json_path)

    raise ValueError(f"Unknown source: {source}")