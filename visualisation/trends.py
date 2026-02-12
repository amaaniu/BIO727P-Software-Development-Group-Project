# summary trend plots across generations (median + IQR)

import pandas as pd
import plotly.graph_objects as go


def summarise_activity_by_generation(df: pd.DataFrame) -> pd.DataFrame:
    # required columns
    required = {"generation", "activity_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    tmp = df.copy()
    tmp["generation"] = pd.to_numeric(tmp["generation"], errors="coerce")
    tmp["activity_score"] = pd.to_numeric(tmp["activity_score"], errors="coerce")
    tmp = tmp.dropna(subset=["generation", "activity_score"])
    tmp["generation"] = tmp["generation"].astype(int)

    summary = (
        tmp.groupby("generation")["activity_score"]
        .agg(
            n="count",
            median="median",
            q25=lambda s: s.quantile(0.25),
            q75=lambda s: s.quantile(0.75),
        )
        .reset_index()
        .sort_values("generation")
    )

    return summary


def plot_activity_median_trend(
    df: pd.DataFrame,
    title: str = "Median Activity Score by generation",
    show_iqr: bool = True,
    show_markers: bool = True,
) -> go.Figure:

    summary = summarise_activity_by_generation(df)

    fig = go.Figure()

    # IQR band
    if show_iqr:
        fig.add_trace(
            go.Scatter(
                x=summary["generation"],
                y=summary["q75"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=summary["generation"],
                y=summary["q25"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                name="IQR (25th–75th)",
                hovertemplate="Gen %{x}<br>IQR: %{y:.3f}<extra></extra>",
            )
        )

    # median line
    fig.add_trace(
        go.Scatter(
            x=summary["generation"],
            y=summary["median"],
            mode="lines+markers" if show_markers else "lines",
            name="Median",
            hovertemplate="Gen %{x}<br>Median: %{y:.3f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Generation",
        yaxis_title="Activity Score (unitless)",
        template="simple_white",
    )

    fig.update_xaxes(dtick=1)

    return fig