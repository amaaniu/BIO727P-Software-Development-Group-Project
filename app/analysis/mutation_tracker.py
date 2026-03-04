from __future__ import annotations
from typing import Dict, Any, List

from app.uploads.orf_translation import CODON_TABLE


def _translate_codon(codon: str) -> str:
    # Convert codon to DNA format (U → T) and uppercase
    codon = codon.upper().replace("U", "T")

    # If codon length is not length 3, return unknown
    if len(codon) != 3:
        return "X"
    
    # Convert codon to DNA format (U → T) and uppercase
    return CODON_TABLE.get(codon, "X")


def classify_mutations_cds(
    wt_cds: str,
    var_cds: str,
    generation: int,
) -> Dict[str, Any]:
    """
    Compare WT CDS vs Variant CDS and return mutation records
    formatted for direct insertion into SQLAlchemy Mutations table.
    """

     # Clean and standardise sequences
    wt = (wt_cds or "").strip().upper().replace("U", "T")
    var = (var_cds or "").strip().upper().replace("U", "T")

    # Basic validation
    if not wt:
        raise ValueError("WT CDS empty")
    if not var:
        raise ValueError("Variant CDS empty")
    
    # CDS must be divisible by 3 (valid reading frame)
    if len(wt) % 3 != 0 or len(var) % 3 != 0:
        raise ValueError("CDS length not divisible by 3 (wrong ORF or frameshift).")

    # Compare sequences codon-by-codon
    n_codons = min(len(wt), len(var)) // 3

    mutation_records: List[Dict[str, Any]] = []

    syn_count = 0
    nonsyn_count = 0

    stop_gained = False
    stop_lost = False

    for codon_index in range(n_codons):

        start = codon_index * 3
        wt_codon = wt[start:start+3]
        var_codon = var[start:start+3]

        # Skip codons if they are identical
        if wt_codon == var_codon:
            continue

        # Translate both codons
        wt_aa = _translate_codon(wt_codon)
        var_aa = _translate_codon(var_codon)

        # Determine mutation type
        if wt_aa == var_aa:
            mutation_type = "synonymous"
            syn_count += 1
        else:
            mutation_type = "nonsynonymous"
            nonsyn_count += 1

        # Check stop codon changes
        if wt_aa != "*" and var_aa == "*":
            stop_gained = True

        if wt_aa == "*" and var_aa != "*":
            stop_lost = True

        # Store mutation record
        mutation_records.append({
            "position": codon_index + 1,
            "wt_residue": wt_aa,
            "mutant_residue": var_aa,
            "mutation_type": mutation_type,
            "generation": generation,
            "codon_change": f"{wt_codon}->{var_codon}"
        })
        
    # Return summary of mutations
    return {
        "mutation_records": mutation_records,
        "syn_count": syn_count,
        "nonsyn_count": nonsyn_count,
        "mutation_count": len(mutation_records),
        "stop_gained": stop_gained,
        "stop_lost": stop_lost,

    }