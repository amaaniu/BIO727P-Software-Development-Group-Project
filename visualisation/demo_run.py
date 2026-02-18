# one-command demo script to generate outputs
# run from repo root: python -m visualisation.demo_run
# easier: python -m visualisation.demo_run --source db_export --variants_json path --mutations_json path

from __future__ import annotations

import argparse

from visualisation.data_sources import get_variants, get_mutations
from visualisation.activityscore_plot import plot_activity_violin
from visualisation.trends import plot_activity_median_trend
from visualisation.top10_table_only import compute_top10
from visualisation.reporting import save_plotly_figure, save_table_csv, save_top10_table_png

# bonus visuals
from visualisation.mutation_fingerprint import plot_mutation_fingerprint
from visualisation.activity_landscape_3d import plot_activity_landscape_3d


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="dummy", choices=["dummy", "db_export"])
    parser.add_argument("--variants_json", default=None)
    parser.add_argument("--mutations_json", default=None)
    args = parser.parse_args()

    print("Running visualisation demo...")

    if args.source == "dummy":
        df = get_variants(source="dummy")
        muts_df = None

    else:
        df = get_variants(source="db_export", variants_json_path=args.variants_json)
        muts_df = get_mutations(source="db_export", mutations_json_path=args.mutations_json)

    score_col = "activity_score_log2"

    # generate violin plot
    fig = plot_activity_violin(df, score_col=score_col)
    html_path, png_path = save_plotly_figure(fig, out_prefix="activity_violin")

    # generate median trend plot
    trend_fig = plot_activity_median_trend(df, score_col=score_col, show_iqr=True)
    trend_html, trend_png = save_plotly_figure(trend_fig, out_prefix="activity_median_trend")

    # generate top 10 table
    top10 = compute_top10(df)
    csv_path = save_table_csv(top10, out_name="top10_variants")
    png_table_path = save_top10_table_png(top10, out_name="top10_variants_table")

    print("Outputs saved:")
    print(f"- {html_path}")
    print(f"- {png_path}")
    print(f"- {trend_html}")
    print(f"- {trend_png}")
    print(f"- {csv_path}")
    print(f"- {png_table_path}")

    # bonus visuals
    if muts_df is not None and not muts_df.empty:
        best_variant_id = top10.loc[0, "variant_id"]

        fp_fig = plot_mutation_fingerprint(
            muts_df,
            variant_id=best_variant_id,
            title=f"Mutation fingerprint (variant {best_variant_id})",
        )
        fp_html, fp_png = save_plotly_figure(fp_fig, out_prefix="mutation_fingerprint")
        print(f"- {fp_html}")
        print(f"- {fp_png}")

        land_fig = plot_activity_landscape_3d(
            df,
            muts_df,
            score_col=score_col,
            title="3D Activity Landscape (PCA on mutation positions)",
        )
        land_html, land_png = save_plotly_figure(land_fig, out_prefix="activity_landscape_3d")
        print(f"- {land_html}")
        print(f"- {land_png}")


if __name__ == "__main__":
    main()
