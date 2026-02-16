from __future__ import annotations
from typing import Dict, Any, List

from orf_finder import CODON_TABLE


def _translate_codon(codon: str) -> str:
    codon = codon.upper().replace("U", "T")
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

    wt = (wt_cds or "").strip().upper().replace("U", "T")
    var = (var_cds or "").strip().upper().replace("U", "T")

    if not wt:
        raise ValueError("WT CDS empty")
    if not var:
        raise ValueError("Variant CDS empty")

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

        if wt_codon == var_codon:
            continue

        wt_aa = _translate_codon(wt_codon)
        var_aa = _translate_codon(var_codon)

        if wt_aa == var_aa:
            mutation_type = "synonymous"
            syn_count += 1
        else:
            mutation_type = "nonsynonymous"
            nonsyn_count += 1

        if wt_aa != "*" and var_aa == "*":
            stop_gained = True

        if wt_aa == "*" and var_aa != "*":
            stop_lost = True

        mutation_records.append({

            "position": codon_index + 1,
            "wt_residue": wt_aa,
            "mutant_residue": var_aa,
            "mutation_type": mutation_type,
            "generation": generation,
            "codon_change": f"{wt_codon}->{var_codon}"
        })
        
    return {
        "mutation_records": mutation_records,
        "syn_count": syn_count,
        "nonsyn_count": nonsyn_count,
        "mutation_count": len(mutation_records)
    }