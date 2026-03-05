from __future__ import annotations

import json
from flask import Blueprint, jsonify, render_template, abort, request
from flask_login import current_user, login_required
import pandas as pd

# DB models
from app.models import db, Experiment, Variant, Mutations, UniProtData
from app.db_operations import store_analysis_results
from app.analysis.analysis import analyse_variant
from app.visualisations.data_sources import get_variants, get_mutations
from app.uploads.staging import alphafold_entry_url, fetch_alphafold_prediction
# Analysis + visuals (based on your uploaded scripts)
from app.visualisations.top10_table_only import compute_top10

from app.visualisations.activityscore_plot import plot_activity_violin
from app.visualisations.trends import plot_activity_median_trend
from app.visualisations.mutation_fingerprint import plot_mutation_fingerprint
from app.visualisations.activity_landscape import plot_activity_landscape_3d

# IMPORTANT → match your button URLs
run_analysis_bp = Blueprint("run_analysis", __name__)

@run_analysis_bp.route("/<int:experiment_id>", methods=["GET"])
@login_required
def analysis_page(experiment_id: int):
    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        abort(404, description="Experiment not found")
    return render_template("run_analysis.html", experiment_id=experiment_id)


@run_analysis_bp.route("/api/run-analysis", methods=["POST"])
@login_required
def api_run_analysis():
    payload = request.get_json(silent=True) or {}
    experiment_id = payload.get("experiment_id")

    if not experiment_id:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.filter_by(
        experiment_id=int(experiment_id),
        user_id=current_user.user_id
    ).first()
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

        if analysed == 0:
            if (exp.status or "").strip().lower() not in {"completed", "complete", "done"}:
                exp.status = "in_progress"
            db.session.commit()
            return jsonify({
                "ok": False,
                "error": "Analysis did not process any variants; experiment remains in progress.",
                "experiment_id": exp.experiment_id,
                "variants_analysed": analysed,
                "variants_skipped": skipped,
                "skip_reasons_preview": skip_reasons,
                "mutations_inserted": mutations_inserted,
            }), 400

        exp.status = "completed"
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
