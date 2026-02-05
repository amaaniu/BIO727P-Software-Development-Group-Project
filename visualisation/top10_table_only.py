from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# location for outputs (locally)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# dummy variant-level data (each row = one variant)
def make_dummy_variants(n_generations: int = 6, variants_per_generation: int = 80, seed: int = 42) -> pd.DataFrame:
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


# save top 10 as CSV and as a PNG table image
def save_top10_outputs(top10: pd.DataFrame) -> None:
    # CSV output
    csv_path = OUTPUT_DIR / "top10_variants.csv"
    top10.to_csv(csv_path, index=False)

    # PNG table output
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")

    display_df = top10.copy()
    display_df["activity_score"] = display_df["activity_score"].map(lambda x: f"{x:.3f}")
    display_df["protein_yield"] = display_df["protein_yield"].map(lambda x: f"{x:.1f}")
    display_df["dna_yield"] = display_df["dna_yield"].map(lambda x: f"{x:.1f}")

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    ax.set_title("Top 10 variants by activity score (dummy data)", pad=12)

    png_path = OUTPUT_DIR / "top10_variants_table.png"
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)
    plt.close(fig)

    print(f"Saved: {csv_path}")
    print(f"Saved: {png_path}")


def main() -> None:
    variants_df = make_dummy_variants()
    top10 = compute_top10(variants_df)
    save_top10_outputs(top10)


if __name__ == "__main__":
    main()
