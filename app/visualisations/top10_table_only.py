# top 10 variants by activity_score_log2

import pandas as pd


def compute_top10(variants_df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "variant_id",
        "generation",
        "activity_score_log2",
        "mutation_count",
        "protein_yield",
        "dna_yield",
    ]

    missing = set(cols) - set(variants_df.columns)
    if missing:
        raise ValueError(f"Missing required columns for top10: {missing}")

    top10 = (
        variants_df[cols]
        .sort_values("activity_score_log2", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    return top10
