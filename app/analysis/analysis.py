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

    """
    Runs the full analysis pipeline for a directed evolution variant.

    The pipeline performs:
    1. ORF detection within WT and variant plasmids
    2. Extraction and translation of the coding DNA sequence (CDS)
    3. Codon-level mutation comparison between WT and variant
    4. Activity score calculation normalised to WT control yields

    Returns a structured dictionary used by the database layer and
    visualisation components of the web portal.
    """

    # ------------------------------------------------------------------
    # Step 1: Identify the recombinant gene in the WT plasmid
    # ------------------------------------------------------------------
    """
    1. The ORF detection function scans the plasmid sequence to locate the coding 
    region corresponding to the recombinant enzyme.
    2. A minimum amino acid length threshold helps avoid short spurious ORFs.
    """

    wt_gene = identify_recombinant_gene(
        wt_plasmid_sequence,
        circular=circular,
        min_aa=min_aa
    )

    # ------------------------------------------------------------------
    # Step 2: Identify the recombinant gene in the variant plasmid
    # ------------------------------------------------------------------
    """
    The same ORF detection process is applied to the variant plasmid
    to ensure the CDS is extracted using identical criteria.
    """
    var_gene = identify_recombinant_gene(
        variant_plasmid_sequence,
        circular=circular,
        min_aa=min_aa
    )
    # Extract coding DNA sequences from the detected genes
    wt_cds = wt_gene["cds_dna"]
    var_cds = var_gene["cds_dna"]

    # ------------------------------------------------------------------
    # Step 3: Mutation classification
    # ------------------------------------------------------------------
    """
    The WT and variant CDS are compared codon-by-codon.
    Differences are classified as synonymous or non-synonymous 
    mutations and stored as structured mutation records.
    """

    mutation_result = classify_mutations_cds(
        wt_cds,
        var_cds,
        generation=int(generation)
    )

    # ------------------------------------------------------------------
    # Step 4: Activity score calculation
    # ------------------------------------------------------------------
    """
    The activity score measures catalytic efficiency relative to WT.
    # DNA yield is normalised by protein yield to avoid rewarding
    # variants that simply express more protein.
    
    """

    activity_result = compute_activity_score_log2(
        dna_yield,
        protein_yield,
        wt_dna_yield,
        wt_protein_yield
    )
    # ------------------------------------------------------------------
    # Step 5: Assemble structured analysis output
    # ------------------------------------------------------------------
    """
    The returned dictionary contains WT information, variant information, mutation data, and activity metrics. 
    This format allows direct integration with the database and visualisation modules of the web portal.
    
    """

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