"""
3D Activity Landscape (bonus visual).

Approach:
- Build a binary feature matrix per variant based on which mutation positions are present
- Reduce features to 2D using a minimal PCA (SVD)
- Plot 3D scatter where z = Activity Score (log2)

"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px


def _build_mutation_feature_matrix(mutations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert mutation positions into a wide binary (0/1) feature matrix.

    Parameters
    ----------
    mutations_df:
        Must contain 'variant_id' and 'position'.

    Returns
    -------
    pandas.DataFrame
        Index: variant_id
        Columns: mutation positions (int)
        Values: 1 if variant has a mutation at that position.
    """
    required = {"variant_id", "position"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = mutations_df.copy()
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["position"])
    df["position"] = df["position"].astype(int)

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
        .astype(float)
    )
    return wide


def _pca_2d(X: np.ndarray) -> np.ndarray:
    """
    Minimal PCA (2D) using SVD.

    Parameters
    ----------
    X:
        Samples x features matrix.

    Returns
    -------
    numpy.ndarray
        Samples x 2 coordinates.
    """
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _Vt = np.linalg.svd(Xc, full_matrices=False)
    return U[:, :2] * S[:2]


def plot_activity_landscape_3d(
    variants_df: pd.DataFrame,
    mutations_df: pd.DataFrame,
    title: str = "3D Activity Landscape",
    score_col: str = "activity_score_log2",
):
    """
    Create a 3D activity landscape plot.

    Parameters
    ----------
    variants_df:
        Must contain 'variant_id', 'generation', and score_col.
    mutations_df:
        Must contain 'variant_id' and 'position'.
    title:
        Figure title.
    score_col:
        Activity score column name (log2).

    Returns
    -------
    plotly.graph_objs._figure.Figure

    Raises
    ------
    ValueError
        If required columns are missing or there is no overlap between variants and mutations.
    """
    required = {"variant_id", "generation", score_col}
    missing = required - set(variants_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    feat = _build_mutation_feature_matrix(mutations_df)

    meta = variants_df[["variant_id", "generation", score_col]].copy()
    meta[score_col] = pd.to_numeric(meta[score_col], errors="coerce")
    meta["generation"] = pd.to_numeric(meta["generation"], errors="coerce")
    meta = meta.dropna(subset=[score_col, "generation"])

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