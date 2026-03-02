# Data Analysis

This page explains analysis logic used by the portal, with emphasis on the Activity Metric.

## Analysis pipeline summary

At a high level, the portal:

1. Ingests validated plasmid and wt protein sequences, with DE experimental run data
2. Applies preprocessing and quality-control rules.
3. Calculates a single Activity Score for every variant.
4. Ranks variants and produces several visualisations as part of the analysis.

## Activity Score

For each variant in generation \( g \), the Activity Score is defined as:

$$
\text{ActivityScore}_g
= \log_2\!\left(
\left[\frac{\text{DNA Yield}_g}{\text{WT DNA Yield}_{g^*}}\right]
\Big/
\left[\frac{\text{Protein Yield}_g}{\text{WT Protein Yield}_{g^*}}\right]
\right)
$$

### Baseline Rule

The reference generation \( g^* \) is defined as:

$$
g^* =
\begin{cases}
1 & \text{if } g = 1 \\
g - 1 & \text{if } g \ge 2
\end{cases}
$$

- Generation **1** variants are normalised to **Generation 1 WT**
- Generation **\( g \ge 2 \)** variants are normalised to the **WT from the previous generation**

---

### Term Definitions

- **DNA Yield\(_g\)** — Measured DNA output of the variant in generation \( g \)
- **WT DNA Yield\(_{g^*}\)** — DNA output of the reference wild-type for generation \( g^* \)
- **Protein Yield\(_g\)** — Measured protein expression level of the variant in generation \( g \)
- **WT Protein Yield\(_{g^*}\)** — Protein expression level of the reference wild-type for generation \( g^* \)

---

### Interpretation

The Activity Score can be interpreted as:

$$
\text{ActivityScore} =
\log_2
\left(
\frac{\text{Catalytic Output (relative to WT)}}
{\text{Expression Level (relative to WT)}}
\right)
$$

- **Score > 0** → Improved catalytic efficiency relative to WT  
- **Score = 0** → Equivalent to WT  
- **Score < 0** → Reduced catalytic efficiency relative to WT  

## Version note

Last updated: February 20, 2026.
