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