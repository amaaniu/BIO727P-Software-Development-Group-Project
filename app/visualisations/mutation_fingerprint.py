from __future__ import annotations
from typing import Any

import pandas as pd
import plotly.graph_objects as go


def plot_mutation_fingerprint(
    mutations_df: pd.DataFrame,
    variant_id: Any,
    protein_length: int,
    title: str = "Mutation fingerprint",
    *,
    y_level: float = 0.5,
) -> go.Figure:
    """
    Example-style mutation fingerprint:
    - x: amino-acid position (true spacing)
    - markers: triangle-down, colored by generation (legend per generation)
    - labels: WTposMut (e.g., E35V)
    - grey bar: protein length
    """

    required = {"variant_id", "generation", "position", "wt_residue", "mutant_residue"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if not isinstance(protein_length, int) or protein_length <= 0:
        raise ValueError("protein_length must be a positive integer")

    df = mutations_df.loc[mutations_df["variant_id"] == variant_id].copy()
    if df.empty:
        raise ValueError(f"No mutations found for variant_id={variant_id}")

    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["generation", "position"])
    df["generation"] = df["generation"].astype(int)
    df["position"] = df["position"].astype(int)

    # Build mutation labels like "E35V"
    df["mutation_label"] = (
        df["wt_residue"].astype(str)
        + df["position"].astype(str)
        + df["mutant_residue"].astype(str)
    )

    # groupby aggregation
    df = (
        df.groupby(["generation", "position"], as_index=False)
        .agg(mutation_label=("mutation_label", lambda s: ", ".join(sorted(set(s)))))
    )

    gens = sorted(df["generation"].unique())

    fig = go.Figure()

    # Grey protein bar
    fig.add_shape(
        type="rect",
        x0=0,
        x1=protein_length,
        y0=y_level - 0.08,
        y1=y_level + 0.08,
        fillcolor="lightgrey",
        line=dict(color="grey"),
        layer="below",
    )

    # One trace per generation
    for g in gens:
        dfg = df[df["generation"] == g].sort_values("position")

        fig.add_trace(
            go.Scatter(
                x=dfg["position"],
                y=[y_level] * len(dfg),
                mode="markers+text",
                name=f"Generation {g}",
                text=dfg["mutation_label"],
                textposition="top center",
                textfont=dict(size=10),
                marker=dict(
                    symbol="triangle-down",
                    size=14,
                    line=dict(width=1, color="black"),
                ),
                hovertemplate=(
                    "Position=%{x}<br>"
                    f"Generation={g}<br>"
                    "Mutation=%{text}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title,
        template="simple_white",
        xaxis=dict(
            title="Amino Acid Position",
            range=[0, protein_length],
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            range=[0, 1],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
        ),
        legend=dict(title="Generation"),
        margin=dict(l=60, r=30, t=70, b=60),
    )

    return fig