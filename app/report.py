"""
Build and serve analysis reports.
Includes report page endpoints, summary/visualization payload helpers, and PDF export.
"""

from __future__ import annotations

# Standard library
from urllib.parse import urlparse
import json

#Third-party libraries
import pandas as pd
from flask import Blueprint, jsonify, render_template, Response, abort, request, url_for
from flask_login import current_user, login_required
from playwright.sync_api import sync_playwright
from sqlalchemy import func

# DB models
from app.models import db, Experiment, Variant, Mutations, UniProtData, UniProtFeature

#App services and operations
from app.db_operations import store_analysis_results
from app.analysis.analysis import analyse_variant
from app.uploads.staging import alphafold_entry_url, fetch_alphafold_prediction

#Visualisation builders and data sources
from app.visualisations.data_sources import get_variants, get_mutations
from app.visualisations.top10_table_only import compute_top10
from app.visualisations.activityscore_plot import plot_activity_violin
from app.visualisations.trends import plot_activity_median_trend
from app.visualisations.mutation_fingerprint import plot_mutation_fingerprint
from app.visualisations.activity_landscape import plot_activity_landscape_3d


report_bp = Blueprint("report", __name__)

@report_bp.get("/<int:experiment_id>")
@login_required
def view_report(experiment_id: int):
    """Render the report page shell for a user's experiment.
    Args:
        experiment_id: Database identifier for the experiment to display.

    Returns:
        Response: Rendered HTML template for the report page.
    """
    exp = Experiment.query.filter_by(experiment_id=experiment_id,user_id=current_user.user_id).first()
    if not exp:
        abort(404, description="Experiment not found")

    return render_template("report.html", experiment_id=experiment_id)

@report_bp.route("/api/summary", methods=["GET"])
@login_required
def api_summary():
    """Provide a summary of variants for a given experiment, suitable for report tables
    Args:
        None: Reads ``experiment_id`` from the request query string.

    Returns:
        Response: JSON response containing variant summary rows or an error.
    """
    experiment_id = request.args.get("experiment_id", type=int)
    if experiment_id is None:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400
    
    exp = Experiment.query.filter_by(experiment_id=experiment_id, user_id=current_user.user_id).first()
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

    variants = (Variant.query.filter_by(experiment_id=experiment_id)
                .order_by(Variant.generation.asc(), Variant.plasmid_variant_index.asc()).all())

    if not variants:
        return jsonify({"ok": False, "error": "No variants found"}), 404

    # Only return the fields the frontend summary and tables actually consume.
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
    """Convert a Plotly figure into a JSON-safe response payload.
    Args:
        fig: Plotly figure object or ``None``.

    Returns:
        dict | None: Payload wrapper for Plotly figures, or ``None`` when no
        figure was supplied.
    """
    if fig is None:
        return None
    # fig.to_plotly_json() can include numpy arrays; round-trip via JSON to make it Flask-jsonify safe.
    return {"type": "plotly", "figure": json.loads(fig.to_json())}

def get_lineage_chain(leaf_variant):
    """Follow parent links to build a lineage chain from root to leaf.
    Args:
        leaf_variant: Final ``Variant`` object whose ancestry should be traced.

    Returns:
        list: Ordered lineage of ``Variant`` objects from root to leaf.
    """
    chain = []
    seen = set()
    v = leaf_variant

    while v is not None:
        if v.variant_id in seen:
            raise ValueError("Cycle detected in lineage.")
        seen.add(v.variant_id)
        chain.append(v)
        v = v.parent

    chain.reverse()
    return chain


def build_introduced_mutations_df(lineage_chain):
    """Build a dataframe of mutations newly introduced at each lineage generation.

    Args:
        lineage_chain (Iterable[Variant]): Ordered lineage of Variant objects.

    Returns:
        pandas.DataFrame: Mutation rows with columns:
            generation, variant_id, position, wt_residue, mutant_residue.
    """
    import pandas as pd

    chain = list(lineage_chain)
    if not chain:
        return pd.DataFrame(
            columns=["generation", "variant_id", "position", "wt_residue", "mutant_residue"]
        )

    def _keys(v):
        q = v.mutations
        # v.mutations is lazy='dynamic' → query; ensure list of objects
        muts = q.all() if hasattr(q, "all") else list(q)

        # Optional filter: keep only substitutions if mutation_type exists
        if muts and hasattr(muts[0], "mutation_type"):
            muts = [m for m in muts if (m.mutation_type or "").lower() in ("substitution", "missense", "nonsynonymous")]

        return {(int(m.position), str(m.wt_residue), str(m.mutant_residue)) for m in muts}

    # Compare each variant to its actual parent so branching lineages remain correct.
    rows = []
    for v in chain:
        cur = _keys(v)
        parent = v.parent  # use the real parent relationship
        par = _keys(parent) if parent is not None else set()

        introduced = cur - par

        for pos, wt, mut in introduced:
            rows.append(
                dict(
                    generation=int(v.generation),
                    variant_id=int(v.variant_id),
                    position=int(pos),
                    wt_residue=wt,
                    mutant_residue=mut,
                )
            )

    return pd.DataFrame(rows)

