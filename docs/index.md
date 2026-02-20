# Overview

The Directed Evolution Monitoring & Analytics Portal is a web-based platform for staging, validating, and analysing directed evolution (DE) experiments.

This help manual explains how to:
- Set up and register experiments.
- Upload and validate sequence and assay data.
- Understand quality-control checks.
- Interpret analytical outputs, including the Activity Metric (template section for now).

## What this portal does

The portal supports the full workflow from experiment setup to ranked variant outputs. It can:
- Retrieve wild-type sequence and feature annotations from UniProt.
- Validate uploaded plasmid FASTA and experimental run files.
- Parse and quality-check TSV or JSON datasets.
- Compute a unified Activity Metric used to compare variants (final formula to be added later).
- Provide summaries across rounds/generations.

## Directed evolution context

In this project, DE runs in iterative cycles of mutagenesis, selection, and carry-forward of top variants. The portal is used after each experimental run to:
- register the target using a UniProt accession;
- upload plasmid FASTA encoding the target polymerase variants;
- upload assay output from the run (for example, quantified readouts used for selection);
- track performance across generations.

This keeps experimental records, sequence context, and result interpretation in one place during multi-generation campaigns.

## Who this manual is for

This guide is for new users of the web portal, including students and researchers running directed evolution campaigns.

## Documentation map

- `Getting Started`: account/access requirements and first upload.
- `Workflow`: end-to-end sequence of actions in the portal.
- `Data Analysis`: Activity Metric template, output interpretation, and placeholder sections for formula details.
- `Troubleshooting`: common upload/validation issues and fixes.
- `FAQ`: quick answers to recurring questions.

## Version note

Last updated: February 20, 2026.
