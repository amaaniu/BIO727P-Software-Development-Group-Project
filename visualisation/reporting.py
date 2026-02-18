# functions for saving/exporting visualisation outputs

from pathlib import Path
import pandas as pd


# location for outputs (locally)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# save a plotly figure as html (and png if kaleido is installed)
def save_plotly_figure(fig, out_prefix: str):

    # html output
    html_path = OUTPUT_DIR / f"{out_prefix}.html"
    fig.write_html(str(html_path))

    # png output (optional; requires kaleido install)
    png_path = OUTPUT_DIR / f"{out_prefix}.png"
    try:
        fig.write_image(str(png_path), scale=2)
    except Exception as e:
        png_path = None
        print(f"PNG export skipped (install kaleido to enable). Details: {e}")

    return str(html_path), (str(png_path) if png_path else None)


# save a dataframe to csv
def save_table_csv(df: pd.DataFrame, out_name: str):

    csv_path = OUTPUT_DIR / f"{out_name}.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)


# save top 10 table as a png image (requires matplotlib)
def save_top10_table_png(top10: pd.DataFrame, out_name: str = "top10_variants_table"):

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")

    display_df = top10.copy()

    # format numeric columns nicely
    if "activity_score_log2" in display_df.columns:
        display_df["activity_score_log2"] = display_df["activity_score_log2"].map(lambda x: f"{x:.3f}")

    if "protein_yield" in display_df.columns:
        display_df["protein_yield"] = display_df["protein_yield"].map(lambda x: f"{x:.1f}")

    if "dna_yield" in display_df.columns:
        display_df["dna_yield"] = display_df["dna_yield"].map(lambda x: f"{x:.1f}")

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    ax.set_title("Top 10 variants by activity score (log2)", pad=12)

    png_path = OUTPUT_DIR / f"{out_name}.png"
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)
    plt.close(fig)

    return str(png_path)
