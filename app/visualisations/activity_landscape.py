from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Features and mutation counts

def _build_position_feature_matrix(
    mutations_df: pd.DataFrame,
    all_variant_ids: pd.Index,
) -> pd.DataFrame:
    """
    Convert mutation records into a binary feature matrix (variant × position).

    Each column represents one mutated position ("pos_<int>").
    Variants with no mutations get an all-zero row.

    Parameters
    ----------
    mutations_df:
        Must contain 'variant_id' and 'position'. Extra columns are ignored.
    all_variant_ids:
        Full list of variant IDs so zero-mutation variants are included.

    Returns
    -------
    pd.DataFrame
        Binary feature matrix, index = variant_id (str).
    """
    required = {"variant_id", "position"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"mutations_df is missing columns: {sorted(missing)}")

    df = mutations_df[["variant_id", "position"]].copy()
    df["variant_id"] = df["variant_id"].astype(str)
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["position"])
    df["position"] = df["position"].astype(int)

    df["feat"] = "pos_" + df["position"].astype(str)
    df["present"] = 1.0

    wide = (
        df.pivot_table(
            index="variant_id",
            columns="feat",
            values="present",
            aggfunc="max",
            fill_value=0.0,
        )
        .astype(float)
    )

    # Ensure every variant appears (no-mutation variants → zero row)
    wide = wide.reindex(all_variant_ids.astype(str), fill_value=0.0)
    return wide


def _mutation_counts(
    mutations_df: pd.DataFrame,
    all_variant_ids: pd.Index,
) -> pd.Series:
    """
    Map variant_id → mutation count (records in mutations_df).

    If a 'mutation_type' column exists, rows labeled 'synonymous' are excluded.
    Otherwise all rows are counted.

    Parameters
    ----------
    mutations_df:
        Mutation-level dataframe.
    all_variant_ids:
        Full list of variant IDs (ensures missing variants -> 0).

    Returns
    -------
    pd.Series
        Index: variant_id (str), Values: integer counts.
    """
    df = mutations_df.copy()
    if df.empty:
        return pd.Series(0, index=all_variant_ids.astype(str))

    df["variant_id"] = df["variant_id"].astype(str)

    if "mutation_type" in df.columns:
        mt = df["mutation_type"].astype(str).str.lower()
        df = df[mt != "synonymous"]

    counts = df.groupby("variant_id").size()
    return counts.reindex(all_variant_ids.astype(str), fill_value=0)

# Dimensionality reduction

