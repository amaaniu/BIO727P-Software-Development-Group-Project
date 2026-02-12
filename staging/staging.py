from __future__ import annotations

from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests

# Flask setup- for testing purposes only, will be removed when integrated with final_page/app.py
# =========================
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB upload limit

def fetch_uniprot(accession):
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    uniprot_res = requests.get(url, timeout=15)

    if uniprot_res.status_code == 404:
        raise ValueError("UniProt accession not found")

    elif uniprot_res.status_code == 400:
        raise ValueError("Invalid UniProt accession format")

    elif uniprot_res.status_code >= 500:
        raise ValueError("UniProt server error, try again later")

    elif uniprot_res.status_code != 200:
        raise ValueError(f"UniProt request failed ({uniprot_res.status_code})")

    data = uniprot_res.json()

    protein_name = (
        data.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", accession)
    )

    sequence = data.get("sequence", {}).get("value")
    if not sequence:
        raise ValueError("Sequence not found in UniProt response")

    return {
        "accession": accession,
        "protein_name": protein_name,
        "sequence": sequence,
        "sequence_length": len(sequence),
    }