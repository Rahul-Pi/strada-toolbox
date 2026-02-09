"""
Readers for STRADA data files (Excel and CSV).

All encoding and dtype handling is centralised here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from strada.config.constants import CSV_ENCODING, COL_CRASH_ID


def load_csv(
    path: str | Path,
    *,
    encoding: str = CSV_ENCODING,
) -> pd.DataFrame:
    """Read a STRADA CSV file with the correct encoding.

    Parameters
    ----------
    path : str or Path
        Absolute or relative path to the CSV file.
    encoding : str, optional
        Character encoding.  Defaults to ``utf-8-sig`` (the encoding used
        by STRADA exports on Windows).

    Returns
    -------
    pd.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    return pd.read_csv(path, encoding=encoding, low_memory=False)


def load_excel_sheet(
    path: str | Path,
    sheet_name: str,
) -> pd.DataFrame:
    """Read a single sheet from a STRADA Excel workbook.

    Line-break characters (``\\n``, ``\\r``) inside cells are replaced by
    spaces so that the resulting DataFrame is safe to write to CSV.

    Parameters
    ----------
    path : str or Path
        Path to the ``.xlsx`` file.
    sheet_name : str
        Name of the sheet to read (e.g. ``"Olyckor"`` or ``"Personer"``).

    Returns
    -------
    pd.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    df = pd.read_excel(path, sheet_name=sheet_name)

    # Replace in-cell line breaks with spaces
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("\n", " ", regex=False)
                .str.replace("\r", " ", regex=False)
            )

    return df


def save_csv(
    df: pd.DataFrame,
    path: str | Path,
    *,
    encoding: str = CSV_ENCODING,
) -> Path:
    """Write a DataFrame to CSV with STRADA-standard encoding.

    Parameters
    ----------
    df : pd.DataFrame
    path : str or Path
    encoding : str, optional

    Returns
    -------
    Path — the written file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding=encoding)
    return path


def load_strada_pair(
    data_dir: str | Path,
    olyckor_name: str = "Olyckor.csv",
    personer_name: str = "Personer.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience loader for an Olyckor / Personer CSV pair.

    Parameters
    ----------
    data_dir : str or Path
        Directory containing both CSV files.
    olyckor_name : str
        File name of the crashes CSV.
    personer_name : str
        File name of the persons CSV.

    Returns
    -------
    (df_olyckor, df_personer) : tuple[pd.DataFrame, pd.DataFrame]
    """
    data_dir = Path(data_dir)
    df_olyckor = load_csv(data_dir / olyckor_name)
    df_personer = load_csv(data_dir / personer_name)
    return df_olyckor, df_personer
