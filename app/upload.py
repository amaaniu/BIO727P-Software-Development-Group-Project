"""Endpoints for the staged upload workflow used before running analysis.

This module validates UniProt accessions, stores wild-type metadata, checks
uploaded plasmid FASTA content against the expected protein, and ingests the
experiment data files needed for downstream analysis.
"""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.models import Experiment, UniProtData, UniProtFeature, Variant, db
from app.db_operations import process_and_insert, update_experiment_plasmid
from app.uploads.file_handling import process_file
from app.uploads.orf_translation import six_frame_orfs
from app.uploads.staging import (
    alphafold_entry_url,
    fetch_alphafold_prediction,
    fetch_uniprot,
    match_wt_exact,
    parse_fasta,
)

upload_bp = Blueprint("upload", __name__)

@upload_bp.route("/", methods=["GET"])
@login_required
def upload_page():
    """Render the upload workflow page.

    Args:
        None.

    Returns:
        Response: Rendered HTML template for the upload page.
    """
    return render_template("upload.html")

@upload_bp.route("/api/uniprot", methods=["POST"])
@login_required
def api_uniprot():
    """Validate a UniProt accession and initialise upload state for an experiment.

    Args:
        None: Reads JSON payload data from the request body.

    Returns:
        Response: JSON response containing WT metadata, AlphaFold links, and
        the experiment identifier used by later upload steps.
    """
    user_id = current_user.user_id

    try:
        payload = request.get_json(silent=True) or {}
        accession = (payload.get("accession") or "").strip()

        if not accession:
            return jsonify({"ok": False, "error": "Please enter a UniProt accession."}), 400

        # 1) Fetch the canonical WT metadata that anchors the rest of the upload workflow.
        data = fetch_uniprot(accession)
        alphafold_link = alphafold_entry_url(data["uniprot_id"])
        alphafold_prediction = fetch_alphafold_prediction(data["uniprot_id"])
        alphafold_img = (
            alphafold_prediction.get("paeImageUrl") if alphafold_prediction else None
        )
        alphafold_pdb_url = (
            alphafold_prediction.get("pdbUrl") if alphafold_prediction else None
        )

        # 2) Upsert cached UniProt metadata so repeated searches reuse a local copy.
        existing = UniProtData.query.get(data["uniprot_id"])
        if not existing:
            existing = UniProtData(
                uniprot_id=data["uniprot_id"],
                protein_name=data.get("protein_name"),
                organism_name=data.get("organism_name"),
                protein_length=data["protein_length"],
                protein_sequence=data["protein_sequence"],
            )
            db.session.add(existing)
        else:
            # Backfill/refresh values so old partial rows don't keep organism_name as NULL.
            existing.protein_name = data.get("protein_name") or existing.protein_name
            existing.organism_name = data.get("organism_name") or existing.organism_name
            existing.protein_length = data["protein_length"]
            existing.protein_sequence = data["protein_sequence"]
        db.session.commit()

        # 3) Replace cached feature rows so repeated fetches do not duplicate annotations.
        UniProtFeature.query.filter_by(uniprot_id=data["uniprot_id"]).delete()
        for f in data.get("features", []):
            db.session.add(UniProtFeature(
                uniprot_id=data["uniprot_id"],
                feature_type=f["feature_type"],
                description=f.get("description"),
                start_pos=f.get("start_pos"),
                end_pos=f.get("end_pos"),
            ))
        db.session.commit()

        # 4) Reuse a draft experiment (awaiting_data with no variants) if one exists.
        # This avoids creating extra experiment IDs when users restart upload.
        experiment = (
            db.session.query(Experiment)
            .outerjoin(Variant, Variant.experiment_id == Experiment.experiment_id)
            .filter(
                Experiment.user_id == current_user.user_id,
                func.lower(func.coalesce(Experiment.status, "")) == "awaiting_data",
            )
            .group_by(Experiment.experiment_id)
            .having(func.count(Variant.variant_id) == 0)
            .order_by(Experiment.experiment_id.desc())
            .first()
        )

        if experiment:
            experiment.uniprot_id = data["uniprot_id"]
            experiment.wt_protein_sequence = data["protein_sequence"]
            experiment.plasmid_sequence = None
            experiment.status = "awaiting_data"
            if not (experiment.experiment_name or "").strip():
                experiment.experiment_name = f"Experiment {experiment.experiment_id}"
        else:
            experiment = Experiment(
                user_id=current_user.user_id,
                experiment_name="",
                uniprot_id=data["uniprot_id"],
                wt_protein_sequence=data["protein_sequence"],
                status="awaiting_data",
                created_at=datetime.utcnow(),
            )
            db.session.add(experiment)
            db.session.flush()  # assign autoincrement experiment_id before naming
            experiment.experiment_name = f"Experiment {experiment.experiment_id}"

        db.session.commit()

        return jsonify({
            "ok": True,
            "experiment_id": experiment.experiment_id,
            "wt": {
                "accession": data["uniprot_id"],
                "protein_name": data.get("protein_name"),
                "organism_name": data.get("organism_name"),
                "sequence": data["protein_sequence"],
                "sequence_length": data["protein_length"],
                "features": data.get("features", []),
                "gene_name": data.get("gene_name"),
                "function_text": data.get("function_text"),
                "catalytic_activity": data.get("catalytic_activity"),
                "similarity_texts": data.get("similarity_texts", []),
                "family_text": (data.get("similarity_texts") or [None])[0],
                "alphafold_link": alphafold_link,
                "alphafold_img": alphafold_img,
                "alphafold_pdb_url": alphafold_pdb_url,
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400


@upload_bp.route("/api/validate-fasta", methods=["POST"])
@login_required
def api_validate_fasta():
    """Validate an uploaded plasmid FASTA against the experiment's WT protein.

    Args:
        None: Reads multipart form data and file uploads from the request.

    Returns:
        Response: JSON response containing FASTA metadata and WT match results.
    """
    try:
        if "fastaFile" not in request.files:
            return jsonify({"ok": False, "error": "No FASTA file uploaded (expected 'fastaFile')."}), 400

        experiment_id = request.form.get("experiment_id")
        if not experiment_id:
            return jsonify({"ok": False, "error": "Missing experiment_id."}), 400
        experiment_id = int(experiment_id)

        experiment = Experiment.query.filter_by(
            experiment_id=experiment_id,
            user_id=current_user.user_id
        ).first()
        if not experiment:
            return jsonify({"ok": False, "error": "Experiment not found for current user."}), 404
        
        wt_sequence = (experiment.wt_protein_sequence or "").strip()
        if not wt_sequence:
            return jsonify({"ok": False, "error": "Missing WT sequence."}), 400

        file = request.files["fastaFile"]
        fasta_text = file.read().decode("utf-8", errors="replace")

        header, dna_seq = parse_fasta(fasta_text)

        # Translate ORFs from the circular plasmid and verify that one matches the WT exactly.
        orfs = six_frame_orfs(dna_seq, circular=True, min_aa=50)
        result = match_wt_exact(orfs, wt_sequence)

        update_experiment_plasmid(
            experiment_id=experiment_id,
            user_id=current_user.user_id,
            plasmid_sequence=dna_seq,
            status="awaiting_data",
        )
        
        return jsonify({
            "ok": True,
            "experiment_id": experiment_id,
            "header": header,
            "dna_length_bp": len(dna_seq),
            "wt_check": result
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@upload_bp.route("/api/upload-data", methods=["POST"])
@login_required
def api_upload_data():
    """Ingest an experiment data file into the database for the current user.

    Args:
        None: Reads multipart form data and file uploads from the request.

    Returns:
        Response: JSON response describing the inserted data type, count, and
        experiment identifier.
    """
    user_id = current_user.user_id

    try:
        if "dataFile" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded (expected 'dataFile')."}), 400

        file = request.files["dataFile"]

        # 1) Parse once to detect type before handing off to the main insert pipeline.
        parsed = process_file(file)
        file.seek(0)  # IMPORTANT: reset stream

        data_type = parsed["data_type"]

        # 2) Get experiment_id if provided
        experiment_id = request.form.get("experiment_id")
        if experiment_id:
            experiment_id = int(experiment_id)
            experiment = Experiment.query.get(experiment_id)
            if not experiment or experiment.user_id != current_user.user_id:
                return jsonify({"ok": False, "error": "Experiment not found for current user."}), 404



        # 3) If uploading non-experiment data without an experiment_id, create a placeholder Experiment
        if data_type != "experiment" and not experiment_id:
            return jsonify({"ok": False, "error": "experiment_id is required for this upload."}), 400
        
        
        # 4) Now do the real insert
        result = process_and_insert(
            file,
            experiment_id=experiment_id,
            user_id=current_user.user_id
        )

        # Mark the experiment as active once substantive downstream data has been uploaded.
        if (
            experiment_id
            and result.get("data_type") in {"variant", "mutation", "activity", "control"}
            and int(result.get("count") or 0) > 0
        ):
            experiment = Experiment.query.filter_by(
                experiment_id=experiment_id,
                user_id=current_user.user_id
            ).first()
            if experiment and (experiment.status or "").strip().lower() not in {"completed", "complete", "done"}:
                experiment.status = "in_progress"
                db.session.commit()
 
 
        return jsonify({
            "ok": True,
            "data_type": result["data_type"],
            "count": result["count"],
            "experiment_id": experiment_id
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
