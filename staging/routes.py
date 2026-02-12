from flask import Blueprint, render_template, request, jsonify
from staging import fetch_uniprot, parse_fasta, match_wt_exact
from orf_translation import six_frame_orfs
from file_handling import process_file

routes_bp = Blueprint("routes", __name__)

@routes_bp.route("/", methods=["GET"])
def staging_page():
    return render_template("staging.html")


@routes_bp.route("/api/uniprot", methods=["POST"])
def api_uniprot():
    try:
        payload = request.get_json(silent=True) or {}
        accession = (payload.get("accession") or "").strip()

        if not accession:
            return jsonify({"ok": False, "error": "Please enter a UniProt accession."}), 400

        data = fetch_uniprot(accession)

        # Return lots of detail to display
        return jsonify({
            "ok": True,
            "wt": {
                "accession": data["accession"],
                "protein_name": data["protein_name"],
                "sequence": data["sequence"],
                "sequence_length": data["sequence_length"],
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

        wt_sequence = (request.form.get("wt_sequence") or "").strip()
        if not wt_sequence:
            return jsonify({"ok": False, "error": "Missing WT sequence."}), 400

        file = request.files["fastaFile"]
        fasta_text = file.read().decode("utf-8", errors="replace")

        header, dna_seq = parse_fasta(fasta_text)

        # Translate ORFs and check match
        orfs = six_frame_orfs(dna_seq)
        result = match_wt_exact(orfs, wt_sequence)

        return jsonify({
            "ok": True,
            "header": header,
            "dna_length_bp": len(dna_seq),
            "wt_check": result
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@routes_bp.route("/api/upload-data", methods=["POST"])
def api_upload_data():
    try:
        if "dataFile" not in request.files:
            return jsonify({"ok": False, "error": "No data file uploaded (expected 'dataFile')."}), 400

        file = request.files["dataFile"]

        result = process_file(file)  # returns {"data_type":..., "records":[...]}

        return jsonify({
            "ok": True,
            "data_type": result["data_type"],
            "record_count": len(result["records"])
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
