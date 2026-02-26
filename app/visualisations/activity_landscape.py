from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _build_mutation_feature_matrix(mutations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert amino-acid substitutions into a wide binary feature matrix.

    Parameters
    ----------
    mutations_df:
        Must contain 'variant_id', 'position',
        'wt_residue', and 'mutant_residue'.

    Returns
    -------
    pandas.DataFrame
        Index: variant_id
        Columns: unique substitution features (e.g. "237_A>V")
        Values: 1 if variant contains that substitution.
    """
    required = {"variant_id", "position", "wt_residue", "mutant_residue"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = mutations_df.copy()
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["position"])
    df["position"] = df["position"].astype(int)

    df["feat"] = (
        df["position"].astype(str)
        + "_"
        + df["wt_residue"].astype(str)
        + ">"
        + df["mutant_residue"].astype(str)
    )

    df["present"] = 1

    wide = (
        df.pivot_table(
            index="variant_id",
            columns="feat",
            values="present",
            aggfunc="max",
            fill_value=0,
        )
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
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    return U[:, :2] * S[:2]


def _gaussian_surface(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    grid_size: int = 70,
    bandwidth: float | None = None,
):
    """
    Smooth z-values over a regular 2D grid using Gaussian kernel weighting.
    """
    xmin, xmax = np.percentile(x, [1, 99])
    ymin, ymax = np.percentile(y, [1, 99])

    xi = np.linspace(xmin, xmax, grid_size)
    yi = np.linspace(ymin, ymax, grid_size)
    Xg, Yg = np.meshgrid(xi, yi)

    if bandwidth is None:
        sx = np.std(x) if np.std(x) > 0 else 1.0
        sy = np.std(y) if np.std(y) > 0 else 1.0
        bandwidth = 0.15 * max(sx, sy)

    dx = Xg[..., None] - x[None, None, :]
    dy = Yg[..., None] - y[None, None, :]
    d2 = dx * dx + dy * dy

    w = np.exp(-0.5 * d2 / (bandwidth * bandwidth))
    wsum = np.sum(w, axis=2)

    Zg = np.sum(w * z[None, None, :], axis=2) / np.maximum(wsum, 1e-12)
    return Xg, Yg, Zg


def plot_activity_landscape_3d(
    variants_df: pd.DataFrame,
    mutations_df: pd.DataFrame,
    title: str = "3D Activity Landscape (Topography)",
    score_col: str = "activity_score_log2",
):
    """
    Create a 3D activity landscape using PCA on substitution features.

    Parameters
    ----------
    variants_df:
        Must contain 'variant_id', 'generation', and score_col.
    mutations_df:
        Must contain substitution-level mutation data.
    title:
        Figure title.
    score_col:
        Activity score column name (log2).

    Returns
    -------
    plotly.graph_objs._figure.Figure
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

    X = merged[feat.columns].to_numpy(dtype=float)
    coords = _pca_2d(X)

    merged["dim1"] = coords[:, 0]
    merged["dim2"] = coords[:, 1]

    Xg, Yg, Zg = _gaussian_surface(
        merged["dim1"].to_numpy(),
        merged["dim2"].to_numpy(),
        merged[score_col].to_numpy(),
    )

    fig = go.Figure()

    fig.add_trace(
        go.Surface(
            x=Xg,
            y=Yg,
            z=Zg,
            colorbar=dict(title="Activity score (log2)"),
            contours=dict(
                z=dict(show=True, usecolormap=True, project_z=True)
            ),
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=merged["dim1"],
            y=merged["dim2"],
            z=merged[score_col],
            mode="markers",
            marker=dict(size=3, opacity=0.6),
            text=merged["variant_id"],
            hovertemplate=(
                "variant_id=%{text}<br>"
                "dim1=%{x:.2f}<br>"
                "dim2=%{y:.2f}<br>"
                "activity=%{z:.2f}<extra></extra>"
            ),
            name="variants",
        )
    )

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="Sequence diversity dim 1 (PCA)",
            yaxis_title="Sequence diversity dim 2 (PCA)",
            zaxis_title="Activity score (log2)",
        ),
        template="simple_white",
    )

    return fig