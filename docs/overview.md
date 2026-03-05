# Overview

The Directed Evolution Monitoring & Analytics Portal is a web-based platform for staging and analysing directed evolution (DE) experiments.

This help manual explains how to:

- Set up an analysis.
- Upload and validate your data.
- Interpret analytical outputs, including the Activity Score.

## What this portal does

The portal supports the full workflow from experiment setup to ranked variant outputs. It can:

- Retrieve details of the wild-type protein from UniProt.
- Validate uploaded plasmid FASTA and experimental run files.
- Compute a unified metric for Activity used to compare variants.
- Tracks mutations across generations.
- Identifies the best performing variants.

## Directed evolution context

In this project, DE runs in iterative cycles of mutagenesis, selection, and carry-forward of top variants. The portal is used after each experimental run to:

- register the target protein using a UniProt accession code;
- upload plasmid FASTA encoding the target polymerase;
- upload assay output from the run (for example, DNA and protein quantification, used for selection);
- identify the best performing variants and track performance across generations.

This keeps experimental records, sequence context, and results in one place during multi-generation studies.

## Who this manual is for

This guide is for new users of the web portal, including students and researchers running directed evolution campaigns that can be easily monitored and analysed with this tool.

## Documentation map

- `Getting Started`: account/access requirements and how to upload data.
- `Workflow`: end-to-end sequence of actions in the portal.
- `Data Analysis`: details on the analytical capacity of the web portal: Activity Score breakdown, output interpretation, and visuals.
- `Troubleshooting`: common upload/validation issues and fixes.
- `FAQ`: quick answers to recurring questions.

## Version note

Last updated: February 20, 2026.
