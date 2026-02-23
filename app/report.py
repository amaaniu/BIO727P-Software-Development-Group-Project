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

from flask import Blueprint, jsonify, render_template, abort, request
import pandas as pd

# Plotly HTML conversion
from plotly.io import to_html

# DB models
from app.models import db, Experiment, Variant, Mutations
from app.db_operations import store_analysis_results
from app.analysis.analysis import analyse_variant
from app.visualisations.data_sources import get_variants, get_mutations
# Analysis + visuals (based on your uploaded scripts)
from app.visualisations.top10_table_only import compute_top10

from app.visualisations.activityscore_plot import plot_activity_violin
from app.visualisations.trends import plot_activity_median_trend
from app.visualisations.mutation_fingerprint import plot_mutation_fingerprint
from app.visualisations.activity_landscape import plot_activity_landscape_3d

# IMPORTANT → match your button URLs
report_bp = Blueprint("report", __name__)


@report_bp.route("/<int:experiment_id>", methods=["GET"])
def report_page(experiment_id: int):
    exp = Experiment.query.get(experiment_id)
    if not exp:
        abort(404, description="Experiment not found")
    return render_template("report.html", experiment_id=experiment_id)


@report_bp.route("/api/run-analysis", methods=["POST"])
def api_run_analysis():
    payload = request.get_json(silent=True) or {}
    experiment_id = payload.get("experiment_id")

    if not experiment_id:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.get(int(experiment_id))
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

    if not exp.plasmid_sequence:
        return jsonify({"ok": False, "error": "WT plasmid FASTA not uploaded yet."}), 400

    variants = Variant.query.filter_by(experiment_id=exp.experiment_id).all()
    if not variants:
        return jsonify({"ok": False, "error": "No variants found for this experiment."}), 400

    # Baseline (WT) yields:
    # 1) Prefer experiment-level fields if your schema has them.
    # 2) Fallback to earliest variant with non-null yields (usually generation 0).
    wt_dna = getattr(exp, "wt_dna_yield", None)
    wt_protein = getattr(exp, "wt_protein_yield", None)

    baseline_variant = None
    if wt_dna is None or wt_protein is None:
        yield_candidates = [
            v for v in variants
            if v.dna_yield is not None and v.protein_yield is not None
        ]
        if yield_candidates:
            baseline_variant = min(
                yield_candidates,
                key=lambda v: (int(v.generation), int(v.variant_id)),
            )
            wt_dna = baseline_variant.dna_yield
            wt_protein = baseline_variant.protein_yield

    if wt_dna is None or wt_protein is None:
        return jsonify({"ok": False, "error": "WT baseline missing (no experiment-level WT yields and no baseline variant)."}), 400

    wt_dna_yield = float(wt_dna)
    wt_protein_yield = float(wt_protein)
    if wt_dna_yield == 0.0 or wt_protein_yield == 0.0:
        return jsonify({"ok": False, "error": "WT baseline yields cannot be zero."}), 400

    try:
        analysed = 0
        skipped = 0
        skip_reasons = []
        mutations_inserted = 0

        for v in variants:
            if not v.dna_sequence:
                skipped += 1
                if len(skip_reasons) < 10:
                    skip_reasons.append(f"variant_id={v.variant_id}: missing dna_sequence")
                continue

            if v.dna_yield is None or v.protein_yield is None:
                skipped += 1
                if len(skip_reasons) < 10:
                    skip_reasons.append(f"variant_id={v.variant_id}: missing dna_yield/protein_yield")
                continue

            result = analyse_variant(
                wt_plasmid_sequence=exp.plasmid_sequence,
                variant_plasmid_sequence=v.dna_sequence,
                generation=int(v.generation),
                dna_yield=float(v.dna_yield),
                protein_yield=float(v.protein_yield),
                wt_dna_yield=wt_dna_yield,
                wt_protein_yield=wt_protein_yield,
                circular=True,
                min_aa=200,
            )

            # Store using your db_operations helper (no commit inside it)
            mutations_inserted += store_analysis_results(v, result)
            analysed += 1

        db.session.commit()

        return jsonify({
            "ok": True,
            "experiment_id": exp.experiment_id,
            "variants_analysed": analysed,
            "variants_skipped": skipped,
            "skip_reasons_preview": skip_reasons,  # first 10
            "mutations_inserted": mutations_inserted,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400

@report_bp.route("/api/summary", methods=["GET"])
def api_summary():
    experiment_id = request.args.get("experiment_id", type=int)
    if not experiment_id:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    variants = (Variant.query
                .filter_by(experiment_id=experiment_id)
                .order_by(Variant.generation.asc(), Variant.plasmid_variant_index.asc())
                .all())

    if not variants:
        return jsonify({"ok": False, "error": "No variants found"}), 404

    # Only return fields needed for plotting + table
    rows = []
    for v in variants:
        rows.append({
            "variant_id": v.variant_id,
            "generation": v.generation,
            "plasmid_variant_index": v.plasmid_variant_index,
            "activity_score": v.activity_score,
            "mutation_count": v.mutation_count,
            "protein_yield": v.protein_yield,
            "dna_yield": v.dna_yield,
        })

    return jsonify({"ok": True, "variants": rows})


def _fig_to_embed(fig):
    if fig is None:
        return ""
    return to_html(fig, full_html=False, include_plotlyjs="cdn")

@report_bp.route("/api/render-report", methods=["GET"])
def api_render_report():
    experiment_id = request.args.get("experiment_id", type=int)
    if not experiment_id:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.get(experiment_id)
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

    variants_df = get_variants(experiment_id)
    if variants_df.empty:
        return jsonify({"ok": True, "summary": "No variants available yet.", "viz": {}})

    try:
        mutations_df = get_mutations(experiment_id)
    except Exception:
        mutations_df = pd.DataFrame()

    has_scores = (
        "activity_score_log2" in variants_df.columns
        and variants_df["activity_score_log2"].notna().any()
    )

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

    # ---- 1) Top 10 table ----
    try:
        top10_df = compute_top10(variants_df)
        selected_variant_id = int(top10_df.iloc[0]["variant_id"]) if not top10_df.empty else None
        viz1 = top10_df.to_html(
            index=False,
            classes="table table-sm table-striped table-bordered align-middle",
            border=0,
        )
    except Exception as e:
        viz1 = f"<p class='text-danger'>Top10 failed: {e}</p>"
        selected_variant_id = None

    # ---- 2) Activity score plot ----
    try:
        viz2 = _fig_to_embed(plot_activity_violin(variants_df)) if has_scores else "<p class='text-muted'>No activity scores yet.</p>"
    except Exception as e:
        viz2 = f"<p class='text-danger'>Activity plot failed: {e}</p>"

    # ---- 3) Trends ----
    try:
        viz3 = _fig_to_embed(plot_activity_median_trend(variants_df)) if has_scores else "<p class='text-muted'>No trend data yet.</p>"
    except Exception as e:
        viz3 = f"<p class='text-danger'>Trends failed: {e}</p>"

    # ---- 4) Mutation fingerprint ----
    try:
        if selected_variant_id and not mutations_df.empty:
            viz4 = _fig_to_embed(plot_mutation_fingerprint(mutations_df, selected_variant_id))
        else:
            viz4 = "<p class='text-muted'>No mutation fingerprint available.</p>"
    except Exception as e:
        viz4 = f"<p class='text-danger'>Fingerprint failed: {e}</p>"

    # ---- 5) Activity landscape ----
    try:
        if has_scores and not mutations_df.empty:
            viz5 = _fig_to_embed(plot_activity_landscape_3d(variants_df, mutations_df))
        else:
            viz5 = "<p class='text-muted'>No landscape data available.</p>"
    except Exception as e:
        viz5 = f"<p class='text-danger'>Landscape failed: {e}</p>"

    return jsonify({
        "ok": True,
        "summary": summary,
        "viz": {"viz1": viz1, "viz2": viz2, "viz3": viz3, "viz4": viz4, "viz5": viz5}
    })
