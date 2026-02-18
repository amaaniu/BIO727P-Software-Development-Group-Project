from __future__ import annotations

import math
from typing import Dict, Optional, Any, List

from orf_finder import identify_recombinant_gene, CODON_TABLE


# ============================
# ACTIVITY SCORE FUNCTIONS
# ============================

def compute_activity_score_raw(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:

    if dna_yield is None or protein_yield is None:
        return None

    if wt_dna_yield is None or wt_protein_yield is None:
        return None

    if wt_dna_yield == 0 or wt_protein_yield == 0:
        return None

    dna_norm = dna_yield / wt_dna_yield
    protein_norm = protein_yield / wt_protein_yield

    if protein_norm == 0:
        return None

    activity_score_raw = dna_norm / protein_norm

    return {
        "dna_norm": dna_norm,
        "protein_norm": protein_norm,
        "activity_score_raw": activity_score_raw,
    }


def compute_activity_score_log2(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:

    result = compute_activity_score_raw(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )

    if result is None:
        return None

    raw = result["activity_score_raw"]

    result["activity_score_log2"] = (
        math.log2(raw) if raw > 0 else None
    )

    return result


def compute_activity_scores(
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float
) -> Optional[Dict[str, Any]]:

    return compute_activity_score_log2(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )


# ============================
# MUTATION TRACKER
# ============================

def _translate_codon(codon: str) -> str:
    codon = codon.upper().replace("U", "T")
    return CODON_TABLE.get(codon, "X")


def classify_mutations_cds(
    wt_cds: str,
    var_cds: str,
    generation: int
) -> Dict[str, Any]:

    wt = wt_cds.strip().upper()
    var = var_cds.strip().upper()

    if not wt:
        raise ValueError("WT CDS empty")

    if not var:
        raise ValueError("Variant CDS empty")

    n_codons = min(len(wt), len(var)) // 3

    mutation_records: List[Dict[str, Any]] = []

    syn_count = 0
    nonsyn_count = 0

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


# ============================
# MAIN BACKEND PIPELINE
# ============================

def analyse_variant(
    wt_plasmid_sequence: str,
    variant_plasmid_sequence: str,
    generation: int,
    dna_yield: float,
    protein_yield: float,
    wt_dna_yield: float,
    wt_protein_yield: float,
    circular: bool = True,
    min_aa: int = 200
) -> Dict[str, Any]:

    # Identify WT gene
    wt_gene = identify_recombinant_gene(
        wt_plasmid_sequence,
        circular=circular,
        min_aa=min_aa
    )

    # Identify Variant gene
    var_gene = identify_recombinant_gene(
        variant_plasmid_sequence,
        circular=circular,
        min_aa=min_aa
    )

    wt_cds = wt_gene["cds_dna"]
    var_cds = var_gene["cds_dna"]

    # Mutation analysis
    mutation_result = classify_mutations_cds(
        wt_cds,
        var_cds,
        generation
    )

    # Activity score
    activity_result = compute_activity_scores(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )

    return {

        "wt": {
            "protein": wt_gene["protein"],
            "cds_length_bp": wt_gene["cds_length_bp"],
            "protein_length_aa": wt_gene["protein_length_aa"],
        },

        "variant": {
            "protein": var_gene["protein"],
            "cds_length_bp": var_gene["cds_length_bp"],
            "protein_length_aa": var_gene["protein_length_aa"],
        },

        "mutations": mutation_result,

        "activity": activity_result,

        "variant_summary": {
            "protein_sequence": var_gene["protein"],
            "mutation_count": mutation_result["mutation_count"],
            "activity_score_raw": (
                activity_result["activity_score_raw"]
                if activity_result else None
            ),
            "activity_score_log2": (
                activity_result["activity_score_log2"]
                if activity_result else None
            ),
        }

    }