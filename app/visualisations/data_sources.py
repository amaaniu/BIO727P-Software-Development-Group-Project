"""
Data access layer for the visualisation package.

Supports:
- 'dummy' synthetic data for development/demo
- 'db_export' JSON files exported from the backend

"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SourceType = Literal["dummy", "db_export"]


def make_dummy_variants(
    n_generations: int = 6,
    variants_per_generation: int = 80,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a synthetic variants table (one row per variant) for development.

    The dummy data simulates gradual improvement across generations and computes an Activity Score
    using the same WT-normalised ratio used in the real pipeline.

    Parameters
    ----------
    n_generations:
        Number of directed evolution generations to simulate.
    variants_per_generation:
        Number of variants per generation.
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    pandas.DataFrame
        Columns include:
        - variant_id, generation, dna_yield, protein_yield
        - dna_norm, protein_norm, activity_score_raw, activity_score_log2
        - mutation_count
    """
    rng = np.random.default_rng(seed)

    rows = []
    variant_id = 1

    wt_dna_by_gen = {g: 30 + g * 3 for g in range(1, n_generations + 1)}
    wt_protein_by_gen = {g: 50 + g * 5 for g in range(1, n_generations + 1)}

    for gen in range(1, n_generations + 1):
        wt_dna = float(wt_dna_by_gen[gen])
        wt_protein = float(wt_protein_by_gen[gen])

        for _ in range(variants_per_generation):
            mutation_count = int(max(0, rng.normal(loc=gen * 1.2, scale=1.5)))

            protein_yield = float(max(0.0, rng.normal(loc=50 + gen * 5, scale=10)))
            dna_yield = float(max(0.0, rng.normal(loc=30 + gen * 3, scale=8)))

            dna_norm = dna_yield / wt_dna if wt_dna else None
            protein_norm = protein_yield / wt_protein if wt_protein else None

            activity_raw = None
            activity_log2 = None
            if dna_norm is not None and protein_norm not in (None, 0):
                activity_raw = dna_norm / protein_norm
                activity_log2 = math.log2(activity_raw) if activity_raw and activity_raw > 0 else None

            rows.append(
                {
                    "variant_id": variant_id,
                    "generation": gen,
                    "dna_yield": dna_yield,
                    "protein_yield": protein_yield,
                    "dna_norm": dna_norm,
                    "protein_norm": protein_norm,
                    "activity_score_raw": activity_raw,
                    "activity_score_log2": activity_log2,
                    "mutation_count": mutation_count,
                }
            )
            variant_id += 1

    return pd.DataFrame(rows)


