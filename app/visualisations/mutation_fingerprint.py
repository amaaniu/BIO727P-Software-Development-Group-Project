"""
Mutation fingerprint visualisation.

Bonus visual: show specific amino acid changes and the generation introduced.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def plot_mutation_fingerprint(
    mutations_df: pd.DataFrame,
    variant_id: Any,
    title: str = "Mutation fingerprint",
) -> go.Figure:
    """
    Fingerprint plot of mutation position vs generation for a selected variant.

    Parameters
    ----------
    mutations_df:
        DataFrame containing per-mutation rows.
    variant_id:
        Variant identifier to plot (kept flexible to handle int/str IDs).
    title:
        Figure title.

    Returns
    -------
    plotly.graph_objects.Figure

    Raises
    ------
    ValueError
        If required columns are missing or the variant has no mutation rows.
    """
    required = {"variant_id", "generation", "position", "wt_residue", "mutant_residue"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = mutations_df.copy()
    df = df[df["variant_id"] == variant_id].copy()
    if df.empty:
        raise ValueError(f"No mutations found for variant_id={variant_id}")

    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["generation", "position"])
    df["generation"] = df["generation"].astype(int)
    df["position"] = df["position"].astype(int)

    df["mutation_label"] = (
        df["wt_residue"].astype(str)
        + df["position"].astype(str)
        + df["mutant_residue"].astype(str)
    )

    # If multiple mutations occur at the same (position, generation), join labels.
    cell = (
        df.groupby(["generation", "position"])["mutation_label"]
        .apply(lambda s: ",".join(sorted(set(s.astype(str)))))
        .reset_index()
    )

    generations = sorted(cell["generation"].unique())
    positions = sorted(cell["position"].unique())

    z = pd.DataFrame(index=generations, columns=positions, dtype=float)
    text = pd.DataFrame(index=generations, columns=positions, dtype=object)

    # Fill: colour is generation, text is mutation label
    for _, r in cell.iterrows():
        g = int(r["generation"])
        p = int(r["position"])
        z.loc[g, p] = g
        text.loc[g, p] = r["mutation_label"]

    z = z.to_numpy()
    text = text.fillna("").to_numpy()

    fig = go.Figure(
        data=go.Heatmap(
            x=positions,
            y=generations,
            z=z,
            text=text,
            hovertemplate=(
                "Position=%{x}<br>"
                "Generation=%{y}<br>"
                "Mutation=%{text}<extra></extra>"
            ),
            colorscale="Blues",
            colorbar=dict(title="Generation"),
            zmin=min(generations),
            zmax=max(generations),
        )
    )

    fig.update_traces(
        texttemplate="%{text}",
        textfont=dict(size=10),
    )

    fig.update_layout(
        title=title,
        xaxis_title="Amino acid position",
        yaxis_title="Generation introduced",
        template="simple_white",
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, tickmode="auto")
    fig.update_yaxes(showgrid=True, gridwidth=1, autorange="reversed")

    return fig