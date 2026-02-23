# Getting Started

This page helps first-time users complete their first successful analysis run.

## Prerequisites

Before using the portal, ensure you have:
- Registered an account for the platform.
- A valid UniProt accession for the target wildtype protein from your research.
- Input files in one of the supported formats (`.tsv` or `.json`).

## Recommended first run

1. Sign in to the portal.
2. Create a new experiment.
3. Enter target metadata, including the UniProt accession.
4. Upload plasmid FASTA for the run.
5. Upload the data from your experimental run (`.tsv` or `.json`) containing assay outputs, DNA sequences and variant identifiers.
6. Resolve validation warnings or errors (if there are any present).
7. Run analysis and review the generated outputs, which can be saved as a PDF.

## Input data expectations

Document your real schema here. Typical fields include:
- Variant ID.
- Sequence DNA.
- Round/generation label for every variant.
- Raw DNA and protein abundances for every variant.
- Optional metadata.

## Supported files

- `TSV`: tab-separated text with a header row.
- `JSON`: array/object format, structured as key/value pairs.

## Access and permissions

Describe role behavior in your portal:
- Viewer: read-only results access.
- Editor: upload and run analysis.
- Admin: manage experiments and users.

## Version note

Last updated: February 20, 2026.