def _pca_2d(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Project samples into 2D using PCA via SVD (no sklearn dependency).

    Parameters
    ----------
    X:
        Shape (n_samples, n_features).

    Returns
    -------
    coords:
        Shape (n_samples, 2) PCA coordinates.
    evr:
        Shape (2,) explained variance ratio for PC1 and PC2.

    Raises
    ------
    ValueError
        If fewer than 2 samples are provided.
    """
    if X.ndim != 2:
        raise ValueError("X must be 2D (samples × features).")
    n_samples = X.shape[0]
    if n_samples < 2:
        raise ValueError(f"PCA requires at least 2 samples; got {n_samples}.")

    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)

    coords = U[:, :2] * S[:2]

    total = float(np.sum(S**2))  # use ALL singular values for denominator
    evr = (S[:2] ** 2) / total if total > 0 else np.array([0.0, 0.0])

    return coords, evr

# Surface smoothing

def _gaussian_surface(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    *,
    grid_size: int = 120,
    bandwidth: float | None = None,
    bounds_percentile: tuple[float, float] = (0.5, 99.5),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Smooth scatter z-values onto a regular 2D grid using Gaussian kernel weighting.

    Parameters
    ----------
    x, y, z:
        1D arrays of equal length.
    grid_size:
        Resolution of the output grid.
    bandwidth:
        Gaussian kernel width. None -> heuristic.
    bounds_percentile:
        Percentile bounds for grid extents (reduces outlier empty space).

    Returns
    -------
    Xg, Yg, Zg:
        2D arrays for go.Surface.
    """
    if len(x) == 0:
        raise ValueError("No points supplied to surface smoother.")

    lo, hi = bounds_percentile
    xmin, xmax = np.percentile(x, [lo, hi])
    ymin, ymax = np.percentile(y, [lo, hi])

    xi = np.linspace(xmin, xmax, grid_size)
    yi = np.linspace(ymin, ymax, grid_size)
    Xg, Yg = np.meshgrid(xi, yi)

    if bandwidth is None:
        sx = float(np.std(x)) or 1.0
        sy = float(np.std(y)) or 1.0
        bandwidth = 0.20 * max(sx, sy)

    bw2 = max(float(bandwidth) ** 2, 1e-12)

    dx = Xg[..., None] - x[None, None, :]
    dy = Yg[..., None] - y[None, None, :]
    d2 = dx * dx + dy * dy

    w = np.exp(-0.5 * d2 / bw2)
    wsum = w.sum(axis=2)
    Zg = (w * z[None, None, :]).sum(axis=2) / np.maximum(wsum, 1e-12)

    return Xg, Yg, Zg


def _aggregate_on_plane(
    df: pd.DataFrame,
    *,
    xcol: str,
    ycol: str,
    zcol: str,
    round_ndigits: int = 3,
) -> pd.DataFrame:
    """
    Aggregate points that are effectively identical on the 2D PCA plane.

    PCA on sparse binary features often yields repeated/near-repeated (x, y)
    coordinates. Aggregating stabilizes smoothing and reduces artefacts.

    Parameters
    ----------
    df:
        Source dataframe containing xcol, ycol, zcol.
    xcol, ycol, zcol:
        Column names for plane coordinates and scalar value.
    round_ndigits:
        Rounding precision used to define "same location".

    Returns
    -------
    pd.DataFrame
        Columns: [xcol, ycol, zcol, 'n'] where 'n' is cluster size.
    """
    d = df[[xcol, ycol, zcol]].copy()
    d["_x"] = d[xcol].round(round_ndigits)
    d["_y"] = d[ycol].round(round_ndigits)

    out = (
        d.groupby(["_x", "_y"], as_index=False)
        .agg(
            **{
                xcol: ("_x", "first"),
                ycol: ("_y", "first"),
                zcol: (zcol, "mean"),
                "n": (zcol, "size"),
            }
        )
    )
    return out

# Main plotting

def plot_activity_landscape_3d(
    variants_df: pd.DataFrame,
    mutations_df: pd.DataFrame,
    *,
    title: str = "3D Activity Landscape (PCA on mutation positions)",
    score_col: str = "activity_score_log2",
    grid_size: int = 120,
    bandwidth: float | None = None,
    jitter: float = 0.02,
    top_n: int = 10,
) -> go.Figure:
    """
    Create a 3D activity landscape using PCA on mutation-position features.

    Adds:
    - Surface smoothing performed on an aggregated PCA plane (reduces artefacts).
    - Optional "Aggregated clusters" view (readable overview).
    - Top-N labels shown only for "All generations" and "Points only".
    """
    required = {"variant_id", "generation", score_col}
    missing = required - set(variants_df.columns)
    if missing:
        raise ValueError(f"variants_df is missing columns: {sorted(missing)}")

    id_cols = ["variant_id", "generation", score_col]
    if "experiment_variant_id" in variants_df.columns:
        id_cols.append("experiment_variant_id")
    meta = variants_df[id_cols].copy()
    meta["variant_id"] = meta["variant_id"].astype(str)
    if "experiment_variant_id" in meta.columns:
        meta["display_variant_id"] = meta["experiment_variant_id"].fillna(meta["variant_id"]).astype(str)
        hover_id_label = "experiment_variant_id"
    else:
        meta["display_variant_id"] = meta["variant_id"]
        hover_id_label = "variant_id"
    meta["generation"] = pd.to_numeric(meta["generation"], errors="coerce")
    meta[score_col] = pd.to_numeric(meta[score_col], errors="coerce")
    meta = meta.dropna(subset=["generation", score_col])

    if len(meta) < 2:
        raise ValueError(f"Need at least 2 valid variants; got {len(meta)}.")

    # Score handling: avoid double-log
    if "log2" in score_col.lower():
        meta["log2_score"] = meta[score_col].astype(float)
    else:
        eps = 1e-6
        meta["log2_score"] = np.log2(np.maximum(meta[score_col].astype(float), eps))

    # Feature matrix (includes no-mutation variants)
    feat = _build_position_feature_matrix(mutations_df, all_variant_ids=meta["variant_id"])
    X = feat.to_numpy(dtype=float)

    coords, evr = _pca_2d(X)
    meta["dim1"] = coords[:, 0]
    meta["dim2"] = coords[:, 1]

    # Jitter (display only)
    rng = np.random.default_rng(0)
    meta["dim1_plot"] = meta["dim1"] + rng.normal(0, jitter, size=len(meta))
    meta["dim2_plot"] = meta["dim2"] + rng.normal(0, jitter, size=len(meta))

    # Mutation counts (for marker size)
    counts = _mutation_counts(mutations_df, all_variant_ids=meta["variant_id"])
    meta["n_mutations"] = counts.values

    # --- Surface smoothing on aggregated plane ---
    plane = _aggregate_on_plane(meta, xcol="dim1", ycol="dim2", zcol="log2_score", round_ndigits=3)

    Xg, Yg, Zg = _gaussian_surface(
        plane["dim1"].to_numpy(),
        plane["dim2"].to_numpy(),
        plane["log2_score"].to_numpy(),
        grid_size=grid_size,
        bandwidth=bandwidth,
    )

    fig = go.Figure()

    # Trace 0: surface
    fig.add_trace(
        go.Surface(
            x=Xg,
            y=Yg,
            z=Zg,
            surfacecolor=Zg,
            colorbar=dict(title="Activity (log2)"),
            contours=dict(z=dict(show=True, usecolormap=True, project_z=True)),
            opacity=0.88,
            name="Activity surface",
            showscale=True,
        )
    )
    fig.data[0].update(
        opacity=0.72,
        colorbar=dict(
            title="Activity (log2)",
            thickness=14,
            len=0.70,
            x=1.02,
            y=0.50,
        ),
        contours=dict(
            z=dict(show=True, usecolormap=True, project_z=True, width=1)
        ),
    )

    # Traces 1..N: one scatter per generation (detailed view)
    gens = sorted(meta["generation"].unique())
    for g in gens:
        df_g = meta.loc[meta["generation"] == g].copy()
        sizes = np.clip(df_g["n_mutations"] * 2 + 4, 4, 20)

        fig.add_trace(
            go.Scatter3d(
                x=df_g["dim1_plot"],
                y=df_g["dim2_plot"],
                z=df_g["log2_score"],
                mode="markers",
                marker=dict(size=sizes, opacity=0.78),
                text=df_g["display_variant_id"],
                customdata=np.stack([df_g["generation"], df_g["n_mutations"], df_g["log2_score"]], axis=1),
                hovertemplate=(
                    f"{hover_id_label}=%{{text}}<br>"
                    "generation=%{customdata[0]:.0f}<br>"
                    "mutations=%{customdata[1]:.0f}<br>"
                    "activity(log2)=%{customdata[2]:.2f}<br>"
                    "PC1=%{x:.2f}<br>"
                    "PC2=%{y:.2f}<extra></extra>"
                ),
                name=f"Gen {int(g)}",
                visible=True,
            )
        )

    # Trace: Top performers (labels) — show only in All/Points-only
    top = meta.nlargest(int(top_n), "log2_score").copy()
    fig.add_trace(
        go.Scatter3d(
            x=top["dim1_plot"],
            y=top["dim2_plot"],
            z=top["log2_score"],
            mode="markers+text",
            marker=dict(
                size=10,
                symbol="diamond",
                color="black",
                opacity=0.9,
                line=dict(width=1.2, color="white"),
            ),
            text=top["display_variant_id"],
            textposition="top center",
            textfont=dict(size=8),
            name=f"Top {int(top_n)}",
            visible=True,
        )
    )

    # Trace: Aggregated cluster points (overview) — hidden by default
    plane_pts = _aggregate_on_plane(meta, xcol="dim1_plot", ycol="dim2_plot", zcol="log2_score", round_ndigits=3)

    fig.add_trace(
        go.Scatter3d(
            x=plane_pts["dim1_plot"],
            y=plane_pts["dim2_plot"],
            z=plane_pts["log2_score"],
            mode="markers",
            marker=dict(
                size=np.clip(3 + np.sqrt(plane_pts["n"]) * 2, 4, 18),
                opacity=0.55,
            ),
            customdata=plane_pts["n"],
            hovertemplate=(
                "Clustered point<br>"
                "PC1=%{x:.2f}<br>"
                "PC2=%{y:.2f}<br>"
                "Mean activity(log2)=%{z:.2f}<br>"
                "Variants in cluster=%{customdata}<extra></extra>"
            ),
            name="Aggregated (clusters)",
            visible=False,
        )
    )

    # --- Dropdown visibility ---
    n_gens = len(gens)
    # Trace order:
    # 0 surface
    # 1..n_gens gen scatters
    # n_gens+1 top labels
    # n_gens+2 aggregated clusters
    top_trace_idx = 1 + n_gens
    agg_trace_idx = 2 + n_gens

    def visible(surface_on: bool, gen_index: int | None) -> list[bool]:
        """
        Visibility list:
          [surface] + [gens...] + [top_labels] + [agg_clusters]

        Rules:
          - Top labels shown only when viewing ALL generations.
          - Aggregated clusters off unless explicitly selected.
        """
        show_all = gen_index is None
        v = [surface_on] + [False] * n_gens + [show_all] + [False]

        if show_all:
            for i in range(n_gens):
                v[1 + i] = True
        else:
            v[1 + gen_index] = True

        return v

    buttons = [
        dict(
            label="All generations",
            method="update",
            args=[{"visible": visible(True, None)}, {"title": title}],
        ),
        dict(
            label="Points only",
            method="update",
            args=[{"visible": visible(False, None)}, {"title": title + " — points only"}],
        ),
        dict(
            label="Aggregated clusters",
            method="update",
            args=[
                {
                    "visible": [True] + [False] * n_gens + [False] + [True]
                },
                {"title": title + " — aggregated clusters"},
            ],
        ),
    ]

    for i, g in enumerate(gens):
        buttons.append(
            dict(
                label=f"Generation {int(g)}",
                method="update",
                args=[
                    {"visible": visible(True, i)},
                    {"title": f"{title} — Gen {int(g)}"},
                ],
            )
        )

    pct1, pct2 = float(evr[0] * 100), float(evr[1] * 100)
    subtitle = f"PCA on mutated positions - PC1 {pct1:.1f}% variance, PC2 {pct2:.1f}% variance"

    fig.update_layout(
        title=dict(
            text=f"{title}<br><sup style='color:#666'>{subtitle}</sup>",
            x=0.5,
            xanchor="center",
            y=0.98,
            yanchor="top",
        ),
        template="simple_white",
        height=720,
        margin=dict(l=10, r=90, t=90, b=10),
        showlegend=False,
        scene=dict(
            xaxis=dict(
                title=f"Sequence diversity PC1 ({pct1:.1f}%)",
                showspikes=False,
                gridcolor="rgba(0,0,0,0.08)",
                zerolinecolor="rgba(0,0,0,0.15)",
            ),
            yaxis=dict(
                title=f"Sequence diversity PC2 ({pct2:.1f}%)",
                showspikes=False,
                gridcolor="rgba(0,0,0,0.08)",
                zerolinecolor="rgba(0,0,0,0.15)",
            ),
            zaxis=dict(
                title="Activity score (log2)",
                showspikes=False,
                gridcolor="rgba(0,0,0,0.08)",
                zerolinecolor="rgba(0,0,0,0.15)",
            ),
            aspectmode="manual",
            aspectratio=dict(x=1.1, y=1.1, z=0.75),
            camera=dict(eye=dict(x=1.25, y=1.35, z=0.85)),
        ),
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                buttons=buttons,
                x=0.01,
                y=1.14,
                xanchor="left",
                yanchor="top",
                showactive=True,
                bgcolor="white",
                bordercolor="rgba(0,0,0,0.25)",
                borderwidth=1,
            )
        ],
    )

    return fig
