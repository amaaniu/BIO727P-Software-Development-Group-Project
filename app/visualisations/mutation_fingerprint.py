"""
Mutation fingerprint visualisation.

Bonus visual: show specific amino acid changes and the generation introduced. 
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px


def plot_mutation_fingerprint(
    mutations_df: pd.DataFrame,
    variant_id: Any,
    title: str = "Mutation fingerprint",
):
    """
    Scatter plot of mutation position vs generation for a selected variant.

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
    plotly.graph_objs._figure.Figure

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

    df["mutation_label"] = (
        df["wt_residue"].astype(str)
        + df["position"].astype(int).astype(str)
        + df["mutant_residue"].astype(str)
    )

    fig = px.scatter(
        df,
        x="position",
        y="generation",
        color="generation",
        hover_name="mutation_label",
        title=title,
    )
    fig.update_layout(
        xaxis_title="Amino acid position",
        yaxis_title="Generation introduced",
        template="simple_white",
    )
    fig.update_xaxes(showgrid=True, gridwidth=1)
    fig.update_yaxes(showgrid=True, gridwidth=1)

    return fig