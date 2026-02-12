from __future__ import annotations
from typing import Dict, Any, List, Optional

from orf_finder import CODON_TABLE  

def _translate_codon(codon: str) -> str:
    """Translate one codon. Unknown/ambiguous -> 'X'."""
    codon = codon.upper().replace("U", "T")
    return CODON_TABLE.get(codon, "X")


def _fmt_dna_sub(pos_1based: int, wt_base: str, var_base: str) -> str:
    """DNA substitution like c.123A>G (1-based CDS coordinate)."""
    return f"c.{pos_1based}{wt_base}>{var_base}"


def _fmt_aa_sub(pos_1based: int, wt_aa: str, var_aa: str) -> str:
    """AA substitution like A123T."""
    return f"{wt_aa}{pos_1based}{var_aa}"


def classify_mutations_cds(
    wt_cds: str,
    var_cds: str,
    *,
    allow_length_mismatch: bool = False
) -> Dict[str, Any]:
    """
    Compare WT CDS DNA vs Variant CDS DNA codon-by-codon.

    Output is substitution-focused (syn/nonsyn). If indels/frameshifts exist,
    we flag via qc_flags and compare only overlapping full codons.

    Returns dict with:
      syn_count, nonsyn_count
      dna_substitutions (list[str])
      aa_substitutions (list[str])
      syn_codons, nonsyn_codons (list[dict] for debugging)
      stop_gained, stop_lost
      qc_flags (list[str])
    """
    qc: List[str] = []

    wt = (wt_cds or "").strip().upper().replace("U", "T")
    var = (var_cds or "").strip().upper().replace("U", "T")

    if not wt:
        raise ValueError("WT CDS is empty.")
    if not var:
        raise ValueError("Variant CDS is empty.")

    # Frame checks
    if len(wt) % 3 != 0:
        qc.append("wt_len_not_multiple_of_3")
    if len(var) % 3 != 0:
        qc.append("var_len_not_multiple_of_3")

    # Length checks
    if len(wt) != len(var):
        if not allow_length_mismatch:
            qc.append("length_mismatch")
        else:
            qc.append("length_mismatch_allowed")

    # Compare only overlapping full codons
    n_codons = min(len(wt), len(var)) // 3
    if n_codons == 0:
        qc.append("no_full_codons_to_compare")

    dna_subs: List[str] = []
    aa_subs: List[str] = []
    syn_codons: List[Dict[str, Any]] = []
    nonsyn_codons: List[Dict[str, Any]] = []

    stop_gained = False
    stop_lost = False

    for codon_i in range(n_codons):
        start = codon_i * 3
        wt_codon = wt[start:start + 3]
        var_codon = var[start:start + 3]

        if wt_codon == var_codon:
            continue

        # Record per-base substitutions for this codon
        for k in range(3):
            if wt_codon[k] != var_codon[k]:
                dna_subs.append(_fmt_dna_sub(start + k + 1, wt_codon[k], var_codon[k]))

        wt_aa = _translate_codon(wt_codon)
        var_aa = _translate_codon(var_codon)

        # QC: ambiguous bases
        if "N" in wt_codon or "N" in var_codon:
            qc.append("ambiguous_base_N_present")

        event = {
            "codon_index_1based": codon_i + 1,
            "nt_start_1based": start + 1,
            "wt_codon": wt_codon,
            "var_codon": var_codon,
            "wt_aa": wt_aa,
            "var_aa": var_aa,
        }

        if wt_aa == var_aa:
            syn_codons.append(event)
        else:
            nonsyn_codons.append(event)
            aa_subs.append(_fmt_aa_sub(codon_i + 1, wt_aa, var_aa))

            if wt_aa != "*" and var_aa == "*":
                stop_gained = True
            if wt_aa == "*" and var_aa != "*":
                stop_lost = True

    return {
        "syn_count": len(syn_codons),
        "nonsyn_count": len(nonsyn_codons),
        "dna_substitutions": dna_subs,
        "aa_substitutions": aa_subs,
        "syn_codons": syn_codons,
        "nonsyn_codons": nonsyn_codons,
        "stop_gained": stop_gained,
        "stop_lost": stop_lost,
        "qc_flags": sorted(set(qc)),
    }


def aa_mutations_from_proteins(wt_protein: str, var_protein: str) -> Dict[str, Any]:
    """
    Simple protein-only mutation list (QC helper).
    """
    wt = (wt_protein or "").strip().upper()
    var = (var_protein or "").strip().upper()

    n = min(len(wt), len(var))
    aa_subs: List[str] = []

    for i in range(n):
        if wt[i] != var[i]:
            aa_subs.append(_fmt_aa_sub(i + 1, wt[i], var[i]))

    return {
        "aa_length_wt": len(wt),
        "aa_length_var": len(var),
        "length_mismatch": len(wt) != len(var),
        "aa_sub_count_overlap": len(aa_subs),
        "aa_substitutions": aa_subs,
    }