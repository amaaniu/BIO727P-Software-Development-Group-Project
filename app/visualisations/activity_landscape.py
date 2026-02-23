# 3D activity landscape
# - uses mutation positions to build features per variant
# - PCA for 2D embedding
# - z axis is activity_score_log2

import numpy as np
import pandas as pd
import plotly.express as px
from app.visualisations.data_source2 import get_variants, get_mutations

def _build_mutation_feature_matrix(mutations_df: pd.DataFrame) -> pd.DataFrame:
    # turns mutation positions into a wide binary matrix: one column per position
    # each row = variant_id

    required = {"variant_id", "position"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = mutations_df.copy()
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["position"])
    df["position"] = df["position"].astype(int)

    # one-hot encode mutation positions
    df["present"] = 1
    wide = (
        df.pivot_table(
            index="variant_id",
            columns="position",
            values="present",
            aggfunc="max",
            fill_value=0,
        )
        .sort_index(axis=1)
    )

    return wide.astype(float)


def _pca_2d(X: np.ndarray):
    # minimal PCA using SVD
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    coords = U[:, :2] * S[:2]
    return coords


def plot_activity_landscape_3d(
    variants_df: pd.DataFrame,
    mutations_df: pd.DataFrame,
    title: str = "3D Activity Landscape",
    score_col: str = "activity_score_log2",
):
    # required columns
    required = {"variant_id", score_col}
    missing = required - set(variants_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    feat = _build_mutation_feature_matrix(mutations_df)

    meta = variants_df[["variant_id", "generation", score_col]].copy()
    meta[score_col] = pd.to_numeric(meta[score_col], errors="coerce")
    meta = meta.dropna(subset=[score_col])

    merged = meta.merge(feat, left_on="variant_id", right_index=True, how="inner")
    if merged.empty:
        raise ValueError("No overlapping variants between variants_df and mutations_df")

    feature_cols = feat.columns.tolist()
    X = merged[feature_cols].to_numpy(dtype=float)

    coords = _pca_2d(X)
    merged["dim1"] = coords[:, 0]
    merged["dim2"] = coords[:, 1]

    fig = px.scatter_3d(
        merged,
        x="dim1",
        y="dim2",
        z=score_col,
        color="generation",
        hover_data=["variant_id", "generation", score_col],
        title=title,
    )

    fig.update_layout(
        scene=dict(
            xaxis_title="Sequence diversity dim 1 (PCA)",
            yaxis_title="Sequence diversity dim 2 (PCA)",
            zaxis_title="Activity score (log2)",
        ),
        template="simple_white",
    )

    return fig
