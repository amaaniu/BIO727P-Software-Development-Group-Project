from __future__ import annotations
from typing import Optional
import pandas as pd
import plotly.graph_objects as go


def plot_mutation_fingerprint(
    introduced_df: pd.DataFrame,
    *,
    protein_length: Optional[int] = None,
    title: str = "Mutation fingerprint (introduced per generation)",
) -> go.Figure:
    """
    Plot amino acid mutations introduced at each generation.

    Rows = generation
    X-axis = amino acid position
    Markers = introduced mutations (triangle-down)

    Required columns:
        generation
        position
        wt_residue
        mutant_residue
    """

    required = {"generation", "position", "wt_residue", "mutant_residue"}
    missing = required - set(introduced_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = introduced_df.copy()

    df["generation"] = pd.to_numeric(df["generation"], errors="coerce").astype(int)
    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype(int)

    if protein_length is None:
        protein_length = int(df["position"].max())

    df["mutation_label"] = (
        df["wt_residue"].astype(str)
        + df["position"].astype(str)
        + df["mutant_residue"].astype(str)
    )

    # Collapse collisions at same (generation, position)
    df = (
        df.groupby(["generation", "position"], as_index=False)
        .agg(mutation_label=("mutation_label", lambda s: ", ".join(sorted(set(s)))))
    )

    generations = sorted(df["generation"].unique())

    fig = go.Figure()

    # Draw protein bars per generation row
    for g in generations:
        fig.add_shape(
            type="rect",
            x0=0,
            x1=protein_length,
            y0=g - 0.18,
            y1=g + 0.18,
            fillcolor="lightgrey",
            line=dict(color="grey", width=1),
            layer="below",
        )

    # Plot mutations
    for g in generations:
        dfg = df[df["generation"] == g]

        fig.add_trace(
            go.Scatter(
                x=dfg["position"],
                y=[g] * len(dfg),
                mode="markers",
                name=f"Gen {g}",
                marker=dict(
                    symbol="triangle-down",
                    size=11,
                    line=dict(width=1, color="black"),
                ),
                customdata=dfg["mutation_label"],
                hovertemplate=(
                    "Generation=%{y}<br>"
                    "Position=%{x}<br>"
                    "Introduced=%{customdata}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title,
        template="simple_white",
        legend_title="Generation",
        margin=dict(l=70, r=30, t=70, b=60),
    )

    fig.update_xaxes(
        title="Amino Acid Position",
        range=[0, protein_length],
        showgrid=True,
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