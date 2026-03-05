# Troubleshooting

Use this page to quickly diagnose common user issues.

## Upload errors

### Unsupported file type

Symptom:

- Upload fails immediately.

Fix:

- Use `.tsv` or `.json` files only.

### Missing required fields

Symptom:

- Validation reports missing columns/keys.

Fix:

- Ensure required fields are present and named exactly as expected.

## Sequence validation errors

### Invalid sequence characters

Symptom:

- Rows flagged for incorrect (non-DNA) symbols.

Fix:

- Remove non-biological characters and whitespace.
- Confirm DNA/protein alphabet expected by your pipeline.

### Length mismatch

Symptom:

- Sequence length check fails.

Fix:

- Verify target region and alignment with reference/wild-type.

## Analysis issues

### No Activity Metric generated

Symptom:

- Analysis completes with empty score column.

Fix:

- Check for missing activity inputs.
- Confirm preprocessing did not filter all rows.

### Unexpected ranking

Symptom:

- High-performing known variants rank low.

Fix:

- Review normalisation method and metric weights.
- Verify replicate handling and outlier rules.

## Version note

Last updated: February 20, 2026.
