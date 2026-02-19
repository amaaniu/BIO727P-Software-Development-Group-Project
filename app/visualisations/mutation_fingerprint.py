# mutation fingerprinting by generation
# - shows amino acid mutation positions for a selected variant

import pandas as pd
import plotly.express as px


def plot_mutation_fingerprint(
    mutations_df: pd.DataFrame,
    variant_id,
    title: str = "Mutation fingerprint",
):
    # required columns
    required = {"variant_id", "generation", "position", "wt_residue", "mutant_residue"}
    missing = required - set(mutations_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = mutations_df.copy()
    df = df[df["variant_id"] == variant_id].copy()

    if df.empty:
        raise ValueError(f"No mutations found for variant_id={variant_id}")

    # basic typing
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["generation", "position"])

    # label for hover
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

    # gridlines ON
    fig.update_xaxes(showgrid=True, gridwidth=1)
    fig.update_yaxes(showgrid=True, gridwidth=1)

    return fig
