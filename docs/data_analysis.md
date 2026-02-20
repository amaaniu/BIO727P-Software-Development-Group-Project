# Data Analysis

This page explains analysis logic used by the portal, with emphasis on the Activity Metric.

## Analysis pipeline summary

At a high level, the portal:
1. Ingests validated plasmid and wt protein sequences, with DE experimental run data
2. Applies preprocessing and quality-control rules.
3. Calculates a single Activity Metric for every variant.
4. Ranks variants and produces several visualisations to highlight analysis..

## Activity Metric

Template:

`Activity Score = `

Where:
- `a` is 
- `b` is 
- `c ` is
## Required details for marking

Document the following explicitly:
- Exact formula used in code.
- Definition and units of each variable.
- Normalisation method (include bounds/reference set).
- Handling of missing values and outliers.
- Why this metric is biologically/experimentally meaningful.

## Worked example

Include one fully worked example with real numbers:
1. Input values.
2. Intermediate normalized values.
3. Final Activity Metric.
4. Interpretation of score.

## Output interpretation

Explain how to read each analysis output in the portal:
- Variant ranking table.
- Per-generation trend plot.
- QC summary panel.

## Version note

Last updated: February 20, 2026.
