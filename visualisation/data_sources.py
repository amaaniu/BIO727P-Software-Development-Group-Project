# function for generating dummy data for testing and development purposes
# dummy variant-level data (each row = one variant)

# functions for generating dummy data for testing and development purposes
# dummy variant-level data (each row = one variant)

import numpy as np
import pandas as pd


# generate dummy variants
def make_dummy_variants(
    n_generations: int = 6,
    variants_per_generation: int = 80,
    seed: int = 42
) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    rows = []
    variant_id = 1

    for gen in range(1, n_generations + 1):
        for _ in range(variants_per_generation):

            mutation_count = int(max(0, rng.normal(loc=gen * 1.2, scale=1.5)))

            base_activity = 0.8 + gen * 0.25
            activity_score = float(rng.normal(loc=base_activity, scale=0.35))
            activity_score = max(0.0, activity_score)

            protein_yield = float(max(0.0, rng.normal(loc=50 + gen * 5, scale=10)))
            dna_yield = float(max(0.0, rng.normal(loc=30 + gen * 3, scale=8)))

            rows.append(
                {
                    "variant_id": variant_id,
                    "generation": gen,
                    "activity_score": activity_score,
                    "mutation_count": mutation_count,
                    "protein_yield": protein_yield,
                    "dna_yield": dna_yield,
                }
            )
            variant_id += 1

    return pd.DataFrame(rows)


# data access function for visualisation module
# later this will be switched out to database / API source
def get_variants(experiment_id: int | None = None, source: str = "dummy") -> pd.DataFrame:

    if source == "dummy":
        return make_dummy_variants()

    raise ValueError(f"Unknown source: {source}")