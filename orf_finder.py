
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple

CODON_TABLE = {
    "TTT": "F", "TTC": "F",
    "TTA": "L", "TTG": "L", "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S", "AGT": "S", "AGC": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    "TAA": "*", "TAG": "*", "TGA": "*",
}
STOP_CODONS = {"TAA", "TAG", "TGA"}

class SequenceError(ValueError):
    pass

def validate_dna(seq: str) -> str:
    if not seq or not seq.strip():
        raise SequenceError("Empty DNA sequence.")
    dna = seq.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").upper()
    allowed = set("ACGTN")
    bad = sorted({c for c in dna if c not in allowed})
    if bad:
        raise SequenceError(f"Invalid DNA characters: {', '.join(bad)}")
    if len(dna) < 50:
        raise SequenceError("Sequence too short (min 50 bp).")
    return dna

def reverse_complement(dna: str) -> str:
    comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N"}
    dna = dna.upper()
    return "".join(comp[b] for b in reversed(dna))

def transcribe_dna_to_rna(dna: str) -> str:
    return dna.upper().replace("T", "U")

def translate_dna(dna: str) -> str:
    dna = dna.upper()
    aa = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        aa.append(CODON_TABLE.get(codon, "X"))
    return "".join(aa)

def _orf_endpoints_in_seq(seq: str, frame: int) -> List[Tuple[int, int]]:
    """
    Returns ORF endpoints (start_bp, end_bp_exclusive) for ORFs in a single frame.
    ORF defined as ATG ... STOP (stop excluded).
    """
    out = []
    i = frame
    while i <= len(seq) - 3:
        if seq[i:i+3] == "ATG":
            j = i
            while j <= len(seq) - 3:
                codon = seq[j:j+3]
                if codon in STOP_CODONS:
                    out.append((i, j))  # stop excluded
                    break
                j += 3
            # continue scanning after this start (keeps your original behaviour)
        i += 3
    return out

def find_orfs_in_frame(
    seq: str,
    frame: int,
    min_aa: int,
    max_bp: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    seq: DNA sequence to scan (already upper).
    frame: 0/1/2
    min_aa: minimum protein length
    max_bp: optional cap on ORF length in bp (prevents looping around a circular plasmid twice)
    """
    orfs = []
    for start, end in _orf_endpoints_in_seq(seq, frame):
        if max_bp is not None and (end - start) > max_bp:
            continue
        orf_dna = seq[start:end]
        prot = translate_dna(orf_dna)
        if len(prot) >= min_aa:
            orfs.append({
                "frame": frame,
                "start_bp": start,
                "end_bp": end,
                "dna": orf_dna,
                "protein": prot,
                "protein_length_aa": len(prot),
            })
    return orfs

def _map_rev_start_to_fwd(start_bp_rev: int, orig_len: int) -> int:
    """
    Map a start position on the reverse-complemented sequence back to a forward coordinate.
    This gives a forward-coordinate of the *corresponding* base position (0-based).
    """
    # reverse index 0 corresponds to forward index (len-1)
    return (orig_len - 1 - start_bp_rev) % orig_len

def six_frame_orfs(
    plasmid_dna: str,
    circular: bool = True,
    min_aa: int = 50,
) -> List[Dict[str, Any]]:
    dna = validate_dna(plasmid_dna)
    L = len(dna)

    fwd = dna + dna if circular else dna
    rev = reverse_complement(fwd)

    all_orfs: List[Dict[str, Any]] = []
    max_bp = L if circular else None  # prevents multi-lap ORFs in circular mode

    # Forward strand
    for frame in (0, 1, 2):
        for orf in find_orfs_in_frame(fwd, frame, min_aa=min_aa, max_bp=max_bp):
            if orf["start_bp"] < L:
                start = orf["start_bp"]
                end = orf["end_bp"]
                wrap = end > L
                all_orfs.append({
                    "strand": "+",
                    "frame": f"+{frame}",
                    "start_bp": start % L,
                    "end_bp": end % L,
                    "wraparound": wrap,
                    "dna": orf["dna"][:L] if wrap else orf["dna"],
                    "protein": orf["protein"][: (L // 3)] if wrap else orf["protein"],
                    "protein_length_aa": len(orf["protein"][: (L // 3)]) if wrap else orf["protein_length_aa"],
                })

    # Reverse strand
    for frame in (0, 1, 2):
        for orf in find_orfs_in_frame(rev, frame, min_aa=min_aa, max_bp=max_bp):
            if orf["start_bp"] < L:
                # map start/end back to forward coords (approx; good enough for reporting)
                start_fwd = _map_rev_start_to_fwd(orf["start_bp"], L)
                end_fwd = _map_rev_start_to_fwd(orf["end_bp"], L)
                wrap = orf["end_bp"] > L
                all_orfs.append({
                    "strand": "-",
                    "frame": f"-{frame}",
                    "start_bp": start_fwd,
                    "end_bp": end_fwd,
                    "wraparound": wrap,
                    "dna": orf["dna"][:L] if wrap else orf["dna"],
                    "protein": orf["protein"][: (L // 3)] if wrap else orf["protein"],
                    "protein_length_aa": len(orf["protein"][: (L // 3)]) if wrap else orf["protein_length_aa"],
                })

    return all_orfs

def _simple_identity(a: str, b: str) -> float:
    """
    Simple position-wise identity on the overlapping region.
    (Not a full alignment; good lightweight scoring for close sequences.)
    """
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    matches = sum(1 for i in range(n) if a[i] == b[i])
    return matches / n

def pick_best_orf(orfs: List[Dict[str, Any]], wt_protein: Optional[str] = None) -> Dict[str, Any]:
    if not orfs:
        raise SequenceError("No ORFs found.")

    if wt_protein:
        wt = wt_protein.strip().upper()
        # prioritise: highest identity, then longer length
        best = max(orfs, key=lambda o: (_simple_identity(o["protein"], wt), o["protein_length_aa"]))
        best["match_identity"] = _simple_identity(best["protein"], wt)
        return best

    return max(orfs, key=lambda o: o["protein_length_aa"])

def identify_recombinant_gene(
    plasmid_dna: str,
    wt_protein: Optional[str] = None,
    circular: bool = True,
    min_aa: int = 200,
) -> Dict[str, Any]:
    orfs = six_frame_orfs(plasmid_dna, circular=circular, min_aa=min_aa)
    best = pick_best_orf(orfs, wt_protein=wt_protein)

    cds_dna = best["dna"]
    mrna = transcribe_dna_to_rna(cds_dna)
    protein = best["protein"]

    return {
        **best,
        "cds_dna": cds_dna,
        "mrna": mrna,
        "protein": protein,

        "plasmid_length": len(validate_dna(plasmid_dna)),
        "cds_length_bp": len(cds_dna),
        "protein_length_aa": len(protein),
    }
