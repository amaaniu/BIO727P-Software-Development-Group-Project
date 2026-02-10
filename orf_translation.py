"""

Goal:
Given a plasmid DNA sequence, identify the recombinant gene, then transcribe + translate to get the corresponding protein sequence.

What this does:
1) Validate DNA
2) Treat as circular DNA (ORFs that wrap around origin)
3) Scan 6 reading frames for ORFs (ATG ... STOP)
4) Translate ORFs to protein sequences
5) Pick the "best" ORF (e.g., longest ORF)
6) Provide transcript (mRNA) + protein sequence for the chosen ORF

"""

from __future__ import annotations
from typing import Optional


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
    """Raised when sequence validation or processing fails."""


def validate_dna(seq):
    """
    Validate and normalise a DNA string.
    Returns: cleaned uppercase DNA sequence.
    """
    if not seq or not seq.strip():
        raise SequenceError("Empty DNA sequence.")

    dna = seq.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").upper()
    
    allowed = set("ACGTN")
    bad = sorted({c for c in dna if c not in allowed}) #shows which characters are invalid (if any)
    if bad:
        raise SequenceError(f"Invalid DNA characters: {', '.join(bad)}")

    if len(dna) < 50: #value can be changed
        raise SequenceError("Sequence too short (min 50 bp).")

    return dna


def reverse_complement(dna):
    """
    Return the reverse complement of a DNA sequence.
    """
    complement = {
        "A": "T",
        "T": "A",
        "C": "G",
        "G": "C",
        "N": "N"
    }

    reverse_sequence = ""

    for base in dna.upper():
        reverse_sequence = complement[base] + reverse_sequence

    return reverse_sequence


def transcribe_dna_to_rna(dna: str) -> str:
    """
    DNA coding strand -> mRNA (T -> U).
    """
    return dna.upper().replace("T", "U")


def translate_dna(dna):
    """
    Translate DNA to protein using CODON_TABLE.
    Unknown codons become 'X'
    """
    dna = dna.upper()
    amino_acid_seq = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        if codon in CODON_TABLE:
            amino_acid_seq.append(CODON_TABLE[codon])
        else:
            amino_acid_seq.append("X")
    return "".join(amino_acid_seq)


# ORF finding
def find_orfs_in_frame(dna, frame, min_aa):
    """
    Find ORFs in ONE reading frame on a DNA string.
    """
    dna = dna.upper()
    orfs = []

    i = frame
    while i <= len(dna) - 3:

        if dna[i:i+3] == "ATG":

            for j in range(i, len(dna) - 2, 3):
                codon = dna[j:j+3]

                if codon in STOP_CODONS:
                    orf_dna = dna[i:j]  # exclude stop codon
                    protein = translate_dna(orf_dna)

                    if len(protein) >= min_aa:
                        orfs.append({
                            "frame": frame,
                            "start_bp": i,
                            "end_bp": j,
                            "dna": orf_dna,
                            "protein": protein
                        })
                    break

        i += 3

    return orfs

def six_frame_orfs(dna, circular=True):
    """
    Get ORFs from all 6 frames (+0,+1,+2 and -0,-1,-2).
    """
    dna = validate_dna(dna)
    original_length = len(dna)

    if circular:
        forward_sequence = dna + dna
    else:
        forward_sequence = dna

    reverse_sequence = reverse_complement(forward_sequence)

    all_orfs = []

    # Forward strand
    for frame in [0, 1, 2]:
        for orf in find_orfs_in_frame(forward_sequence, frame):
            if orf["start_bp"] < original_length:
                all_orfs.append({
                    "frame": f"+{frame}",
                    "start_bp": orf["start_bp"],
                    "dna": orf["dna"],
                    "protein": orf["protein"],
                    "protein_length_aa": len(orf["protein"])
                })

    # Reverse strand
    for frame in [0, 1, 2]:
        for orf in find_orfs_in_frame(reverse_sequence, frame):
            if orf["start_bp"] < original_length:
                all_orfs.append({
                    "frame": f"-{frame}",
                    "start_bp": orf["start_bp"],  # position on reverse_sequence (fine if not using coords)
                    "dna": orf["dna"],
                    "protein": orf["protein"],
                    "protein_length_aa": len(orf["protein"])
                })

    return all_orfs

def pick_longest_orf(orfs):
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

