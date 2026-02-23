# data sources for visualisation
# - dummy data for development
# - db export loaders for integration

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


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
