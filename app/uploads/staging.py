import requests

from app.uploads.orf_translation import six_frame_orfs, pick_longest_orf


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

    organism_name = data.get("organism", {}).get("scientificName", "Unknown Organism")

    sequence = data.get("sequence", {}).get("value")
    if not sequence:
        raise ValueError("Sequence not found in UniProt response")

    # -------------------------
    # Features (your existing)
    # -------------------------
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

    # Function text
    function_text = None
    # Catalytic activity text
    catalytic_activity_text = None
    # Similarity / family text
    similarity_texts = []

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
        "catalytic_activity": catalytic_activity_text,
        "similarity_texts": similarity_texts,  # often includes "Belongs to ..."
    }

def alphafold_entry_url(uniprot_id: str) -> str:
    return f"https://alphafold.ebi.ac.uk/entry/{uniprot_id}"


def fetch_alphafold_prediction(uniprot_id: str, timeout: int = 15):
    """Return AlphaFold prediction metadata for an accession, or None."""
    api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
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
    """Backward-compatible thumbnail getter (currently returns PAE image)."""
    prediction = fetch_alphafold_prediction(uniprot_id, timeout=timeout)
    if not prediction:
        return None
    return prediction.get("paeImageUrl")
    
# FASTA parsing + DNA validation
class FastaError(ValueError):
    pass

def parse_fasta(fasta_text):
    """ Parse a FASTA string that must contain exactly ONE record.
    Returns: (header, sequence) with sequence uppercased and whitespace removed."""

    if not fasta_text or not fasta_text.strip():
        raise FastaError("Empty FASTA file.")  

    # DNA letters allowed in plasmid FASTA
    allowed = set("ACGTN")

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

def validate_plasmid_fasta(fasta_text, wt_protein_sequence, min_aa=50):
    header, dna_seq = parse_fasta(fasta_text)
    orfs = six_frame_orfs(dna_seq, circular=True, min_aa=min_aa)
    match = match_wt_exact(orfs, wt_protein_sequence)

    return {
        "header": header,
        "dna_sequence": dna_seq,
        "orfs_found": len(orfs),
        **match
    }
