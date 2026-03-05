from __future__ import annotations

import math
from typing import Dict, Optional, Any, List

from app.uploads.orf_translation import identify_recombinant_gene, CODON_TABLE
from app.analysis.mutation_tracker import classify_mutations_cds
from app.analysis.activity_score import compute_activity_score_log2

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
        generation=int(generation)
    )

    # Activity score
    activity_result = compute_activity_score_log2(
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
            "activity_score_log2": (
                activity_result["activity_score_log2"]
                if activity_result else None
            ),
        }

    }