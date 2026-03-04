"""
Goal:
Given a plasmid DNA sequence, identify the recombinant gene, then transcribe + translate to get the corresponding protein sequence.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple

# Genetic code
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
    """Raised when DNA validation or ORF discovery cannot proceed safely."""
    pass
    # raised when sequence validation or processing fails.


def validate_dna(seq):
    """Validate and normalise a DNA sequence string.

    Args:
        seq: Raw DNA sequence text supplied by the caller.

    Returns:
        str: Cleaned uppercase DNA sequence containing only supported bases.
    """
    """
    Validate and normalise a DNA string.
    Returns: cleaned uppercase DNA sequence.
    """
    if not seq or not seq.strip():
        raise SequenceError("Empty DNA sequence.")

    # Normalise whitespace early so every downstream function sees the same sequence format.
    dna = seq.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").upper()
    
    allowed = set("ACGTN")
    bad = sorted({c for c in dna if c not in allowed}) #shows which characters are invalid (if any)
    if bad:
        raise SequenceError(f"Invalid DNA characters: {', '.join(bad)}")

    if len(dna) < 50: #value can be changed
        raise SequenceError("Sequence too short (min 50 bp).")

    return dna

def reverse_complement(dna):
    """Return the reverse complement of a DNA sequence.

    Args:
        dna: Input DNA sequence.

    Returns:
        str: Reverse-complemented DNA sequence.
    """
    """
    Return the reverse complement of a DNA sequence.
    """
    complement = {"A": "T", "T": "A","C": "G","G": "C","N": "N"}
    dna= dna.upper()
    return "".join(complement[b] for b in reversed(dna))


def transcribe_dna_to_rna(dna: str) -> str:
    """Transcribe a DNA coding strand into RNA.

    Args:
        dna: DNA sequence on the coding strand.

    Returns:
        str: RNA sequence with thymine replaced by uracil.
    """
    """
    DNA coding strand -> mRNA (T -> U).
    """
    return dna.upper().replace("T", "U")


def translate_dna(dna):
    """Translate a DNA sequence into a protein sequence.

    Args:
        dna: DNA coding sequence to translate.

    Returns:
        str: Amino-acid sequence produced from codon translation.
    """
    """
    Translate DNA to protein using CODON_TABLE.
    Unknown codons become 'X'
    """
    dna = dna.upper()
    amino_acid_seq = []
    # Translation truncates incomplete trailing codons by stepping in triplets only.
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        if codon in CODON_TABLE:
            amino_acid_seq.append(CODON_TABLE[codon])
        else:
            amino_acid_seq.append("X")
    return "".join(amino_acid_seq)

def _orf_endpoints_in_seq(dna, frame):
    """Find ORF start and end coordinates within a single reading frame.

    Args:
        dna: DNA sequence to scan.
        frame: Reading frame offset (0, 1, or 2).

    Returns:
        list[tuple[int, int]]: Start and end coordinates for ATG-to-stop ORFs,
        with the stop codon excluded from the end position.
    """
    """
    Returns ORF endpoints (start_bp, end_bp_exclusive) for ORFs in a single frame.
    ORF defined as ATG ... STOP (stop excluded).
    """
    out = []
    i = frame
    L = len(dna)
    # Walk codon-by-codon within a single frame so start/stop detection stays frame-consistent.
    while i <= L - 3:
        if dna[i:i+3] == "ATG":
            j = i + 3
            while j <= L - 3:
                codon = dna[j:j+3]
                if codon in STOP_CODONS:
                    out.append((i, j))  
                    i = j + 3            
                    break
                j += 3
            else:
                # no stop found; move on one codon
                i += 3
                continue
            continue
        i += 3
    return out

# ORF finding
def find_orfs_in_frame(dna, frame, min_aa, max_bp=None):
    """Find ORFs within one reading frame on a DNA sequence.

    Args:
        dna: DNA sequence to scan.
        frame: Reading frame offset (0, 1, or 2).
        min_aa: Minimum translated protein length to keep.
        max_bp: Optional maximum ORF length in base pairs.

    Returns:
        list[dict]: ORF records with frame, coordinates, DNA, and translated protein.
    """
    """
    Find ORFs in ONE reading frame on a DNA string.
    """
    dna = dna.upper()
    orfs = []
    for start, end in _orf_endpoints_in_seq(dna, frame):
        if max_bp is not None and (end - start) > max_bp:
            continue
        # The stop codon is excluded so the translated sequence does not end with '*'.
        orf_dna = dna[start:end]
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

def _map_rev_start_to_fwd(start_bp_rev, orig_len):
    """Map a reverse-complement coordinate back onto the forward strand.

    Args:
        start_bp_rev: Position on the reverse-complemented sequence.
        orig_len: Length of the original forward DNA sequence.

    Returns:
        int: Equivalent 0-based coordinate on the forward strand.
    """
    """
    Map a start position on the reverse-complemented sequence back to a forward coordinate.
    This gives a forward-coordinate of the *corresponding* base position (0-based).
    """
    # reverse index 0 corresponds to forward index (len-1)
    return (orig_len - 1 - start_bp_rev) % orig_len

def six_frame_orfs(dna, circular=True, min_aa=50):
    """Find ORFs across all six reading frames of a DNA sequence.

    Args:
        dna: DNA sequence to scan.
        circular: Whether to treat the plasmid as circular for wraparound ORFs.
        min_aa: Minimum translated ORF length to keep.

    Returns:
        list[dict]: ORF records from forward and reverse strands with coordinates,
        wraparound flags, DNA, and translated protein.
    """
    """
    Get ORFs from all 6 frames (+0,+1,+2 and -0,-1,-2).
    """
    dna = validate_dna(dna)
    original_length = len(dna)

    # Doubling the sequence lets wraparound ORFs be discovered with ordinary linear scans.
    if circular:
        forward_sequence = dna + dna
    else:
        forward_sequence = dna

    reverse_sequence = reverse_complement(forward_sequence)

    all_orfs = []
    max_bp= original_length if circular else None

    # Scan the forward strand directly in all three frames.
    for frame in (0, 1, 2):
        for orf in find_orfs_in_frame(forward_sequence, frame, min_aa=min_aa, max_bp=max_bp):
            if orf["start_bp"] < original_length:
                start = orf["start_bp"]
                end = orf["end_bp"]
                wrap = end > original_length
                all_orfs.append({
                    "strand": "+",
                    "frame": f"+{frame}",
                    "start_bp": start % original_length,
                    "end_bp": end % original_length,
                    "wraparound": wrap,
                    "dna": orf["dna"],
                    "protein": orf["protein"],
                    "protein_length_aa": orf.get("protein_length_aa", len(orf["protein"]))
                })

    # Scan the reverse complement and map coordinates back onto the forward plasmid.
    for frame in (0, 1, 2):
        for orf in find_orfs_in_frame(reverse_sequence, frame, min_aa=min_aa, max_bp=max_bp):
            if orf["start_bp"] < original_length:
                # map start/end back to forward coords (approx; good enough for reporting)
                start_fwd = _map_rev_start_to_fwd(orf["start_bp"], original_length)
                end_fwd = _map_rev_start_to_fwd(orf["end_bp"], original_length)
                wrap = orf["end_bp"] > original_length
                all_orfs.append({
                    "strand": "-",
                    "frame": f"-{frame}",
                    "start_bp": start_fwd,
                    "end_bp": end_fwd,
                    "wraparound": wrap,
                    "dna": orf["dna"],
                    "protein": orf["protein"],
                    "protein_length_aa": orf.get("protein_length_aa", len(orf["protein"]))
                })


    return all_orfs

def pick_longest_orf(orfs):
    """Select the ORF with the longest translated protein sequence.

    Args:
        orfs: ORF records to compare.

    Returns:
        dict: The ORF record with the maximum protein length.
    """
    """
    Pick the "best" ORF as the one with the longest protein sequence.
    """
    if not orfs:
        raise SequenceError("No ORFs found.")

    best = orfs[0]
    for orf in orfs:
        if orf["protein_length_aa"] > best["protein_length_aa"]:
            best = orf 

    return best

def _simple_identity(a, b):
    """Compute simple positional identity between two protein sequences.

    Args:
        a: First protein sequence.
        b: Second protein sequence.

    Returns:
        float: Fraction of matching positions over the overlapping region.
    """
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
    """Choose the most likely recombinant ORF.

    Args:
        orfs: Candidate ORF records.
        wt_protein: Optional wild-type protein used to score sequence identity.

    Returns:
        dict: The selected ORF record, optionally annotated with match identity.
    """
    if not orfs:
        raise SequenceError("No ORFs found.")

    if wt_protein:
        wt = wt_protein.strip().upper()
        # When WT is available, prefer biological similarity before raw ORF length.
        # prioritise: highest identity, then longer length
        best = max(orfs, key=lambda o: (_simple_identity(o["protein"], wt), o["protein_length_aa"]))
        best_out = dict(best)
        best_out["match_identity"] = _simple_identity(best_out["protein"], wt)
        return best_out

    return max(orfs, key=lambda o: o["protein_length_aa"])

def identify_recombinant_gene(
    plasmid_dna: str,
    wt_protein: Optional[str] = None,
    circular: bool = True,
    min_aa: int = 200,
) -> Dict[str, Any]:
    """Identify the most likely recombinant coding sequence in a plasmid.

    Args:
        plasmid_dna: Full plasmid DNA sequence.
        wt_protein: Optional wild-type protein sequence used to rank ORFs.
        circular: Whether to treat the plasmid as circular.
        min_aa: Minimum ORF length in amino acids.

    Returns:
        dict: Selected ORF metadata plus CDS DNA, mRNA, protein, and length fields.
    """
    orfs = six_frame_orfs(plasmid_dna, circular=circular, min_aa=min_aa)
    best = pick_best_orf(orfs, wt_protein=wt_protein)

    # Expose DNA, RNA, and protein forms together so downstream code can report each stage explicitly.
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

 
