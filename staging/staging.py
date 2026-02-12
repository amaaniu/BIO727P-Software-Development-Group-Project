from __future__ import annotations

from flask import Flask, render_template, request, jsonify, redirect, url_for

import requests

# Flask setup- for testing purposes only, will be removed when integrated with final_page/app.py
# =========================
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB upload limit

def fetch_uniprot(accession):
    """Fetch UniProt data for a given accession number. Returns a dict with keys"""

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

    features = []

    for f in data.get("features", []):
        ftype = f.get("type")
        desc = f.get("description")

        start = f.get("location", {}).get("start", {}).get("value")
        end = f.get("location", {}).get("end", {}).get("value")

        if ftype and start and end:
            features.append({
                "type": ftype,
                "description": desc or "",
                "start": start,
                "end": end
            })

    return {
        "accession": accession,
        "protein_name": protein_name,
        "sequence": sequence,
        "sequence_length": len(sequence),
        "features": features
    }
    
# FASTA parsing + DNA validation
class FastaError(ValueError):
    pass

def parse_fasta(fasta_text):
    """ Parse a FASTA string that must contain exactly ONE record.
    Returns: (header, sequence) with sequence uppercased and whitespace removed."""

    if not fasta_text or not fasta_text.strip():
        raise FastaError("Empty FASTA file.")  

    # DNA letters allowed in plasmid FASTA (includes common ambiguity codes)
    allowed = set("ACGTNRYKMSWBDHV")

    header = None
    header_count = 0
    seq_parts = []

    line_number = 0

    lines = fasta_text.splitlines()

    for raw in lines:
        line_number += 1
        line = raw.strip()

        # ignore empty lines
        if line == "":
            continue

        # ignore old-style FASTA comment lines anywhere
        if line.startswith(";"):
            continue

        # header line
        if line.startswith(">"):
            header_count += 1

            if header_count > 1:
                raise FastaError( "Multiple FASTA records found. Please upload ONE plasmid FASTA.")

            header = line[1:].strip()
            if header == "":
                raise FastaError("FASTA header is missing an identifier.")
            continue

        # sequence line
        if header is None:
            raise FastaError("Sequence appeared before the FASTA header ('>').")

        # remove spaces/tabs inside the sequence line and normalise case
        fasta_cleaned= line.replace(" ", "").replace("\t", "").upper()

        # validate characters
        for char in fasta_cleaned:
            if char not in allowed:
                raise FastaError(f"Invalid character '{char}' in sequence. ")
    
        seq_parts.append(fasta_cleaned)

    if header is None:
        raise FastaError("No FASTA header found (missing '>').")

    sequence = "".join(seq_parts)

    if sequence == "":
        raise FastaError("No sequence found under the FASTA header.")

    return header, sequence

from orf_translation import six_frame_orfs, pick_longest_orf


def match_wt_exact(orfs, wt_protein):

    wt = wt_protein.strip().upper()

    for orf in orfs:
        protein = orf["protein"]

        if protein.upper() == wt:
            return {
                "match": True,
                "reason": "Exact ORF match to WT found.",
                "matching_frame": orf["frame"],
                "matching_length": len(protein)
            }

    return {
        "match": False,
        "reason": "No translated ORF matched WT exactly.",
        "orfs_found": len(orfs),
        "wt_length_aa": len(wt),
        "longest_orf_aa": max((len(o["protein"]) for o in orfs), default=0),
    }

