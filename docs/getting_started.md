# Getting Started

This page helps first-time users complete their first successful analysis run.

## Prerequisites

Before using the portal, ensure you have:
- Access credentials for the web portal.
- A valid UniProt accession for the target wildtype protein from your research
- Input files in one of the supported formats (`.tsv` or `.json`).

## Recommended first run

1. Sign in to the portal.
2. Create a new experiment.
3. Enter target metadata, including the UniProt accession.
4. Upload plasmid FASTA for the run.
5. Upload run data (`.tsv` or `.json`) containing assay outputs and identifiers.
6. Resolve validation warnings or errors.
7. Run analysis and review the generated outputs, including Activity Metric fields where available.

## Input data expectations

Document your real schema here. Typical fields include:
- Variant or clone ID.
- Sequence (DNA or protein, depending on pipeline).
- Round/generation label.
- Raw activity measurement(s).
- Optional metadata (plate, condition, replicate).

## Supported files

- `TSV`: tab-separated text with a header row.
- `JSON`: array/object format matching portal schema.

## Access and permissions

Describe role behavior in your portal:
- Viewer: read-only results access.
- Editor: upload and run analysis.
- Admin: manage experiments and users.

## Version note

Last updated: February 20, 2026.
