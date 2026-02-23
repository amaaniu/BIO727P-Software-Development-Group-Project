"""
visualisation/io_pipeline.py

Single file containing:
1) Data source loaders for exported JSON (real data only)
2) Backend database export helpers (Variant summary + Mutations table)
3) A demo runner (CLI entrypoint) that loads exported JSON and calls plotting modules

"""

from __future__ import annotations

import argparse
import logging
import math
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# 1) DATA SOURCES (JSON loaders)
# =============================================================================

def _ensure_exists(path: str | Path, label: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    return p


def load_variants_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the variants summary exported from the backend.

    Parameters
    ----------
    path:
        JSON file produced by fetch_variant_summary(...), saved to disk.

    Returns
    -------
    pandas.DataFrame
        Variants table with numeric coercion applied.
    """
    path = _ensure_exists(path, "Variants JSON")
    df = pd.read_json(path)

    for col in ("generation", "activity_score_log2", "mutation_count", "dna_yield", "protein_yield"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_mutations_from_json(path: str | Path) -> pd.DataFrame:
    """
    Load the mutations table exported from the backend.

    Parameters
    ----------
    path:
        JSON file produced by fetch_mutations_table(...), saved to disk.

    Returns
    -------
    pandas.DataFrame
        Mutations table with numeric coercion applied.
    """
    path = _ensure_exists(path, "Mutations JSON")
    df = pd.read_json(path)

    for col in ("generation", "position"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_variants(source: str | Path | int) -> pd.DataFrame:
    """
    Public entry point to get variants dataframe.

    Parameters
    ----------
    source:
        Either a JSON path (str/Path) or an experiment_id (int).
    """
    if isinstance(source, int):
        rows = fetch_variant_summary(source)
        return pd.DataFrame(rows)
    return load_variants_from_json(source)


def get_mutations(source: str | Path | int) -> pd.DataFrame:
    """
    Public entry point to get mutations dataframe.

    Parameters
    ----------
    source:
        Either a JSON path (str/Path) or an experiment_id (int).
    """
    if isinstance(source, int):
        rows = fetch_mutations_table(source)
        return pd.DataFrame(rows)
    return load_mutations_from_json(source)


# =============================================================================
# 2) BACKEND EXPORT HELPERS (DB -> list[dict])
# =============================================================================


_WT_LABELS = {"wt", "wildtype", "wild_type", "wild-type", "control_wt"}


def _is_wt_control(control_type: Optional[str]) -> bool:
    """Return True if control_type appears to indicate a WT control row."""
    if not control_type:
        return False
    return control_type.strip().lower() in _WT_LABELS


def fetch_variant_summary(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-variant summary table for an experiment from the DB.

    Output includes WT-normalised yields and activity_score_log2:
        dna_norm = dna_yield / wt_dna_yield
        protein_norm = protein_yield / wt_protein_yield
        activity_score_log2 = log2(dna_norm / protein_norm)

    Returns
    -------
    list[dict[str, Any]]
        JSON-serialisable rows.

    Raises
    ------
    ImportError
        If called outside backend environment (models/db not available).
    """
    try:
        from app.models import ControlData, Variant  # type: ignore
    except Exception:
        try:
            from models import ControlData, Variant  # type: ignore
        except Exception as e:
            raise ImportError(
                "fetch_variant_summary() must be run in the backend environment where models are available."
            ) from e

    controls = ControlData.query.filter_by(experiment_id=experiment_id).all()

    wt_by_gen: dict[int, dict[str, float]] = {}
    for c in controls:
        if _is_wt_control(getattr(c, "control_type", None)):
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
            if (
                wt["wt_dna"] != 0
                and wt["wt_protein"] != 0
                and v.dna_yield is not None
                and v.protein_yield is not None
            ):
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
                "plasmid_variant_index": getattr(v, "plasmid_variant_index", None),
                "dna_yield": v.dna_yield,
                "protein_yield": v.protein_yield,
                "dna_norm": dna_norm,
                "protein_norm": protein_norm,
                "activity_score_log2": activity_score_log2,
                "mutation_count": getattr(v, "mutation_count", None),
                "protein_sequence": getattr(v, "protein_sequence", None),
            }
        )

    return rows


