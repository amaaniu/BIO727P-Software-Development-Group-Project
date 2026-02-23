"""
Activity Score distribution plots.

Required output (per brief):
- per-generation distribution plot of the Activity Score.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px


def plot_activity_violin(
    df: pd.DataFrame,
    title: str = "Activity Score distribution by generation",
    score_col: str = "activity_score_log2",
    show_points: bool = True,
):
    """
    Plot a violin distribution of Activity Score per generation.

    Parameters
    ----------
    df:
        Variants dataframe.
    title:
        Figure title.
    score_col:
        Name of the score column (default 'activity_score_log2').
    show_points:
        If True, overlay individual points (useful for spotting outliers).

    Returns
    -------
    plotly.graph_objs._figure.Figure
        A Plotly figure suitable for embedding in Flask templates or exporting.

    Raises
    ------
    ValueError
        If required columns are missing.
    """
    required = {"generation", score_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    tmp = df.copy()
    tmp["generation"] = pd.to_numeric(tmp["generation"], errors="coerce")
    tmp[score_col] = pd.to_numeric(tmp[score_col], errors="coerce")
    tmp = tmp.dropna(subset=["generation", score_col])

    gen_order = sorted(tmp["generation"].unique().tolist())
    tmp["generation"] = tmp["generation"].astype(int).astype(str)
    gen_order_str = [str(int(g)) for g in gen_order]

    fig = px.violin(
        tmp,
        x="generation",
        y=score_col,
        category_orders={"generation": gen_order_str},
        box=True,
        points="all" if show_points else False,
        title=title,
    )

    fig.update_layout(
        xaxis_title="Generation",
        yaxis_title="Activity Score (log2 normalised ratio)",
        template="simple_white",
    )
    fig.update_xaxes(showgrid=True, gridwidth=1)
    fig.update_yaxes(showgrid=True, gridwidth=1)

    return fig