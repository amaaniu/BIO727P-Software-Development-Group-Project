from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go


def plot_mutation_fingerprint(
    introduced_df: pd.DataFrame,
    *,
    protein_length: Optional[int] = None,
    title: str = "Mutation fingerprint (introduced per generation)",
    show_text: bool = False,
    max_text_per_generation: int = 12,
) -> go.Figure:
    """
    Plot a mutational fingerprint where each row is a generation and points are mutations
    introduced in that generation (not all mutations present in the final variant).

    Expected columns in introduced_df:
      - generation (int-like)
      - position (int-like, 1-based amino acid position)
      - wt_residue (str, single-letter)
      - mutant_residue (str, single-letter)

    Notes:
      - Stacks generations on the y-axis (easy to interpret, avoids overlap).
      - Defaults to hover-only labels to prevent clutter; enable show_text if desired.
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
        raise ValueError("No introduced mutations to plot (introduced_df is empty after cleaning).")

    # Protein length fallback
    if protein_length is None:
        protein_length = int(df["position"].max())

    if not isinstance(protein_length, int) or protein_length <= 0:
        raise ValueError("protein_length must be a positive integer")

    # Build labels like "E35V"
    df["mutation_label"] = (
        df["wt_residue"].astype(str).str.strip()
        + df["position"].astype(str)
        + df["mutant_residue"].astype(str).str.strip()
    )

    # If multiple mutations collide at same (generation, position), join labels
    df = (
        df.groupby(["generation", "position"], as_index=False)
        .agg(mutation_label=("mutation_label", lambda s: ", ".join(sorted(set(s)))))
    )

    gens = sorted(df["generation"].unique())

    fig = go.Figure()

    # Draw one "protein bar" per generation row 
    bar_half_height = 0.18
    for g in gens:
        fig.add_shape(
            type="rect",
            x0=0,
            x1=protein_length,
            y0=g - bar_half_height,
            y1=g + bar_half_height,
            fillcolor="lightgrey",
            line=dict(color="grey", width=1),
            layer="below",
        )

    # One trace per generation (stacked y prevents overlap)
    for g in gens:
        dfg = df[df["generation"] == g].sort_values("position")

        # show text labels, but cap per generation to avoid soup
        text = None
        mode = "markers"
        if show_text:
            mode = "markers+text"
            text = dfg["mutation_label"].where(
                dfg.reset_index(drop=True).index < max_text_per_generation, ""
            )

        fig.add_trace(
            go.Scatter(
                x=dfg["position"],
                y=[g] * len(dfg),
                mode=mode,
                name=f"Gen {g}",
                text=text,
                textposition="top center",
                textfont=dict(size=10),
                marker=dict(
                    symbol="triangle-down",
                    size=11,
                    line=dict(width=1, color="black"),
                ),
                hovertemplate=(
                    "Generation=%{y}<br>"
                    "Position=%{x}<br>"
                    "Introduced=%{customdata}<extra></extra>"
                ),
                customdata=dfg["mutation_label"],
            )
        )

    fig.update_layout(
        title=title,
        template="simple_white",
        margin=dict(l=70, r=30, t=70, b=60),
        legend=dict(title="Generation"),
    )

    fig.update_xaxes(
        title="Amino Acid Position",
        range=[0, protein_length],
        showgrid=True,
        zeroline=False,
    )

    fig.update_yaxes(
        title="Generation",
        tickmode="array",
        tickvals=gens,
        ticktext=[str(g) for g in gens],
        showgrid=False,
        zeroline=False,
        autorange=False,
        range=[min(gens) - 1, max(gens) + 1],
    )

    return fig