@report_bp.route("/api/render-report", methods=["GET"])
@login_required
def api_render_report():
    """Assemble the full report payload for the frontend report template.
    Args:
        None: Reads ``experiment_id`` from the request query string.

    Returns:
        Response: JSON response containing summary metadata and rendered
        visualisation payloads or error information.
    """
    experiment_id = request.args.get("experiment_id", type=int)
    if experiment_id is None:
        return jsonify({"ok": False, "error": "Missing experiment_id"}), 400

    exp = Experiment.query.filter_by(
        experiment_id=experiment_id,
        user_id=current_user.user_id
    ).first()
    if not exp:
        return jsonify({"ok": False, "error": "Experiment not found"}), 404

    # Pull data via datasources.py (DB -> list[dict] -> DataFrame) ---
    variants_df = get_variants(experiment_id)
    if variants_df is None or variants_df.empty:
        return jsonify({"ok": True, "summary": "No variants available yet.", "viz": {}})

    # Coerce numeric columns exactly like your pipeline does
    for col in ("generation", "activity_score_log2", "mutation_count", "dna_yield", "protein_yield"):
        if col in variants_df.columns:
            variants_df[col] = pd.to_numeric(variants_df[col], errors="coerce")

    # some pipelines store activity on Variant.activity_score only.
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

    # Normalise the accession before querying cached UniProt metadata tables.
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
    # Summary is shaped to match the report.html renderer directly.
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

    # Each visual block is isolated so one failed chart does not block the whole report.
    # ---- 1) Top 10 table ----
    try:
        top10_df = compute_top10(variants_df)
        
        # Collect Top10 IDs for UI selection (prefer experiment_variant_id for consistency)
        top10_experiment_variant_ids: list[int] = []
        if not top10_df.empty:
            if "experiment_variant_id" in top10_df.columns:
                top10_experiment_variant_ids = [
                    int(x) for x in top10_df["experiment_variant_id"].dropna().tolist()
                ]
            elif "variant_id" in top10_df.columns and "experiment_variant_id" in variants_df.columns:
                # Map top10 variant_id -> experiment_variant_id for UI display/selection
                idmap = (
                    variants_df.loc[:, ["variant_id", "experiment_variant_id"]]
                    .dropna(subset=["variant_id", "experiment_variant_id"])
                    .drop_duplicates(subset=["variant_id"])
                    .set_index("variant_id")["experiment_variant_id"]
                    .to_dict()
                )
                top10_experiment_variant_ids = [
                    int(idmap[v]) for v in top10_df["variant_id"].dropna().tolist() if v in idmap
                ]

        # Default selection = first top performer (experiment_variant_id)
        selected_fp_experiment_variant_id = (
            top10_experiment_variant_ids[0] if top10_experiment_variant_ids else None
        )

        # Optional override from UI, but only if it's in the Top10 list
        requested_fp_experiment_variant_id = request.args.get(
            "fingerprint_experiment_variant_id",
            type=int
        )
        if (
            requested_fp_experiment_variant_id is not None
            and requested_fp_experiment_variant_id in top10_experiment_variant_ids
        ):
            selected_fp_experiment_variant_id = requested_fp_experiment_variant_id

        # Map experiment_variant_id -> true Variant.variant_id for lineage traversal
        selected_variant_id = None
        if selected_fp_experiment_variant_id is not None:
            if "experiment_variant_id" in variants_df.columns and "variant_id" in variants_df.columns:
                match = variants_df.loc[
                    variants_df["experiment_variant_id"] == selected_fp_experiment_variant_id,
                    "variant_id",
                ]
                if not match.empty:
                    selected_variant_id = int(match.iloc[0])

        viz1 = top10_df.to_html(
            index=False,
            classes="table table-sm align-middle mb-0 feature-meta-table",
            border=0,
        )
    except Exception as e:
        viz1 = f"<p class='text-danger'>Top10 failed: {e}</p>"
        selected_variant_id = None
        top10_experiment_variant_ids = []
        selected_fp_experiment_variant_id = None

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
            selected_variant = Variant.query.get(selected_variant_id)
            chain = get_lineage_chain(selected_variant)
            introduced_df = build_introduced_mutations_df(chain)

            protein_length = len(selected_variant.protein_sequence)

            fig4 = plot_mutation_fingerprint(introduced_df,
                                             protein_length=protein_length,
                                             title=f"Mutation fingerprint (introduced per generation) - variant {selected_fp_experiment_variant_id}",)
            
            viz4 = _fig_to_payload(fig4)
        
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
        "viz": {"viz1": viz1, "viz2": viz2, "viz3": viz3, "viz4": viz4, "viz5": viz5},
        "top10_experiment_variant_ids": top10_experiment_variant_ids,
        "selected_fingerprint_experiment_variant_id": selected_fp_experiment_variant_id,
    })



@report_bp.get("/<int:experiment_id>/download.pdf")
@login_required
def download_report_pdf(experiment_id: int):
    """Render a user's report page to PDF using Playwright.
    Args:
        experiment_id: Database identifier for the experiment to export.

    Returns:
        Response: PDF download response for the rendered report.
    """
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

        # Render the same authenticated browser view the user sees in HTML.
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

        # Print styling
        page.emulate_media(media="print")

        # Wait for standard image assets to load before printing
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

