# functions for generating the Top 10 variants table (without saving to file):

import pandas as pd


# top 10 variants by activity_score
def compute_top10(variants_df: pd.DataFrame) -> pd.DataFrame:

    cols = ["variant_id", "generation", "activity_score", "mutation_count", "protein_yield", "dna_yield"]

    top10 = (
        variants_df[cols]
        .sort_values("activity_score", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    return top10