def fetch_mutations_table(experiment_id: int) -> List[Dict[str, Any]]:
    """
    Export a per-mutation table joined to variant generation from the DB.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serialisable rows.

    Raises
    ------
    ImportError
        If called outside backend environment (models/db not available).
    """
    try:
        from app.models import Mutations, Variant, db  # type: ignore
    except Exception:
        try:
            from models import Mutations, Variant, db  # type: ignore
        except Exception as e:
            raise ImportError(
                "fetch_mutations_table() must be run in the backend environment where models are available."
            ) from e

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


# =============================================================================
# 3) DEMO RUNNER 
# =============================================================================

def _require_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{name} missing required columns: {sorted(missing)}")


def _save_outputs_hint(outputs: List[Path]) -> None:
    logger.info("Saved outputs:")
    for p in outputs:
        logger.info("- %s", p)


def main(argv: Optional[list[str]] = None) -> None:
    """
    CLI entrypoint.

    Loads exported JSON and calls plotting modules to generate outputs.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    parser = argparse.ArgumentParser(description="Run DE visualisation pipeline using exported JSON.")
    parser.add_argument("--variants_json", required=True, help="Path to variants JSON export.")
    parser.add_argument("--mutations_json", required=False, help="Path to mutations JSON export (optional).")
    parser.add_argument("--output_dir", default="outputs", help="Output directory (default: outputs).")
    parser.add_argument(
        "--open_html",
        action="store_true",
        help="Open exported HTML files in your default browser.",
    )
    args = parser.parse_args(argv)

    variants_df = get_variants(args.variants_json)
    _require_columns(variants_df, {"variant_id", "generation", "activity_score_log2"}, "Variants dataframe")

    muts_df: Optional[pd.DataFrame] = None
    if args.mutations_json:
        muts_df = get_mutations(args.mutations_json)

    
    from visualisation.activityscore_plot import plot_activity_violin  # type: ignore
    from visualisation.trends import plot_activity_median_trend  # type: ignore
    from visualisation.top10_table_only import compute_top10  # type: ignore
    from visualisation.reporting import save_plotly_figure, save_table_csv, save_top10_table_png  # type: ignore

    output_dir = Path(args.output_dir)

    outputs: List[Path] = []

    score_col = "activity_score_log2"

    fig1 = plot_activity_violin(variants_df, score_col=score_col)
    html1, png1 = save_plotly_figure(fig1, out_prefix="activity_violin", output_dir=output_dir)
    outputs.append(Path(html1))
    if png1:
        outputs.append(Path(png1))

    fig2 = plot_activity_median_trend(variants_df, score_col=score_col, show_iqr=True)
    html2, png2 = save_plotly_figure(fig2, out_prefix="activity_median_trend", output_dir=output_dir)
    outputs.append(Path(html2))
    if png2:
        outputs.append(Path(png2))

    top10 = compute_top10(variants_df)
    csv_path = save_table_csv(top10, out_name="top10_variants", output_dir=output_dir)
    outputs.append(Path(csv_path))

    table_png = save_top10_table_png(top10, out_name="top10_variants_table", output_dir=output_dir)
    outputs.append(Path(table_png))

    # Bonus plots if mutations provided
    if muts_df is not None and not muts_df.empty:
        from visualisation.mutation_fingerprint import plot_mutation_fingerprint  # type: ignore
        from visualisation.activity_landscape_3d import plot_activity_landscape_3d  # type: ignore

        best_variant_id = top10.loc[0, "variant_id"]

        fp_fig = plot_mutation_fingerprint(
            muts_df,
            variant_id=best_variant_id,
            title=f"Mutation fingerprint (variant {best_variant_id})",
        )
        fp_html, fp_png = save_plotly_figure(fp_fig, out_prefix="mutation_fingerprint", output_dir=output_dir)
        outputs.append(Path(fp_html))
        if fp_png:
            outputs.append(Path(fp_png))

        land_fig = plot_activity_landscape_3d(
            variants_df,
            muts_df,
            score_col=score_col,
            title="3D Activity Landscape (PCA on mutation positions)",
        )
        land_html, land_png = save_plotly_figure(land_fig, out_prefix="activity_landscape_3d", output_dir=output_dir)
        outputs.append(Path(land_html))
        if land_png:
            outputs.append(Path(land_png))

    _save_outputs_hint(outputs)

    if args.open_html:
        for p in outputs:
            if p.suffix.lower() == ".html":
                webbrowser.open(p.resolve().as_uri())


if __name__ == "__main__":
    main()
