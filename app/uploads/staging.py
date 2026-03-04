"""Prepare uploaded sequence data for analysis.
Includes UniProt/AlphaFold metadata lookup and FASTA validation.
"""

import requests
from app.uploads.orf_translation import six_frame_orfs


def fetch_uniprot(accession):
    """Fetch and normalise UniProt metadata for a protein accession.
    Args:
        accession: UniProt accession supplied by the user.

    Returns:
        dict: Normalised UniProt metadata including sequence, annotations,
        and feature rows used by the upload UI.
    """

    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    # Fail early on HTTP problems so the upload step can show a clear user message.
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

    organism_name = data.get("organism", {}).get("scientificName", "Unknown Organism")

    sequence = data.get("sequence", {}).get("value")
    if not sequence:
        raise ValueError("Sequence not found in UniProt response")

    # Features table with type, description, and location (start/end) for the upload summary panel.
    features = []
    for f in data.get("features", []):
        ftype = f.get("type")
        desc = f.get("description")

        start = f.get("location", {}).get("start", {}).get("value")
        end = f.get("location", {}).get("end", {}).get("value")

        if ftype and start and end:
            features.append({
                "feature_type": ftype,
                "description": desc or "",
                "start_pos": start,
                "end_pos": end
            })

    # Gene name + synonyms
    gene_name = None
    gene_synonyms = []

    genes = data.get("genes", []) or []
    if genes:
        gene_name = genes[0].get("geneName", {}).get("value")

        for g in genes:
            for syn in (g.get("synonyms", []) or []):
                v = syn.get("value")
                if v:
                    gene_synonyms.append(v)

    function_text = None
    catalytic_activity_text = None
    similarity_texts = []

    # Extract only the curated comment types used in the upload summary panel.
    for c in data.get("comments", []) or []:
        ctype = c.get("commentType")

        if ctype == "FUNCTION" and function_text is None:
            texts = c.get("texts", []) or []
            if texts:
                function_text = texts[0].get("value")

        elif ctype == "CATALYTIC ACTIVITY" and catalytic_activity_text is None:
            # UniProt can store catalytic activity as reaction + sometimes texts
            reaction = c.get("reaction") or {}
            rname = reaction.get("name")
            if rname:
                catalytic_activity_text = rname
            else:
                texts = c.get("texts", []) or []
                if texts:
                    catalytic_activity_text = texts[0].get("value")

        elif ctype == "SIMILARITY":
            texts = c.get("texts", []) or []
            for t in texts:
                v = t.get("value")
                if v:
                    similarity_texts.append(v)

    return {
        "uniprot_id": accession,
        "protein_name": protein_name,
        "organism_name": organism_name,
        "protein_sequence": sequence,
        "protein_length": len(sequence),
        "features": features,
        "gene_name": gene_name,
        "gene_synonyms": sorted(set(gene_synonyms)),
        "function_text": function_text,
        "catalytic_activity": catalytic_activity_text, #
        "similarity_texts": similarity_texts,  # often includes "Belongs to ..."
    }

def alphafold_entry_url(uniprot_id: str) -> str:
    """Build the public AlphaFold entry URL for a UniProt accession.
    Args:
        uniprot_id: UniProt accession used by AlphaFold as the entry key.

    Returns:
        str: Browser URL for the AlphaFold entry page.
    """
    return f"https://alphafold.ebi.ac.uk/entry/{uniprot_id}"


def fetch_alphafold_prediction(uniprot_id: str, timeout: int = 15):
    """Fetch AlphaFold prediction metadata for a UniProt accession.
    Args:
        uniprot_id: UniProt accession to look up in the AlphaFold API.
        timeout: Request timeout in seconds.

    Returns:
        dict | None: The first AlphaFold prediction payload when available,
        otherwise ``None``.
    """
    api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
    # AlphaFold returns a list payload, even when there is only one prediction entry.
    response = requests.get(api_url, timeout=timeout)
    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, list) or not payload:
        return None

    return payload[0]


def fetch_alphafold_thumbnail_url(uniprot_id: str, timeout: int = 15):
    """Return a thumbnail-like image URL from AlphaFold metadata.
    Args:
        uniprot_id: UniProt accession to look up.
        timeout: Request timeout in seconds.

    Returns:
        str | None: The PAE image URL used as a fallback preview, or ``None``
        when AlphaFold metadata is unavailable.
    """
    prediction = fetch_alphafold_prediction(uniprot_id, timeout=timeout)
    if not prediction:
        return None
    return prediction.get("paeImageUrl")
    
#
class FastaError(ValueError):
    """Raised when an uploaded FASTA file fails structural or character validation."""
    pass

def parse_fasta(fasta_text):
    """Parse a single-record plasmid FASTA payload.
    Args:
        fasta_text: Raw FASTA file contents as text.

    Returns:
        tuple[str, str]: The FASTA header and cleaned uppercase DNA sequence.
    """

    if not fasta_text or not fasta_text.strip():
        raise FastaError("Empty FASTA file.")  

    # DNA letters allowed in plasmid FASTA
    allowed = set("ACGTN")

    header = None
    header_count = 0
    seq_parts = []

    line_number = 0

    # Split line-by-line so validation errors can be tied to FASTA structure.
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

def match_wt_exact(orfs, wt_protein):
    """Check translated ORFs for an exact wild-type protein match.
    Args:
        orfs: ORF dictionaries produced by ``six_frame_orfs``.
        wt_protein: Expected wild-type protein sequence from UniProt.

    Returns:
        dict: Match metadata describing either the successful ORF hit or the
        mismatch summary used by the upload validator.
    """

    wt = wt_protein.strip().upper()
    # Exact matching is intentional here because upload validation is a strict gate.
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

def validate_plasmid_fasta(fasta_text, wt_protein_sequence, min_aa=50):
    """Validate a plasmid FASTA by translating ORFs and comparing to the WT protein.
    Args:
        fasta_text: Raw plasmid FASTA content uploaded by the user.
        wt_protein_sequence: Wild-type protein sequence fetched from UniProt.
        min_aa: Minimum amino-acid length for ORFs considered during translation.

    Returns:
        dict: FASTA header, cleaned DNA sequence, ORF count, and exact-match
        validation details for the uploaded plasmid.
    """
    header, dna_seq = parse_fasta(fasta_text)
    # Translate all six frames on a circular plasmid so inserts spanning the origin are still detected.
    orfs = six_frame_orfs(dna_seq, circular=True, min_aa=min_aa)
    match = match_wt_exact(orfs, wt_protein_sequence)

    return {
        "header": header,
        "dna_sequence": dna_seq,
        "orfs_found": len(orfs),
        **match
    }
