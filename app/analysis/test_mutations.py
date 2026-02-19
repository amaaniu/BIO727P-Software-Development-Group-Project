from mutation_tracker import classify_mutations_cds
from app.uploads.orf_translation import translate_dna
from activity_score import compute_activity_scores

# WT CDS (no stop codon)
wt_cds = "ATG" + "GCT"*5 + "TTC"*5

# Variant CDS
# GCT -> GCC (synonymous)
# TTC -> TAC (non-synonymous)
var_cds = "ATG" + "GCC" + "GCT"*4 + "TTC"*4 + "TAC"

print("WT protein:", translate_dna(wt_cds))
print("VAR protein:", translate_dna(var_cds))

generation = 1

# ---- MUTATION TRACKER TEST ----
result = classify_mutations_cds(wt_cds, var_cds, generation)

print("\nSynonymous count:", result["syn_count"])
print("Non-synonymous count:", result["nonsyn_count"])
print("Mutation count:", result["mutation_count"])

print("\nMutation records:")
for m in result["mutation_records"]:
    print(m)


# ---- ACTIVITY SCORE TEST ----
# Example yields
wt_dna_yield = 100.0
wt_protein_yield = 50.0

variant_dna_yield = 120.0
variant_protein_yield = 50.0

activity = compute_activity_scores(
    dna_yield=variant_dna_yield,
    protein_yield=variant_protein_yield,
    wt_dna_yield=wt_dna_yield,
    wt_protein_yield=wt_protein_yield
)

print("\nActivity score results:")
print(activity)



#=========
# test_backend_analysis.py
# Run: python3 test_backend_analysis.py

from backend_analysis import analyse_variant


def make_plasmid_with_orf(cds: str, flank: int = 300) -> str:
    # Simple plasmid-like sequence: flank + CDS + stop + flank
    # (ORF finder expects ATG...STOP; identify_recombinant_gene excludes stop from CDS)
    return ("A" * flank) + cds + "TAA" + ("C" * flank)


def main():
    # WT CDS (no stop codon here; we add stop in plasmid builder)
    # ATG = M
    # GCT = A
    # TTC = F
    wt_cds = "ATG" + ("GCT" * 5) + ("TTC" * 5)  # M AAAAA FFFFF

    # Variant CDS:
    # - codon 2: GCT -> GCC (synonymous A->A)
    # - last codon: TTC -> TAC (nonsynonymous F->Y)
    var_cds = "ATG" + "GCC" + ("GCT" * 4) + ("TTC" * 4) + "TAC"  # M AAAAA FFFFY

    wt_plasmid = make_plasmid_with_orf(wt_cds, flank=400)
    var_plasmid = make_plasmid_with_orf(var_cds, flank=400)

    # Controls baseline for generation 1
    # Use any non-zero numbers; activity score depends on ratios.
    generation = 1
    wt_dna_yield = 30.0
    wt_protein_yield = 50.0

    # Variant yields
    dna_yield = 30.0
    protein_yield = 25.0

    result = analyse_variant(
        wt_plasmid_sequence=wt_plasmid,
        variant_plasmid_sequence=var_plasmid,
        generation=generation,
        dna_yield=dna_yield,
        protein_yield=protein_yield,
        wt_dna_yield=wt_dna_yield,
        wt_protein_yield=wt_protein_yield,
        circular=True,
        min_aa=10,  # small for this toy example
    )

    print("\n=== WT ===")
    print("WT protein:", result["wt"]["protein"])
    print("WT CDS length bp:", result["wt"]["cds_length_bp"])
    print("WT protein length aa:", result["wt"]["protein_length_aa"])

    print("\n=== VARIANT ===")
    print("VAR protein:", result["variant"]["protein"])
    print("VAR CDS length bp:", result["variant"]["cds_length_bp"])
    print("VAR protein length aa:", result["variant"]["protein_length_aa"])

    print("\n=== MUTATIONS ===")
    muts = result["mutations"]
    print("Synonymous count:", muts["syn_count"])
    print("Non-synonymous count:", muts["nonsyn_count"])
    print("Mutation count:", muts["mutation_count"])
    print("Mutation records:")
    for r in muts["mutation_records"]:
        print(r)

    print("\n=== ACTIVITY ===")
    print(result["activity"])

    print("\n=== SUMMARY ===")
    print(result["variant_summary"])


if __name__ == "__main__":
    main()