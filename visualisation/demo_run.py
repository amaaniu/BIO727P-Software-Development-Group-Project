# one-command demo script to generate outputs
# run from repo root: python -m visualisation.demo_run

from visualisation.data_sources import get_variants
from visualisation.activityscore_plot import plot_activity_violin
from visualisation.top10_table_only import compute_top10
from visualisation.reporting import save_plotly_figure, save_table_csv, save_top10_table_png


def main():

    print("Running visualisation demo...")

    # get dummy data
    df = get_variants(source="dummy")

    # generate violin plot
    fig = plot_activity_violin(df)
    html_path, png_path = save_plotly_figure(fig, out_prefix="activity_violin")

    # generate top 10 table
    top10 = compute_top10(df)
    csv_path = save_table_csv(top10, out_name="top10_variants")
    png_table_path = save_top10_table_png(top10, out_name="top10_variants_table")

    print("Outputs saved:")
    print(f"- {html_path}")
    print(f"- {png_path}")
    print(f"- {csv_path}")
    print(f"- {png_table_path}")


if __name__ == "__main__":
    main()
