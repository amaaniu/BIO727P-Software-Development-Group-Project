import pandas as pd
import plotly.express as px

from visualisation.data_sources import get_variants


# violin plot for activity score distribution per generation
def plot_activity_violin(
    df: pd.DataFrame,
    title: str = "Activity Score distribution by generation",
    show_points: bool = True,
):

    # validating required columns (for transition from dummy to real data)
    required = {"generation", "activity_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ensuring correct types/order
    df = df.copy()
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df["activity_score"] = pd.to_numeric(df["activity_score"], errors="coerce")
    df = df.dropna(subset=["generation", "activity_score"])

    # ordering generations numerically
    gen_order = sorted(df["generation"].dropna().unique().tolist())

    # plotly likes categorical x labels for spacing, so convert to string
    df["generation"] = df["generation"].astype(int).astype(str)
    gen_order_str = [str(int(g)) for g in gen_order]

    # violin plot (includes embedded boxplot; shows points if requested)
    fig = px.violin(
        df,
        x="generation",
        y="activity_score",
        category_orders={"generation": gen_order_str},
        box=True,
        points="all" if show_points else False,
        title=title,
    )

    fig.update_layout(
        xaxis_title="Generation",
        yaxis_title="Activity Score (unitless)",
        template="simple_white",
    )

    return fig


# quick local demo run (dummy for now... later will change get_variants source)
if __name__ == "__main__":

    df = get_variants(source="dummy")
    fig = plot_activity_violin(df)
    fig.show()