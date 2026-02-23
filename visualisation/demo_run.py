"""
One-command demo runner for the visualisation outputs.

Examples
--------
Dummy data:
    python -m visualisation.demo_run

DB-export JSON:
    python -m visualisation.demo_run --source db_export --variants_json path/to/variants.json --mutations_json path/to/mutations.json
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from visualisation.activity_landscape_3d import plot_activity_landscape_3d
from visualisation.activityscore_plot import plot_activity_violin
from visualisation.data_sources import get_mutations, get_variants
from visualisation.mutation_fingerprint import plot_mutation_fingerprint
from visualisation.reporting import save_plotly_figure, save_table_csv, save_top10_table_png
from visualisation.top10_table_only import compute_top10
from visualisation.trends import plot_activity_median_trend

logger = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    parser = argparse.ArgumentParser(description="Generate visualisation outputs for the DE monitoring portal.")
    parser.add_argument("--source", default="dummy", choices=["dummy", "db_export"])
    parser.add_argument("--variants_json", default=None, help="Path to variants JSON (required if --source db_export).")
    parser.add_argument("--mutations_json", default=None, help="Path to mutations JSON (required for bonus plots).")
    args = parser.parse_args(argv)

    logger.info("Running visualisation demo (source=%s)...", args.source)

    if args.source == "dummy":
        df = get_variants(source="dummy")
        muts_df = None
    else:
        df = get_variants(source="db_export", variants_json_path=args.variants_json)
        muts_df = get_mutations(source="db_export", mutations_json_path=args.mutations_json)

    score_col = "activity_score_log2"

    fig = plot_activity_violin(df, score_col=score_col)
    html_path, png_path = save_plotly_figure(fig, out_prefix="activity_violin")

    trend_fig = plot_activity_median_trend(df, score_col=score_col, show_iqr=True)
    trend_html, trend_png = save_plotly_figure(trend_fig, out_prefix="activity_median_trend")

    top10 = compute_top10(df)
    csv_path = save_table_csv(top10, out_name="top10_variants")
    png_table_path = save_top10_table_png(top10, out_name="top10_variants_table")

    logger.info("Outputs saved:")
    logger.info("- %s", html_path)
    logger.info("- %s", png_path)
    logger.info("- %s", trend_html)
    logger.info("- %s", trend_png)
    logger.info("- %s", csv_path)
    logger.info("- %s", png_table_path)

    # Bonus visuals
    if muts_df is not None and not muts_df.empty:
        best_variant_id = top10.loc[0, "variant_id"]

        fp_fig = plot_mutation_fingerprint(
            muts_df,
            variant_id=best_variant_id,
            title=f"Mutation fingerprint (variant {best_variant_id})",
        )
        fp_html, fp_png = save_plotly_figure(fp_fig, out_prefix="mutation_fingerprint")
        logger.info("- %s", fp_html)
        logger.info("- %s", fp_png)

        land_fig = plot_activity_landscape_3d(
            df,
            muts_df,
            score_col=score_col,
            title="3D Activity Landscape (PCA on mutation positions)",
        )
        land_html, land_png = save_plotly_figure(land_fig, out_prefix="activity_landscape_3d")
        logger.info("- %s", land_html)
        logger.info("- %s", land_png)


if __name__ == "__main__":
    main()