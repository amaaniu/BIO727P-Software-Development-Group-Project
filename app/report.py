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

# Analysis + visuals (based on your uploaded scripts)
from app.visualisations.top10_table_only import compute_top10

from app.visualisations.activityscore_plot import plot_activity_violin
from app.visualisations.trends import plot_activity_median_trend
from app.visualisations.mutation_fingerprint import plot_mutation_fingerprint
from app.visualisations.activity_landscape import plot_activity_landscape_3d


report_bp = Blueprint("report", __name__)


def _fig_to_embed(fig) -> str:
    """
    Convert a Plotly figure to an embeddable HTML snippet for Jinja.
    """
    if fig is None:
        return ""
    return to_html(fig, full_html=False, include_plotlyjs="cdn")


def _variants_to_df(variants: list[Variant]) -> pd.DataFrame:
    """
    Convert Variant ORM rows into the columns your analysis/plots expect.
    Your plotting code expects: generation + activity_score_log2
    """
    rows = []
    for v in variants:
        rows.append(
            {
                "variant_id": v.variant_id,
                "experiment_id": v.experiment_id,
                "generation": v.generation,
                "plasmid_variant_index": getattr(v, "plasmid_variant_index", None),
                "protein_yield": getattr(v, "protein_yield", None),
                "dna_yield": getattr(v, "dna_yield", None),
                "mutation_count": getattr(v, "mutation_count", None),

                # IMPORTANT:
                # Your plot scripts use "activity_score_log2".
                # If your DB column is called activity_score and already log2, map it here.
                "activity_score_log2": getattr(v, "activity_score", None),
            }
        )
    return pd.DataFrame(rows)


def _mutations_to_df(mutations: list[Mutations]) -> pd.DataFrame:
    """
    Convert Mutations ORM rows into the columns your plots expect.
    """
    rows = []
    for m in mutations:
        rows.append(
            {
                "mutation_id": getattr(m, "mutation_id", None),
                "variant_id": m.variant_id,
                "position": m.position,
                "wt_residue": m.wt_residue,
                "mutant_residue": m.mutant_residue,
                "mutation_type": m.mutation_type,
                "generation": m.generation,
                "codon_change": getattr(m, "codon_change", None),
            }
        )
    return pd.DataFrame(rows)


@report_bp.route("/<int:experiment_id>")
def report(experiment_id: int):
    """
    Synchronous report generation (page loads when done).
    You can keep your fake loading bar for now; later we can make this async.
    """
    exp = Experiment.query.get(experiment_id)
    if not exp:
        abort(404, description="Experiment not found")

    variants = Variant.query.filter_by(experiment_id=experiment_id).all()
    if not variants:
        # Still render the page, but with placeholders.
        summary = {
            "experiment_id": experiment_id,
            "experiment_name": getattr(exp, "experiment_name", None),
            "message": "No variants found for this experiment yet.",
        }
        return render_template("report.html", viz1=None, viz2=None, viz3=None, viz4=None, viz5=None, summary=summary)

    variant_ids = [v.variant_id for v in variants]
    mutations = Mutations.query.filter(Mutations.variant_id.in_(variant_ids)).all()

    variants_df = _variants_to_df(variants)
    mutations_df = _mutations_to_df(mutations)

    # ---- Analysis outputs ----
    # Top 10 variants table
    top10_html = None
    selected_variant_id = None
    try:
        top10_df = compute_top10(variants_df)
        if not top10_df.empty:
            selected_variant_id = top10_df.loc[0, "variant_id"]
        # Render as a Bootstrap-ish table (adjust classes to match your CSS)
        top10_html = top10_df.to_html(
            index=False,
            classes="table table-sm table-striped table-bordered align-middle",
            border=0,
        )
    except Exception as e:
        top10_html = f"<p class='text-danger mb-0'>Top10 generation failed: {e}</p>"

    # ---- Visuals (5 total) ----
    # 1) Violin distribution by generation
    viz1 = None
    try:
        fig1 = plot_activity_violin(variants_df, score_col="activity_score_log2")
        viz1 = _fig_to_embed(fig1)
    except Exception as e:
        viz1 = f"<p class='text-danger mb-0'>Violin plot failed: {e}</p>"

    # 2) Median trend + IQR
    viz2 = None
    try:
        fig2 = plot_activity_median_trend(variants_df, score_col="activity_score_log2")
        viz2 = _fig_to_embed(fig2)
    except Exception as e:
        viz2 = f"<p class='text-danger mb-0'>Trend plot failed: {e}</p>"

    # 3) Mutation fingerprint (for best/top variant)
    viz3 = None
    try:
        if selected_variant_id is not None and not mutations_df.empty:
            fig3 = plot_mutation_fingerprint(mutations_df, variant_id=selected_variant_id)
            viz3 = _fig_to_embed(fig3)
        else:
            viz3 = "<p class='text-muted mb-0'>No mutation fingerprint available yet.</p>"
    except Exception as e:
        viz3 = f"<p class='text-danger mb-0'>Mutation fingerprint failed: {e}</p>"

    # 4) 3D activity landscape
    viz4 = None
    try:
        if not mutations_df.empty:
            fig4 = plot_activity_landscape_3d(variants_df, mutations_df, score_col="activity_score_log2")
            viz4 = _fig_to_embed(fig4)
        else:
            viz4 = "<p class='text-muted mb-0'>No mutation data available for 3D landscape.</p>"
    except Exception as e:
        viz4 = f"<p class='text-danger mb-0'>3D landscape failed: {e}</p>"

    # 5) Top10 table as “visual” (HTML table)
    viz5 = top10_html

    # ---- Summary ----
    summary = {
        "experiment_id": experiment_id,
        "experiment_name": getattr(exp, "experiment_name", None),
        "uniprot_id": getattr(exp, "uniprot_id", None),
        "n_variants": int(len(variants_df)),
        "n_mutations": int(len(mutations_df)),
        "selected_variant_id_for_fingerprint": selected_variant_id,
        "generations_present": sorted(
            [int(x) for x in pd.to_numeric(variants_df["generation"], errors="coerce").dropna().unique().tolist()]
        ),
    }

    return render_template(
        "report.html",
        viz1=viz1,
        viz2=viz2,
        viz3=viz3,
        viz4=viz4,
        viz5=viz5,
        summary=summary,
    )


"""
REGISTERING THE BLUEPRINT:

In app/__init__.py (or wherever you register blueprints):

from app.report import report_bp
app.register_blueprint(report_bp)

Then visit:
  /report/<experiment_id>
"""
