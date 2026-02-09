"""
Preprocessing helpers for raw STRADA data.

This module handles:
  1. Converting Excel workbooks → CSV files.
  2. Filtering datasets by year range.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from strada.config.constants import COL_YEAR, CSV_ENCODING
from strada.io.readers import load_csv, load_excel_sheet, save_csv


# ═══════════════════════════════════════════════════════════════════════════════
# Excel → CSV conversion
# ═══════════════════════════════════════════════════════════════════════════════

def convert_excel_to_csv(
    excel_path: str | Path,
    output_dir: str | Path,
    *,
    olyckor_sheet: str = "Olyckor",
    personer_sheet: str = "Personer",
    olyckor_name: str = "Olyckor.csv",
    personer_name: str = "Personer.csv",
) -> tuple[Path, Path]:
    """Convert STRADA Excel workbook sheets to CSV files.

    In-cell line breaks are replaced by spaces during conversion so that the
    resulting CSVs are safe for downstream processing.

    Parameters
    ----------
    excel_path : str or Path
        Path to the ``.xlsx`` file.
    output_dir : str or Path
        Directory where the CSV files will be written.
    olyckor_sheet / personer_sheet : str
        Sheet names inside the workbook.
    olyckor_name / personer_name : str
        File names for the output CSVs.

    Returns
    -------
    (olyckor_csv, personer_csv) : tuple[Path, Path]
    """
    excel_path = Path(excel_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_olyckor = load_excel_sheet(excel_path, olyckor_sheet)
    olyckor_csv = save_csv(df_olyckor, output_dir / olyckor_name)

    df_personer = load_excel_sheet(excel_path, personer_sheet)
    personer_csv = save_csv(df_personer, output_dir / personer_name)

    return olyckor_csv, personer_csv


# ═══════════════════════════════════════════════════════════════════════════════
# Year-range filtering
# ═══════════════════════════════════════════════════════════════════════════════

def filter_by_year(
    df: pd.DataFrame,
    start_year: int,
    end_year: int,
    *,
    year_col: str = COL_YEAR,
) -> pd.DataFrame:
    """Return rows whose year is within ``[start_year, end_year]``.

    Parameters
    ----------
    df : pd.DataFrame
    start_year, end_year : int
        Inclusive bounds.
    year_col : str
        Name of the year column.

    Returns
    -------
    pd.DataFrame — filtered copy.
    """
    mask = (df[year_col] >= start_year) & (df[year_col] <= end_year)
    return df.loc[mask].copy()


def preprocess_pipeline(
    excel_path: str | Path,
    output_dir: str | Path,
    *,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    olyckor_sheet: str = "Olyckor",
    personer_sheet: str = "Personer",
) -> dict[str, Path | int]:
    """Full preprocessing pipeline: Excel → CSV → optional year filter.

    Parameters
    ----------
    excel_path : str or Path
    output_dir : str or Path
    start_year, end_year : int, optional
        If both are provided the data is additionally filtered and saved
        with a ``-{start_year}-{end_year}`` suffix.
    olyckor_sheet, personer_sheet : str

    Returns
    -------
    dict with keys:
        ``olyckor_csv``, ``personer_csv`` — full dataset paths
        ``olyckor_count``, ``personer_count`` — row counts
        and optionally ``olyckor_filtered_csv``, ``personer_filtered_csv``,
        ``olyckor_filtered_count``, ``personer_filtered_count``.
    """
    output_dir = Path(output_dir)

    # Step 1 — convert
    olyckor_csv, personer_csv = convert_excel_to_csv(
        excel_path,
        output_dir,
        olyckor_sheet=olyckor_sheet,
        personer_sheet=personer_sheet,
    )

    df_olyckor = load_csv(olyckor_csv)
    df_personer = load_csv(personer_csv)

    result: dict[str, Path | int] = {
        "olyckor_csv": olyckor_csv,
        "personer_csv": personer_csv,
        "olyckor_count": len(df_olyckor),
        "personer_count": len(df_personer),
    }

    # Step 2 — optional year filter
    if start_year is not None and end_year is not None:
        df_olyckor_f = filter_by_year(df_olyckor, start_year, end_year)
        df_personer_f = filter_by_year(df_personer, start_year, end_year)

        suffix = f"-{start_year}-{end_year}"
        olyckor_f_csv = save_csv(df_olyckor_f, output_dir / f"Olyckor{suffix}.csv")
        personer_f_csv = save_csv(df_personer_f, output_dir / f"Personer{suffix}.csv")

        result.update({
            "olyckor_filtered_csv": olyckor_f_csv,
            "personer_filtered_csv": personer_f_csv,
            "olyckor_filtered_count": len(df_olyckor_f),
            "personer_filtered_count": len(df_personer_f),
        })

    return result
