"""
Report writers for STRADA verification results.

Supports two output formats:
  - **Plain text** — human-readable summary with pass/fail per check.
  - **CSV**        — one row per flagged issue, suitable for Excel review.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# Data structure returned by every verification check
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VerificationResult:
    """Container for the output of a single verification check.

    Attributes
    ----------
    check_id : str
        Short identifier, e.g. ``"G1"`` or ``"C2"``.
    check_name : str
        Human-readable title.
    status : str
        ``"pass"``, ``"warning"`` or ``"fail"``.
    summary : str
        One-line summary message shown in the text report.
    issue_count : int
        Number of issues found (0 = pass).
    details : pd.DataFrame | None
        Detailed table of flagged records.  Column names are check-specific.
    sub_results : list[VerificationResult]
        Optional nested results for checks with sub-parts (e.g. G3.1–G3.4).
    """

    check_id: str
    check_name: str
    status: str  # "pass" | "warning" | "fail"
    summary: str
    issue_count: int = 0
    details: Optional[pd.DataFrame] = None
    sub_results: list["VerificationResult"] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Plain-text report
# ═══════════════════════════════════════════════════════════════════════════════

def write_text_report(
    results: list[VerificationResult],
    path: str | Path,
    *,
    title: str = "STRADA Data Quality Assessment Report",
    olyckor_count: int | None = None,
    personer_count: int | None = None,
) -> Path:
    """Write a human-readable plain-text report.

    Parameters
    ----------
    results : list[VerificationResult]
        Ordered list of verification results to include.
    path : str or Path
        Output file path.
    title : str
        Report title.
    olyckor_count, personer_count : int, optional
        Dataset sizes to include in the header.

    Returns
    -------
    Path — the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as fh:
        # Header
        fh.write("=" * 80 + "\n")
        fh.write(f"{title}\n")
        fh.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        fh.write("=" * 80 + "\n\n")

        if olyckor_count is not None or personer_count is not None:
            fh.write("Dataset summary:\n")
            if olyckor_count is not None:
                fh.write(f"  Crashes (Olyckor):  {olyckor_count:,}\n")
            if personer_count is not None:
                fh.write(f"  Persons (Personer): {personer_count:,}\n")
            fh.write("\n")

        # Overview table
        fh.write("-" * 80 + "\n")
        fh.write(f"{'Check':<8} {'Status':<10} {'Issues':>8}  {'Description'}\n")
        fh.write("-" * 80 + "\n")
        for r in results:
            icon = {"pass": "✓", "warning": "⚠", "fail": "✗"}.get(r.status, "?")
            fh.write(f"{r.check_id:<8} {icon} {r.status:<8} {r.issue_count:>8}  {r.check_name}\n")
            for sub in r.sub_results:
                icon_s = {"pass": "✓", "warning": "⚠", "fail": "✗"}.get(sub.status, "?")
                fh.write(f"  {sub.check_id:<6} {icon_s} {sub.status:<8} {sub.issue_count:>8}  {sub.check_name}\n")
        fh.write("-" * 80 + "\n\n")

        # Detailed sections
        for r in results:
            _write_section(fh, r)
            for sub in r.sub_results:
                _write_section(fh, sub, indent=2)

        fh.write("=" * 80 + "\n")
        fh.write("End of Report\n")
        fh.write("=" * 80 + "\n")

    return path


def _write_section(fh, result: VerificationResult, indent: int = 0) -> None:
    """Write one check's detailed section to the text report."""
    prefix = " " * indent
    fh.write(f"\n{'=' * 80}\n")
    fh.write(f"{prefix}{result.check_id}: {result.check_name}\n")
    fh.write(f"{'-' * 80}\n")
    fh.write(f"{prefix}{result.summary}\n")

    if result.details is not None and len(result.details) > 0:
        fh.write(f"\n{prefix}Flagged records ({len(result.details):,}):\n")
        # Write column headers
        cols = result.details.columns.tolist()
        fh.write(f"{prefix}  {', '.join(cols)}\n")
        fh.write(f"{prefix}  {'-' * 60}\n")
        for _, row in result.details.iterrows():
            values = [str(row[c]) for c in cols]
            fh.write(f"{prefix}  {', '.join(values)}\n")
    fh.write("\n")


# ═══════════════════════════════════════════════════════════════════════════════
# CSV report
# ═══════════════════════════════════════════════════════════════════════════════

def write_csv_report(
    results: list[VerificationResult],
    path: str | Path,
) -> Path:
    """Write a CSV report with one row per flagged issue.

    The CSV has these columns:
        ``check_id, check_name, crash_id, issue, details``

    This file can be opened in Excel for review or further annotation.

    Parameters
    ----------
    results : list[VerificationResult]
    path : str or Path

    Returns
    -------
    Path — the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["check_id", "check_name", "crash_id", "issue", "details"]

    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        all_results = []
        for r in results:
            all_results.append(r)
            all_results.extend(r.sub_results)

        for r in all_results:
            if r.details is not None and len(r.details) > 0:
                for _, row in r.details.iterrows():
                    crash_id = row.get("Olycksnummer", row.get("crash_id", ""))
                    # Build a details string from remaining columns
                    detail_parts = []
                    for col in r.details.columns:
                        if col not in ("Olycksnummer", "crash_id"):
                            detail_parts.append(f"{col}={row[col]}")
                    writer.writerow({
                        "check_id": r.check_id,
                        "check_name": r.check_name,
                        "crash_id": crash_id,
                        "issue": r.summary,
                        "details": "; ".join(detail_parts),
                    })
            elif r.issue_count > 0:
                # Check had issues but no details DataFrame
                writer.writerow({
                    "check_id": r.check_id,
                    "check_name": r.check_name,
                    "crash_id": "",
                    "issue": r.summary,
                    "details": "",
                })

    return path
