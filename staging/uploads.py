from flask import Blueprint, render_template, request, jsonify, session
from staging import fetch_uniprot, parse_fasta, match_wt_exact
from orf_translation import six_frame_orfs
from file_handling import process_file
from db_operations import ensure_guest_user, process_and_insert, insert_uniprot_records, insert_uniprot_feature_records, update_experiment_plasmid
from datetime import datetime
from models import UniProtFeature, db, Experiment, UniProtData

routes_bp = Blueprint("routes", __name__)

@routes_bp.route("/", methods=["GET"])
def staging_page():
    return render_template("staging.html")

@routes_bp.route("/api/uniprot", methods=["POST"])
def api_uniprot():
    user_id = session.get("user_id", 1)  # guest fallback

    try:
        payload = request.get_json(silent=True) or {}
        accession = (payload.get("accession") or "").strip()

        if not accession:
            return jsonify({"ok": False, "error": "Please enter a UniProt accession."}), 400

        data = fetch_uniprot(accession)

        existing = UniProtData.query.get(data["uniprot_id"])
        if not existing:
            uniprot = UniProtData(
            uniprot_id=data["uniprot_id"],
            protein_name=data.get("protein_name"),
            protein_length=data["protein_length"],
            protein_sequence=data["protein_sequence"],)
        
        db.session.add(uniprot)
        db.session.commit()


        for f in data.get("features", []):
            db.session.add(UniProtFeature(
                uniprot_id=data["uniprot_id"],
                feature_type=f["feature_type"],
                description=f.get("description"),
                start_pos=f.get("start_pos"),
                end_pos=f.get("end_pos"),
            ))

        exp_name = (payload.get("experiment_name") or "Untitled experiment").strip()

        experiment = Experiment(
            user_id=user_id,
            experiment_name=exp_name,
            uniprot_id=data["uniprot_id"],
            wt_protein_sequence=data["protein_sequence"],  # store WT in Experiment for validation step
            status="uniprot_loaded",
            created_at=datetime.utcnow(),
        )

        db.session.add(experiment)
        db.session.commit()

        return jsonify({
            "ok": True,
            "experiment_id": experiment.experiment_id,
            "wt": {
                "accession": data["uniprot_id"],              
                "protein_name": data["protein_name"],
                "sequence": data["protein_sequence"],         
                "sequence_length": data["protein_length"],     
                "features": data.get("features", []),
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@routes_bp.route("/api/validate-fasta", methods=["POST"])
def api_validate_fasta():
    try:
        if "fastaFile" not in request.files:
            return jsonify({"ok": False, "error": "No FASTA file uploaded (expected 'fastaFile')."}), 400

        experiment_id = request.form.get("experiment_id")
        if not experiment_id:
            return jsonify({"ok": False, "error": "Missing experiment_id."}), 400
        experiment_id = int(experiment_id)

        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({"ok": False, "error": "Experiment not found."}), 404
        
        wt_sequence = (experiment.wt_protein_sequence or "").strip()
        if not wt_sequence:
            return jsonify({"ok": False, "error": "Missing WT sequence."}), 400

        file = request.files["fastaFile"]
        fasta_text = file.read().decode("utf-8", errors="replace")

        header, dna_seq = parse_fasta(fasta_text)

        # Translate ORFs and check match
        orfs = six_frame_orfs(dna_seq, circular=True, min_aa=50)
        result = match_wt_exact(orfs, wt_sequence)

        update_experiment_plasmid(
            experiment_id=experiment_id,
            plasmid_sequence=dna_seq,
            status="plasmid_uploaded"
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


@routes_bp.route("/api/upload-data", methods=["POST"])
def api_upload_data():
    user_id = session.get("user_id", 1)  # TEMP: avoid session KeyError

    try:
        if "dataFile" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded (expected 'dataFile')."}), 400

        file = request.files["dataFile"]

        # 1) Parse once to detect type
        parsed = process_file(file)
        file.seek(0)  # IMPORTANT: reset stream

        data_type = parsed["data_type"]

        # 2) Get experiment_id if provided
        experiment_id = request.form.get("experiment_id")
        if experiment_id:
            experiment_id = int(experiment_id)

        # 3) If uploading non-experiment data without an experiment_id, create a placeholder Experiment
        if data_type != "experiment" and not experiment_id:
            return jsonify({"ok": False, "error": "experiment_id is required for this upload."}), 400
        

        # 4) Now do the real insert
        result = process_and_insert(
            file,
            experiment_id=experiment_id,
            user_id=user_id
        )

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