from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_mutation_fingerprint(
    introduced_df: pd.DataFrame,
    *,
    protein_length: Optional[int] = None,
    title: str = "Mutation fingerprint (introduced per generation)",
    top_k: int = 60,
    jitter_y: float = 0.12,
    bin_size: int = 5,
) -> go.Figure:
    """
    Interactive mutation fingerprint with toggle between:

    - Exact markers (readable subset)
    - Density heatmap
    - Heatmap + sample markers
    """

    required = {"generation", "position", "wt_residue", "mutant_residue"}
    missing = required - set(introduced_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = introduced_df.copy()
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["generation", "position"])
    df["generation"] = df["generation"].astype(int)
    df["position"] = df["position"].astype(int)

    if df.empty:
        raise ValueError("No valid mutation records.")

    if protein_length is None:
        protein_length = int(df["position"].max())

    df["mutation_label"] = (
        df["wt_residue"].astype(str)
        + df["position"].astype(str)
        + df["mutant_residue"].astype(str)
    )

    collapsed = (
        df.groupby(["generation", "position"], as_index=False)
        .agg(
            mutation_label=("mutation_label", lambda s: ", ".join(sorted(set(s)))),
            collision_count=("mutation_label", "size"),
        )
    )

    generations = sorted(collapsed["generation"].unique())

    fig = go.Figure()

    # Background bars
    for g in generations:
        fig.add_shape(
            type="rect",
            x0=0,
            x1=protein_length,
            y0=g - 0.18,
            y1=g + 0.18,
            fillcolor="rgba(200,200,200,0.25)",
            line=dict(color="rgba(150,150,150,0.6)", width=1),
            layer="below",
        )

    # MARKERS TRACE (Exact but capped for readability)
  
    rng = np.random.default_rng(0)

    marker_traces = []
    for g in generations:
        dfg = collapsed[collapsed["generation"] == g].copy()

        if len(dfg) > top_k:
            dfg = dfg.sort_values("collision_count", ascending=False).head(top_k)

        yj = g + rng.normal(0, jitter_y, size=len(dfg))

        marker_traces.append(
            go.Scatter(
                x=dfg["position"],
                y=yj,
                mode="markers",
                name=f"Gen {g}",
                marker=dict(
                    symbol="triangle-down",
                    size=np.clip(7 + 1.5 * dfg["collision_count"], 7, 16),
                    line=dict(width=1, color="black"),
                    opacity=0.8,
                ),
                customdata=np.stack(
                    [dfg["mutation_label"], dfg["collision_count"]],
                    axis=1,
                ),
                hovertemplate=(
                    "Generation=%{y:.0f}<br>"
                    "Position=%{x}<br>"
                    "Introduced=%{customdata[0]}<br>"
                    "Collisions=%{customdata[1]}<extra></extra>"
                ),
                visible=True,  # default view
            )
        )

    # HEATMAP TRACE (Density view)
   
    bins = np.arange(0, protein_length + bin_size, bin_size)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    heat = np.zeros((len(generations), len(bin_centers)), dtype=float)
    gen_to_i = {g: i for i, g in enumerate(generations)}

    for _, row in collapsed.iterrows():
        g = int(row["generation"])
        p = int(row["position"])
        j = np.searchsorted(bins, p, side="right") - 1
        if 0 <= j < heat.shape[1]:
            heat[gen_to_i[g], j] += 1

    heatmap_trace = go.Heatmap(
        x=bin_centers,
        y=generations,
        z=heat,
        colorbar=dict(title=f"Count / {bin_size} aa"),
        hovertemplate=(
            "Generation=%{y}<br>"
            f"Position bin=%{{x:.0f}}±{bin_size/2:.0f}<br>"
            "Count=%{z:.0f}<extra></extra>"
        ),
        visible=False,
    )

    # Sample markers (overlay for hybrid mode)
    sample = collapsed.sample(min(len(collapsed), 400), random_state=0)
    yj_sample = sample["generation"].to_numpy() + rng.normal(
        0, jitter_y, size=len(sample)
    )

    hybrid_marker_trace = go.Scatter(
        x=sample["position"],
        y=yj_sample,
        mode="markers",
        marker=dict(symbol="triangle-down", size=6, opacity=0.4),
        showlegend=False,
        hoverinfo="skip",
        visible=False,
    )

    # Add all traces
    for t in marker_traces:
        fig.add_trace(t)

    fig.add_trace(heatmap_trace)
    fig.add_trace(hybrid_marker_trace)

    n_marker = len(marker_traces)
    heat_idx = n_marker
    hybrid_idx = n_marker + 1

    # DROPDOWN MENU
    def visibility(markers, heatmap, hybrid):
        vis = [False] * (n_marker + 2)
        for i in range(n_marker):
            vis[i] = markers
        vis[heat_idx] = heatmap
        vis[hybrid_idx] = hybrid
        return vis

    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                x=0.01,
                y=1.12,
                buttons=[
                    dict(
                        label="Markers (exact)",
                        method="update",
                        args=[{"visible": visibility(True, False, False)}],
                    ),
                    dict(
                        label="Heatmap (density)",
                        method="update",
                        args=[{"visible": visibility(False, True, False)}],
                    ),
                    dict(
                        label="Heatmap + sample markers",
                        method="update",
                        args=[{"visible": visibility(False, True, True)}],
                    ),
                ],
            )
        ]
    )

    fig.update_layout(
        title=title,
        template="simple_white",
        legend_title="Generation",
        margin=dict(l=70, r=30, t=80, b=70),
    )

    fig.update_xaxes(
        title="Amino Acid Position",
        range=[0, protein_length],
        showgrid=True,
        rangeslider=dict(visible=True),
    )

    fig.update_yaxes(
        title="Generation",
        tickmode="array",
        tickvals=generations,
        ticktext=[str(g) for g in generations],
        range=[min(generations) - 1, max(generations) + 1],
        showgrid=False,
    )

    return fig
