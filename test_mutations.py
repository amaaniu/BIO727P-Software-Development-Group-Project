from mutation_tracker import classify_mutations_cds
from orf_finder import translate_dna

# WT CDS (no stop codon)
wt_cds = "ATG" + "GCT"*5 + "TTC"*5
# ATG = M
# GCT = A
# TTC = F

# Variant:
# GCT -> GCC (synonymous, both Alanine)
# TTC -> TAC (non-synonymous, F -> Y)
var_cds = "ATG" + "GCC" + "GCT"*4 + "TTC"*4 + "TAC"

print("WT protein:", translate_dna(wt_cds))
print("VAR protein:", translate_dna(var_cds))

result = classify_mutations_cds(wt_cds, var_cds)

print("\nSynonymous count:", result["syn_count"])
print("Non-synonymous count:", result["nonsyn_count"])
print("AA substitutions:", result["aa_substitutions"])
print("DNA substitutions:", result["dna_substitutions"])
print("QC flags:", result["qc_flags"])
