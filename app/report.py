# app/report.py
"""
Report blueprint:
- Pulls experiment/variant/mutation data from the DB
- Runs analysis + visualisation functions
- Renders report.html (you can keep the fake loading bar for now)

Expected files (based on what you uploaded):
- app/visualisation/activityscore_plot.py        -> plot_activity_violin
- app/visualisation/trends.py                    -> plot_activity_median_trend
- app/visualisation/mutation_fingerprint.py      -> plot_mutation_fingerprint
- app/visualisation/activity_landscape.py        -> plot_activity_landscape_3d
- app/analysis/top10_table_only.py               -> compute_top10

Make sure these folders are packages:
- app/analysis/__init__.py
- app/visualisation/__init__.py
"""

from __future__ import annotations

from flask import Blueprint, render_template, abort
import pandas as pd

# Plotly HTML conversion
from plotly.io import to_html

# DB models
from app.models import db, Experiment, Variant, Mutations  # add Activity/ControlData if you need them
from app.visualisations.data_sources import get_variants, get_mutations
# Analysis + visuals (based on your uploaded scripts)
from app.visualisations.top10_table_only import compute_top10

from app.visualisations.activityscore_plot import plot_activity_violin
from app.visualisations.trends import plot_activity_median_trend
from app.visualisations.mutation_fingerprint import plot_mutation_fingerprint
from app.visualisations.activity_landscape import plot_activity_landscape_3d

# IMPORTANT → match your button URLs
report_bp = Blueprint("report", __name__)


def _fig_to_embed(fig):
    if fig is None:
        return ""
    return to_html(fig, full_html=False, include_plotlyjs="cdn")


@report_bp.route("/<int:experiment_id>")
def report(experiment_id: int):

    exp = Experiment.query.get(experiment_id)
    if not exp:
        abort(404, description="Experiment not found")

    # ✅ Single source of truth for variants
    variants_df = get_variants(experiment_id, source="dummy")

    if variants_df.empty:
        summary = "No variants available for this experiment yet."
        return render_template(
            "report.html",
            viz1=None, viz2=None, viz3=None, viz4=None, viz5=None,
            summary=summary
        )

    # ✅ Mutations optional depending on visual
    try:
        mutations_df = get_mutations(experiment_id, source="dummy")
    except Exception:
        mutations_df = pd.DataFrame()

    # ---- Top 10 table ----
    try:
        top10_df = compute_top10(variants_df)
        selected_variant_id = (
            top10_df.iloc[0]["variant_id"] if not top10_df.empty else None
        )

        viz5 = top10_df.to_html(
            index=False,
            classes="table table-sm table-striped table-bordered align-middle",
            border=0,
        )

    except Exception as e:
        viz5 = f"<p class='text-danger'>Top10 failed: {e}</p>"
        selected_variant_id = None

    # ---- Visualisations ----

    try:
        viz1 = _fig_to_embed(
            plot_activity_violin(variants_df, score_col="activity_score_log2")
        )
    except Exception as e:
        viz1 = f"<p class='text-danger'>Violin failed: {e}</p>"

    try:
        viz2 = _fig_to_embed(
            plot_activity_median_trend(variants_df, score_col="activity_score_log2")
        )
    except Exception as e:
        viz2 = f"<p class='text-danger'>Trend failed: {e}</p>"

    try:
        if selected_variant_id and not mutations_df.empty:
            viz3 = _fig_to_embed(
                plot_mutation_fingerprint(mutations_df, variant_id=selected_variant_id)
            )
        else:
            viz3 = "<p class='text-muted'>No mutation fingerprint available.</p>"
    except Exception as e:
        viz3 = f"<p class='text-danger'>Fingerprint failed: {e}</p>"

    try:
        if not mutations_df.empty:
            viz4 = _fig_to_embed(
                plot_activity_landscape_3d(
                    variants_df, mutations_df, score_col="activity_score_log2"
                )
            )
        else:
            viz4 = "<p class='text-muted'>No mutation data for landscape.</p>"
    except Exception as e:
        viz4 = f"<p class='text-danger'>Landscape failed: {e}</p>"

    # ---- Summary ----
    generations = sorted(
        pd.to_numeric(variants_df["generation"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    summary = (
        f"Experiment: {getattr(exp, 'experiment_name', None)}\n"
        f"Variants: {len(variants_df)}\n"
        f"Mutations: {len(mutations_df)}\n"
        f"Generations: {generations}"
    )

    return render_template(
        "report.html",
        viz1=viz1,
        viz2=viz2,
        viz3=viz3,
        viz4=viz4,
        viz5=viz5,
        summary=summary,
    )
