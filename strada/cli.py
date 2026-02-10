"""
STRADA Toolbox — Command-line interface.

Usage examples::

    # Preprocess an Excel workbook → CSV
    strada preprocess --excel-file data.xlsx --output-dir ./out --start-year 2016 --end-year 2024

    # Run all generic data-quality checks
    strada verify --olyckor Olyckor.csv --personer Personer.csv

    # Run all checks including cycling-specific ones
    strada verify --olyckor Olyckor.csv --personer Personer.csv --cycling

    # Run only specific checks
    strada verify --olyckor Olyckor.csv --personer Personer.csv --checks G1 G4 G5

    # Classify micromobility types (cycling analysis)
    strada classify --personer Personer.csv --output-dir ./out

    # Launch the web dashboard
    strada web
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="strada",
    help="STRADA Data Quality Assessment Toolkit",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


# ─────────────────────────────────────────────────────────────────────────────
#  preprocess
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def preprocess(
    excel_file: Path = typer.Option(
        ..., "--excel-file", "-e",
        help="Path to the STRADA .xlsx workbook.",
        exists=True,
        dir_okay=False,
    ),
    output_dir: Path = typer.Option(
        ..., "--output-dir", "-o",
        help="Directory to write CSV files to.",
    ),
    start_year: Optional[int] = typer.Option(
        None, "--start-year",
        help="If set (with --end-year), create an additional year-filtered CSV pair.",
    ),
    end_year: Optional[int] = typer.Option(
        None, "--end-year",
        help="If set (with --start-year), create an additional year-filtered CSV pair.",
    ),
    olyckor_sheet: str = typer.Option("Olyckor", "--olyckor-sheet"),
    personer_sheet: str = typer.Option("Personer", "--personer-sheet"),
):
    """Convert a STRADA Excel workbook to CSV and optionally filter by year."""
    from strada.core.preprocess import preprocess_pipeline

    console.print(f"\n[bold]Reading:[/bold] {excel_file}")
    result = preprocess_pipeline(
        excel_file,
        output_dir,
        start_year=start_year,
        end_year=end_year,
        olyckor_sheet=olyckor_sheet,
        personer_sheet=personer_sheet,
    )

    table = Table(title="Preprocessing Results")
    table.add_column("File", style="cyan")
    table.add_column("Rows", justify="right", style="green")

    table.add_row(str(result["olyckor_csv"]), f'{result["olyckor_count"]:,}')
    table.add_row(str(result["personer_csv"]), f'{result["personer_count"]:,}')

    if "olyckor_filtered_csv" in result:
        table.add_row(
            str(result["olyckor_filtered_csv"]),
            f'{result["olyckor_filtered_count"]:,}',
        )
        table.add_row(
            str(result["personer_filtered_csv"]),
            f'{result["personer_filtered_count"]:,}',
        )

    console.print(table)
    console.print("\n[green]✓[/green] Preprocessing complete.\n")


# ─────────────────────────────────────────────────────────────────────────────
#  verify
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def verify(
    olyckor: Path = typer.Option(
        ..., "--olyckor",
        help="Path to the Olyckor (crashes) CSV file.",
        exists=True,
        dir_okay=False,
    ),
    personer: Path = typer.Option(
        ..., "--personer",
        help="Path to the Personer (persons) CSV file.",
        exists=True,
        dir_okay=False,
    ),
    output_dir: Path = typer.Option(
        ".", "--output-dir", "-o",
        help="Directory for the output report files.",
    ),
    cycling: bool = typer.Option(
        False, "--cycling",
        help="Include cycling-specific checks (C1–C3).",
    ),
    checks: Optional[List[str]] = typer.Option(
        None, "--checks",
        help="Run only specific checks by ID (e.g. G1 G4 C2). Omit to run all.",
    ),
    report_format: str = typer.Option(
        "both", "--format",
        help="Report format: 'txt', 'csv', or 'both'.",
    ),
):
    """Run data-quality verification checks on STRADA CSV files."""
    from strada.io.readers import load_csv
    from strada.core.verify import run_checks
    from strada.io.reporters import write_text_report, write_csv_report

    console.print(f"\n[bold]Loading data…[/bold]")
    df_olyckor = load_csv(olyckor)
    df_personer = load_csv(personer)
    console.print(f"  Crashes: {len(df_olyckor):,}   Persons: {len(df_personer):,}")

    console.print(f"\n[bold]Running checks…[/bold]")
    results = run_checks(
        df_olyckor,
        df_personer,
        include_cycling=cycling,
        checks=checks,
    )

    # ── Summary table ──────────────────────────────────────────────────────
    summary = Table(title="Verification Summary")
    summary.add_column("Check", style="cyan")
    summary.add_column("Status", justify="center")
    summary.add_column("Issues", justify="right")
    summary.add_column("Description")

    for r in results:
        icon = {"pass": "[green]✓[/green]", "warning": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}.get(r.status, "?")
        summary.add_row(r.check_id, icon, str(r.issue_count), r.check_name)
        for sub in r.sub_results:
            sub_icon = {"pass": "[green]✓[/green]", "warning": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}.get(sub.status, "?")
            summary.add_row(f"  {sub.check_id}", sub_icon, str(sub.issue_count), sub.check_name)

    console.print(summary)

    # ── Write reports ──────────────────────────────────────────────────────
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if report_format in ("txt", "both"):
        txt_path = write_text_report(
            results,
            output_dir / "strada_quality_report.txt",
            olyckor_count=len(df_olyckor),
            personer_count=len(df_personer),
        )
        console.print(f"\n  Text report: [cyan]{txt_path}[/cyan]")

    if report_format in ("csv", "both"):
        csv_path = write_csv_report(results, output_dir / "strada_quality_report.csv")
        console.print(f"  CSV report:  [cyan]{csv_path}[/cyan]")

    total_issues = sum(r.issue_count for r in results)
    if total_issues == 0:
        console.print("\n[green]✓ All checks passed![/green]\n")
    else:
        console.print(f"\n[yellow]⚠ {total_issues} total issues found. See reports for details.[/yellow]\n")


# ─────────────────────────────────────────────────────────────────────────────
#  classify  (cycling-specific)
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def classify(
    personer: Path = typer.Option(
        ..., "--personer",
        help="Path to the Personer (persons) CSV file.",
        exists=True,
        dir_okay=False,
    ),
    output_dir: Path = typer.Option(
        ".", "--output-dir", "-o",
        help="Directory for the output file.",
    ),
    output_name: str = typer.Option(
        "Personer-analysis-ready.csv", "--output-name",
        help="File name for the output CSV.",
    ),
):
    """Classify micromobility types and add conflict-partner column (cycling analysis)."""
    from strada.io.readers import load_csv
    from strada.io.reporters import write_text_report
    from strada.core.classify import run_classification_pipeline
    from strada.io.readers import save_csv

    console.print(f"\n[bold]Loading data…[/bold]")
    df = load_csv(personer)
    console.print(f"  Persons: {len(df):,}")

    console.print(f"\n[bold]Classifying micromobility types…[/bold]")
    df, verif_results, multi_matches, stats = run_classification_pipeline(df)

    # Classification summary
    cykel = df[df["Micromobility_type"] != "N/A"]
    if len(cykel) > 0:
        table = Table(title="Micromobility Classification")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("%", justify="right")

        counts = cykel["Micromobility_type"].value_counts()
        for cat, cnt in counts.items():
            pct = cnt / len(cykel) * 100
            table.add_row(str(cat), f"{cnt:,}", f"{pct:.1f}%")

        console.print(table)

    if len(multi_matches) > 0:
        console.print(f"\n[yellow]⚠ {len(multi_matches)} entries matched multiple categories[/yellow]")

    # Verification summaries
    for v in verif_results:
        icon = {"pass": "[green]✓[/green]", "warning": "[yellow]⚠[/yellow]"}.get(v.status, "?")
        console.print(f"  {icon} {v.check_id}: {v.summary}")

    # Save
    output_dir = Path(output_dir)
    out_path = save_csv(df, output_dir / output_name)
    console.print(f"\n  Saved: [cyan]{out_path}[/cyan]")

    # Also save the text report
    report_path = write_text_report(
        verif_results,
        output_dir / "micromobility_classification_report.txt",
        title="Micromobility Classification Report",
        personer_count=len(df),
    )
    console.print(f"  Report: [cyan]{report_path}[/cyan]")
    console.print("\n[green]✓ Classification complete.[/green]\n")


# ─────────────────────────────────────────────────────────────────────────────
#  web
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def web(
    port: int = typer.Option(8501, "--port", "-p", help="Port for the Streamlit server."),
):
    """Launch the STRADA Toolbox web dashboard."""
    import subprocess
    import sys

    app_path = Path(__file__).parent / "app.py"
    console.print(f"\n[bold]Launching web dashboard on port {port}…[/bold]\n")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
    )


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
