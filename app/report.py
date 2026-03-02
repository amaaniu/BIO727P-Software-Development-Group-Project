# app/report.py
"""

"""
from __future__ import annotations
from urllib.parse import urlparse

from flask import Response, abort, request, url_for
from app.models import Experiment, UniProtData, UniProtFeature
import json
from flask import Blueprint, jsonify, render_template, abort, request
from flask_login import current_user, login_required
import pandas as pd
from sqlalchemy import func
# DB models
from app.models import db, Experiment, Variant, Mutations, UniProtData, UniProtFeature
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
report_bp = Blueprint("report", __name__)

@report_bp.get("/<int:experiment_id>")
@login_required
def view_report(experiment_id: int):
    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        abort(404, description="Experiment not found")

    return render_template("report.html", experiment_id=experiment_id)

@report_bp.route("/api/summary", methods=["GET"])
@login_required
def api_summary():
    experiment_id = request.args.get("experiment_id", type=int)
    if experiment_id is None:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

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


def _fig_to_payload(fig):
    if fig is None:
        return None
    # fig.to_plotly_json() can include numpy arrays; round-trip via JSON to make it Flask-jsonify safe.
    return {"type": "plotly", "figure": json.loads(fig.to_json())}

@report_bp.route("/api/render-report", methods=["GET"])
@login_required
def api_render_report():
    experiment_id = request.args.get("experiment_id", type=int)
    if experiment_id is None:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

    # --- Pull data via datasources.py (DB -> list[dict] -> DataFrame) ---
    variants_df = get_variants(experiment_id)
    if variants_df is None or variants_df.empty:
        return jsonify({"ok": True, "summary": "No variants available yet.", "viz": {}})

    # Coerce numeric columns exactly like your pipeline does
    for col in ("generation", "activity_score_log2", "mutation_count", "dna_yield", "protein_yield"):
        if col in variants_df.columns:
            variants_df[col] = pd.to_numeric(variants_df[col], errors="coerce")

    # Robust fallback: some pipelines store activity on Variant.activity_score only.
    if "activity_score_log2" not in variants_df.columns and "activity_score" in variants_df.columns:
        variants_df["activity_score_log2"] = pd.to_numeric(variants_df["activity_score"], errors="coerce")
    elif "activity_score_log2" in variants_df.columns and "activity_score" in variants_df.columns:
        variants_df["activity_score_log2"] = variants_df["activity_score_log2"].fillna(
            pd.to_numeric(variants_df["activity_score"], errors="coerce")
        )

    try:
        mutations_df = get_mutations(experiment_id)
        if mutations_df is None:
            mutations_df = pd.DataFrame()
    except Exception:
        mutations_df = pd.DataFrame()

    if not mutations_df.empty:
        for col in ("generation", "position"):
            if col in mutations_df.columns:
                mutations_df[col] = pd.to_numeric(mutations_df[col], errors="coerce")

    score_col = "activity_score_log2"
    has_scores = score_col in variants_df.columns and variants_df[score_col].notna().any()

    # Generations list (safe even if generation has NaNs)
    generations = []
    if "generation" in variants_df.columns:
        generations = sorted(
            variants_df["generation"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

    normalized_uniprot_id = (exp.uniprot_id or "").strip().upper()
    uniprot = (
        UniProtData.query
        .filter(func.upper(func.trim(UniProtData.uniprot_id)) == normalized_uniprot_id)
        .first()
    )
    protein_length = (
        getattr(uniprot, "protein_length", None)
        or len((getattr(exp, "wt_protein_sequence", "") or "").strip())
        or None
    )

    alphafold_link = alphafold_entry_url(exp.uniprot_id)
    alphafold_img = None
    alphafold_pdb_url = None
    try:
        alphafold_prediction = fetch_alphafold_prediction(exp.uniprot_id)
        if alphafold_prediction:
            alphafold_img = alphafold_prediction.get("paeImageUrl")
            alphafold_pdb_url = alphafold_prediction.get("pdbUrl")
    except Exception:
        alphafold_img = None
        alphafold_pdb_url = None

    features = [
        {
            "feature_type": feature.feature_type,
            "start_pos": feature.start_pos,
            "end_pos": feature.end_pos,
            "description": feature.description,
        }
        for feature in (
            UniProtFeature.query
            .filter(func.upper(func.trim(UniProtFeature.uniprot_id)) == normalized_uniprot_id)
            .order_by(UniProtFeature.start_pos.asc(), UniProtFeature.end_pos.asc(), UniProtFeature.feature_id.asc())
            .all()
        )
    ]
    summary = {
        "experiment_name": getattr(exp, "experiment_name", None),
        "accession": exp.uniprot_id,
        "protein_name": getattr(uniprot, "protein_name", None),
        "organism_name": getattr(uniprot, "organism_name", None),
        "sequence_length": protein_length,
        "variants": len(variants_df),
        "mutations": len(mutations_df),
        "generations": generations,
        "alphafold_link": alphafold_link,
        "alphafold_img": alphafold_img,
        "alphafold_pdb_url": alphafold_pdb_url,
        "features": features,
    }

    # ---- 1) Top 10 table ----
    try:
        top10_df = compute_top10(variants_df)
        selected_variant_id = int(top10_df.iloc[0]["variant_id"]) if not top10_df.empty else None

        viz1 = top10_df.to_html(
            index=False,
            classes="table table-sm align-middle mb-0 feature-meta-table",
            border=0,
        )
    except Exception as e:
        viz1 = f"<p class='text-danger'>Top10 failed: {e}</p>"
        selected_variant_id = None

    # ---- 2) Activity score plot ----
    try:
        viz2 = (
            _fig_to_payload(plot_activity_violin(variants_df, score_col=score_col))
            if has_scores
            else "<p class='text-muted'>No activity scores yet.</p>"
        )
    except Exception as e:
        viz2 = f"<p class='text-danger'>Activity plot failed: {e}</p>"

    # ---- 3) Trends ----
    try:
        viz3 = (
            _fig_to_payload(plot_activity_median_trend(variants_df, score_col=score_col, show_iqr=True))
            if has_scores
            else "<p class='text-muted'>No trend data yet.</p>"
        )
    except Exception as e:
        viz3 = f"<p class='text-danger'>Trends failed: {e}</p>"

    # ---- 4) Mutation fingerprint ----
    try:
        if selected_variant_id and not mutations_df.empty:
            viz4 = _fig_to_payload(
                plot_mutation_fingerprint(
                    mutations_df,
                    protein_length=protein_length,
                    title=f"Mutation fingerprint (variant {selected_variant_id})",
                )
            )
        else:
            viz4 = "<p class='text-muted'>No mutation fingerprint available.</p>"
    except Exception as e:
        viz4 = f"<p class='text-danger'>Fingerprint failed: {e}</p>"

    # ---- 5) Activity landscape ----
    try:
        if has_scores and not mutations_df.empty:
            viz5 = _fig_to_payload(
                plot_activity_landscape_3d(
                    variants_df,
                    mutations_df,
                    score_col=score_col,
                    title="3D Activity Landscape (PCA on mutation positions)",
                )
            )
        else:
            viz5 = "<p class='text-muted'>No landscape data available.</p>"
    except Exception as e:
        viz5 = f"<p class='text-danger'>Landscape failed: {e}</p>"

    return jsonify({
        "ok": True,
        "summary": summary,
        "viz": {"viz1": viz1, "viz2": viz2, "viz3": viz3, "viz4": viz4, "viz5": viz5}
    })



@report_bp.get("/<int:experiment_id>/download.pdf")
@login_required
def download_report_pdf(experiment_id: int):
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        abort(
            503,
            description=(
                "PDF export requires Playwright. Install it with "
                "'pip install playwright' and then run "
                "'playwright install chromium'."
            ),
        )

    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        abort(404, description="Experiment not found")

    report_url = url_for("report.view_report", experiment_id=experiment_id, _external=True)
    parsed_report_url = urlparse(report_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 1800})

        # Copy Flask session cookies into Playwright so the PDF request is authenticated
        session_cookies = [
            {
                "name": name,
                "value": value,
                "domain": parsed_report_url.hostname,
                "path": "/",
                "secure": parsed_report_url.scheme == "https",
            }
            for name, value in request.cookies.items()
        ]
        if session_cookies:
            context.add_cookies(session_cookies)

        page = context.new_page()

        # Load the report page and wait for network to settle
        page.goto(report_url, wait_until="networkidle")

        # Wait for your JS to finish rendering (set in report.html)
        page.wait_for_function(
            "() => window.__REPORT_READY__ === true || window.__REPORT_READY__ === 'error'",
            timeout=90_000
        )

        # Optional: fail fast (or still generate an error PDF)
        state = page.evaluate("() => window.__REPORT_READY__")
        if state == "error":
            # You can raise here if you want:
            # context.close(); browser.close()
            # abort(500, description="Report failed to render")
            pass

        # ✅ Convert viz2–viz5 into static images FOR THE PDF ONLY
        for viz_id in ("viz2", "viz3", "viz4", "viz5"):
            locator = page.locator(f"#{viz_id}")
            if locator.count() == 0:
                continue

            # Ensure visible and laid out
            locator.wait_for(state="visible", timeout=15_000)
            locator.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            # Screenshot the current rendered chart area
            screenshot_bytes = locator.screenshot(type="png")

            # Replace the div contents with an <img> so PDF captures a static image
            page.evaluate(
                """
                ({ targetId, pngBytes }) => {
                  const target = document.getElementById(targetId);
                  if (!target) return;

                  const bytes = new Uint8Array(pngBytes);
                  let binary = "";
                  for (let i = 0; i < bytes.length; i++) {
                    binary += String.fromCharCode(bytes[i]);
                  }
                  const dataUrl = "data:image/png;base64," + btoa(binary);

                  target.innerHTML = `
                    <img src="${dataUrl}"
                         style="display:block;width:100%;height:auto;max-width:100%;"
                         alt="Static plot preview" />
                  `;
                }
                """,
                {"targetId": viz_id, "pngBytes": list(screenshot_bytes)},
            )

        # Print styling
        page.emulate_media(media="print")

        # Wait for all images (including our injected ones) to load
        page.wait_for_function(
            "() => Array.from(document.images).every((img) => img.complete)",
            timeout=30_000
        )
        page.wait_for_timeout(600)

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
            margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"},
        )

        context.close()
        browser.close()

    filename = f"experiment_{experiment_id}_report.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
