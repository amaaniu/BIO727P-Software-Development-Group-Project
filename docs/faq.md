# FAQ

## What file formats are supported?

The portal supports `TSV` and `JSON` inputs that match the required schema.

## Do I need a UniProt accession?

Yes. The portal uses the UniProt accession to fetch and validate against the wild-type reference.

## Do I also need plasmid FASTA data?

Yes. Upload plasmid FASTA encoding the variants from your DE run so sequence-level checks and downstream tracking can be performed.

## What does the Activity Metric represent?

It is a composite score used to compare variants based on analysis components defined in `Data Analysis`.
# The full formula and logic are intentionally kept as a template until the final implementation details are available.

## Can I export results?

Yes, ranked outputs and summary tables can be exported for reporting.

## Why was my dataset rejected?

Most rejections are due to schema mismatch, missing required values, or invalid sequence formatting. Validation checks occurs at every data upload point, specifying any issue to users.


## Version note

Last updated: February 20, 2026.
