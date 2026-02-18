# violin plot for activity score distribution per generation

import pandas as pd
import plotly.express as px


def plot_activity_violin(
    df: pd.DataFrame,
    title: str = "Activity Score distribution by generation",
    score_col: str = "activity_score_log2",
    show_points: bool = True,
):
    # validating required columns
    required = {"generation", score_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ensuring correct types/order
    df = df.copy()
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df = df.dropna(subset=["generation", score_col])

    # ordering generations numerically
    gen_order = sorted(df["generation"].dropna().unique().tolist())

    # plotly likes categorical x labels for spacing
    df["generation"] = df["generation"].astype(int).astype(str)
    gen_order_str = [str(int(g)) for g in gen_order]

    fig = px.violin(
        df,
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

    # gridlines 
    fig.update_xaxes(showgrid=True, gridwidth=1)
    fig.update_yaxes(showgrid=True, gridwidth=1)

    return fig