def load_variants_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the variants summary exported from the backend.

    Parameters
    ----------
    path:
        JSON file path produced by the backend exporter.

    Returns
    -------
    pandas.DataFrame
        Variants table with basic type coercion applied.
    """
    path = Path(path)
    df = pd.read_json(path)

    for col in ("generation", "activity_score_log2", "mutation_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_mutations_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the mutations table exported from the backend.

    Parameters
    ----------
    path:
        JSON file path produced by the backend exporter.

    Returns
    -------
    pandas.DataFrame
        Mutations table with basic type coercion applied.
    """
    path = Path(path)
    df = pd.read_json(path)

    for col in ("generation", "position"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_variants(
    experiment_id: int | None = None,
    source: SourceType = "dummy",
    variants_json_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Single entry point to obtain a variants dataframe for plotting.

    Parameters
    ----------
    experiment_id:
        Reserved for future direct DB access (not used in the JSON-based visualisation flow).
    source:
        'dummy' or 'db_export'.
    variants_json_path:
        Required if source='db_export'.

    Returns
    -------
    pandas.DataFrame
    """
    if source == "dummy":
        return make_dummy_variants()

    if source == "db_export":
        if not variants_json_path:
            raise ValueError("variants_json_path must be provided when source='db_export'")
        return load_variants_from_json(variants_json_path)

    raise ValueError(f"Unknown source: {source}")


def get_mutations(
    experiment_id: int | None = None,
    source: SourceType = "db_export",
    mutations_json_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Single entry point to obtain a mutations dataframe for bonus plots.

    Parameters
    ----------
    experiment_id:
        Reserved for future direct DB access (not used in the JSON-based visualisation flow).
    source:
        Currently only 'db_export' is supported.
    mutations_json_path:
        Required if source='db_export'.

    Returns
    -------
    pandas.DataFrame
    """
    if source == "db_export":
        if not mutations_json_path:
            raise ValueError("mutations_json_path must be provided when source='db_export'")
        return load_mutations_from_json(mutations_json_path)

    raise ValueError(f"Unknown source: {source}")

"""
Database export helpers for visualisation.

This module extracts analysis-ready tables from the application database and computes
the unified Activity Score for each variant using WT control baselines per generation.

Returned objects are plain Python lists of dicts to make serialisation (e.g., JSON) straightforward.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from models import ControlData, Mutations, Variant, db

logger = logging.getLogger(__name__)


_WT_LABELS = {"wt", "wildtype", "wild_type", "wild-type", "control_wt"}


def _is_wt_control(control_type: Optional[str]) -> bool:
    """
    Check if a control label corresponds to a WT control.

    Parameters
    ----------
    control_type:
        Free-text label stored for a control row.

    Returns
    -------
    bool
        True if label looks like a WT control, else False.
    """
    if not control_type:
        return False
    return control_type.strip().lower() in _WT_LABELS


def fetch_variant_summary(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-variant summary table for an experiment.

    Includes:
    - raw yields (dna_yield, protein_yield)
    - WT-normalised yields per generation (dna_norm, protein_norm)
    - unified Activity Score (activity_score_log2)
    - mutation_count and protein_sequence for downstream visualisations

    Parameters
    ----------
    experiment_id:
        Experiment primary key.

    Returns
    -------
    list[dict[str, Any]]
        One dict per variant (JSON-serialisable).

    Notes
    -----
    If WT controls are missing (or yields are zero) for a generation, activity fields are left as None.
    """
    controls = ControlData.query.filter_by(experiment_id=experiment_id).all()

    wt_by_gen: dict[int, dict[str, float]] = {}
    for c in controls:
        if _is_wt_control(c.control_type):
            # Prefer last-seen WT row if there are duplicates; alternatively, you could average here.
            wt_by_gen[int(c.generation)] = {
                "wt_dna": float(c.dna_yield) if c.dna_yield is not None else 0.0,
                "wt_protein": float(c.protein_yield) if c.protein_yield is not None else 0.0,
            }

    variants = (
        Variant.query.filter_by(experiment_id=experiment_id)
        .order_by(Variant.generation.asc(), Variant.variant_id.asc())
        .all()
    )

    rows: List[Dict[str, Any]] = []

    for v in variants:
        gen = int(v.generation)

        wt = wt_by_gen.get(gen)
        dna_norm: Optional[float] = None
        protein_norm: Optional[float] = None
        activity_score_log2: Optional[float] = None

        if wt and wt["wt_dna"] and wt["wt_protein"]:
            if wt["wt_dna"] != 0 and wt["wt_protein"] != 0 and v.dna_yield is not None and v.protein_yield is not None:
                dna_norm = float(v.dna_yield) / wt["wt_dna"]
                protein_norm = float(v.protein_yield) / wt["wt_protein"]

                if protein_norm != 0:
                    raw = dna_norm / protein_norm
                    activity_score_log2 = math.log2(raw) if raw > 0 else None
        else:
            logger.debug("Missing WT baselines for generation=%s (experiment_id=%s)", gen, experiment_id)

        rows.append(
            {
                "variant_id": v.variant_id,
                "generation": gen,
                "plasmid_variant_index": v.plasmid_variant_index,
                "dna_yield": v.dna_yield,
                "protein_yield": v.protein_yield,
                "dna_norm": dna_norm,
                "protein_norm": protein_norm,
                "activity_score_log2": activity_score_log2,
                "mutation_count": v.mutation_count,
                "protein_sequence": v.protein_sequence,
            }
        )

    return rows


def fetch_mutations_table(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-mutation table joined to variant generation.

    Parameters
    ----------
    experiment_id:
        Experiment primary key.

    Returns
    -------
    list[dict[str, Any]]
        One dict per mutation, including generation for plotting.
    """
    q = (
        db.session.query(
            Mutations.variant_id,
            Variant.generation,
            Mutations.position,
            Mutations.wt_residue,
            Mutations.mutant_residue,
            Mutations.mutation_type,
            Mutations.codon_change,
        )
        .join(Variant, Variant.variant_id == Mutations.variant_id)
        .filter(Variant.experiment_id == experiment_id)
        .order_by(Variant.variant_id.asc(), Mutations.position.asc())
    )

    rows: List[Dict[str, Any]] = []
    for r in q.all():
        rows.append(
            {
                "variant_id": r.variant_id,
                "generation": int(r.generation),
                "position": r.position,
                "wt_residue": r.wt_residue,
                "mutant_residue": r.mutant_residue,
                "mutation_type": r.mutation_type,
                "codon_change": r.codon_change,
            }
        )

    return rows
"""
One-command demo runner for the visualisation outputs.

Examples
--------
Dummy data:
    python -m visualisation.demo_run

DB-export JSON:
    python -m visualisation.demo_run --source db_export --variants_json path/to/variants.json --mutations_json path/to/mutations.json
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from visualisation.activity_landscape_3d import plot_activity_landscape_3d
from visualisation.activityscore_plot import plot_activity_violin
from visualisation.data_sources import get_mutations, get_variants
from visualisation.mutation_fingerprint import plot_mutation_fingerprint
from visualisation.reporting import save_plotly_figure, save_table_csv, save_top10_table_png
from visualisation.top10_table_only import compute_top10
from visualisation.trends import plot_activity_median_trend

logger = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    parser = argparse.ArgumentParser(description="Generate visualisation outputs for the DE monitoring portal.")
    parser.add_argument("--source", default="dummy", choices=["dummy", "db_export"])
    parser.add_argument("--variants_json", default=None, help="Path to variants JSON (required if --source db_export).")
    parser.add_argument("--mutations_json", default=None, help="Path to mutations JSON (required for bonus plots).")
    args = parser.parse_args(argv)

    logger.info("Running visualisation demo (source=%s)...", args.source)

    if args.source == "dummy":
        df = get_variants(source="dummy")
        muts_df = None
    else:
        df = get_variants(source="db_export", variants_json_path=args.variants_json)
        muts_df = get_mutations(source="db_export", mutations_json_path=args.mutations_json)

    score_col = "activity_score_log2"

    fig = plot_activity_violin(df, score_col=score_col)
    html_path, png_path = save_plotly_figure(fig, out_prefix="activity_violin")

    trend_fig = plot_activity_median_trend(df, score_col=score_col, show_iqr=True)
    trend_html, trend_png = save_plotly_figure(trend_fig, out_prefix="activity_median_trend")

    top10 = compute_top10(df)
    csv_path = save_table_csv(top10, out_name="top10_variants")
    png_table_path = save_top10_table_png(top10, out_name="top10_variants_table")

    logger.info("Outputs saved:")
    logger.info("- %s", html_path)
    logger.info("- %s", png_path)
    logger.info("- %s", trend_html)
    logger.info("- %s", trend_png)
    logger.info("- %s", csv_path)
    logger.info("- %s", png_table_path)

    # Bonus visuals
    if muts_df is not None and not muts_df.empty:
        best_variant_id = top10.loc[0, "variant_id"]

        fp_fig = plot_mutation_fingerprint(
            muts_df,
            variant_id=best_variant_id,
            title=f"Mutation fingerprint (variant {best_variant_id})",
        )
        fp_html, fp_png = save_plotly_figure(fp_fig, out_prefix="mutation_fingerprint")
        logger.info("- %s", fp_html)
        logger.info("- %s", fp_png)

        land_fig = plot_activity_landscape_3d(
            df,
            muts_df,
            score_col=score_col,
            title="3D Activity Landscape (PCA on mutation positions)",
        )
        land_html, land_png = save_plotly_figure(land_fig, out_prefix="activity_landscape_3d")
        logger.info("- %s", land_html)
        logger.info("- %s", land_png)


if __name__ == "__main__":
    main()
"""
Reporting/export helpers for the visualisation package.

Supports:
- Plotly HTML export (embed in web portal or download)
- Optional PNG export via kaleido (if installed)
- CSV export for tabular outputs
- Table-as-PNG export for the Top 10 table via matplotlib (publication/report friendly)

"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def get_output_dir(output_dir: str | Path = "outputs") -> Path:
    """
    Get (and create) the output directory.

    Parameters
    ----------
    output_dir:
        Directory path.

    Returns
    -------
    pathlib.Path
        Created directory path.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_plotly_figure(fig, out_prefix: str, output_dir: str | Path = "outputs") -> Tuple[str, Optional[str]]:
    """
    Save a Plotly figure as HTML and (optionally) PNG.

    PNG export requires 'kaleido'. If unavailable, PNG path is returned as None.

    Parameters
    ----------
    fig:
        Plotly figure.
    out_prefix:
        Output filename prefix (without extension).
    output_dir:
        Output directory.

    Returns
    -------
    (html_path, png_path_or_none)
    """
    out = get_output_dir(output_dir)

    html_path = out / f"{out_prefix}.html"
    fig.write_html(str(html_path))

    png_path = out / f"{out_prefix}.png"
    try:
        fig.write_image(str(png_path), scale=2)  # requires kaleido
        return str(html_path), str(png_path)
    except Exception as e:
        logger.info("PNG export skipped (install kaleido to enable). Details: %s", e)
        return str(html_path), None


def save_table_csv(df: pd.DataFrame, out_name: str, output_dir: str | Path = "outputs") -> str:
    """
    Save a dataframe to CSV.

    Parameters
    ----------
    df:
        Table to save.
    out_name:
        Filename (without extension).
    output_dir:
        Output directory.

    Returns
    -------
    str
        CSV path.
    """
    out = get_output_dir(output_dir)
    csv_path = out / f"{out_name}.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)


def save_top10_table_png(
    top10: pd.DataFrame,
    out_name: str = "top10_variants_table",
    output_dir: str | Path = "outputs",
) -> str:
    """
    Save the top 10 table as a PNG using matplotlib's table rendering.

    Parameters
    ----------
    top10:
        Top 10 dataframe.
    out_name:
        Filename (without extension).
    output_dir:
        Output directory.

    Returns
    -------
    str
        PNG path.
    """
    import matplotlib.pyplot as plt  # local import keeps base deps lighter

    out = get_output_dir(output_dir)

    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")

    display_df = top10.copy()

    # format numeric columns nicely if present
    if "activity_score_log2" in display_df.columns:
        display_df["activity_score_log2"] = pd.to_numeric(display_df["activity_score_log2"], errors="coerce").map(
            lambda x: f"{x:.3f}" if pd.notna(x) else ""
        )
    if "protein_yield" in display_df.columns:
        display_df["protein_yield"] = pd.to_numeric(display_df["protein_yield"], errors="coerce").map(
            lambda x: f"{x:.1f}" if pd.notna(x) else ""
        )
    if "dna_yield" in display_df.columns:
        display_df["dna_yield"] = pd.to_numeric(display_df["dna_yield"], errors="coerce").map(
            lambda x: f"{x:.1f}" if pd.notna(x) else ""
        )

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    ax.set_title("Top 10 variants by activity score (log2)", pad=12)

    png_path = out / f"{out_name}.png"
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)
    plt.close(fig)

    return str(png_path)