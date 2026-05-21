# STRADA Toolbox

**Data quality assessment toolkit for STRADA (Swedish Traffic Accident Data Acquisition) datasets.**

STRADA is a national information system for road traffic injuries managed by the Swedish Transport Agency (Transportstyrelsen). This toolbox automates data-quality checks for the two core STRADA tables — **Olyckor** (Crashes) and **Personer** (Persons) — and ships as a **web dashboard** for interactive use, with a **command-line interface** available for scripting and automation. No coding experience is required to use the dashboard.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Usage — Web Dashboard](#usage--web-dashboard)
4. [Usage — Command-Line Interface (CLI)](#usage--command-line-interface-cli)
   - [preprocess](#1-preprocess)
   - [verify](#2-verify)
   - [classify](#3-classify-cycling-specific)
   - [web](#4-web-dashboard)
5. [Verification Checks Reference](#verification-checks-reference)
   - [Generic Checks (G1–G6)](#generic-checks-g1g6)
   - [Cycling-Specific Checks (C1–C3)](#cycling-specific-checks-c1c3)
6. [Quality Scoring](#quality-scoring)
7. [Micromobility Classification](#micromobility-classification)
8. [Report Formats](#report-formats)
9. [Project Structure](#project-structure)
10. [Configuration & Customisation](#configuration--customisation)
11. [Workflow Diagram](#workflow-diagram)
12. [Contributing](#contributing)
13. [License](#license)

---

## Quick Start

```bash
# 1. Install (with dashboard support)
cd STRADA_toolbox
pip install ".[web]"

# 2. Launch the web dashboard — upload CSVs, pick checks, download reports
strada web

# 3. Or, for scripted / automated runs, use the CLI
strada verify \
    --olyckor path/to/Olyckor.csv \
    --personer path/to/Personer.csv \
    --cycling
```

---

## Installation

### Prerequisites

- **Python 3.9+**
- The STRADA data files (`.xlsx` workbook or pre-exported `.csv` files)

### Install from source

```bash
# Clone / download this repository
cd STRADA_toolbox

# Option A: install in editable mode (recommended for development)
pip install -e .

# Option B: install normally
pip install .
```

### Install web dashboard support

The web dashboard uses [Streamlit](https://streamlit.io) which is included as an optional dependency:

```bash
pip install -e ".[web]"
```

### Using a virtual environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -e ".[web]"
```

### Install from requirements file (alternative)

```bash
pip install -r requirements.txt
```

---

## Usage — Web Dashboard

The web dashboard is the recommended way to use the toolbox. It provides every feature through a graphical interface, no terminal required after launch.

![STRADA dashboard — Verify tab](assets/dashboard.png)

### Launching

```bash
strada web
```

This opens your browser at `http://localhost:8501` with four tabs:

### Tab: 🔍 Verify
1. Upload your Olyckor and Personer CSV files
2. Select which checks to run (checkboxes for each G1–G6 and C1–C3)
3. Click **▶ Run selected checks**
4. Browse results interactively in expandable tables
5. Download text or CSV reports

### Tab: 🚲 Classify (Cycling)
1. Upload your Personer CSV
2. Click **▶ Run classification**
3. View the micromobility type distribution
4. Download the classified dataset

### Tab: 📥 Preprocess
1. Upload a STRADA Excel workbook
2. Optionally set a year range filter
3. Click **▶ Convert**
4. Download the resulting CSV files

### Tab: ℹ️ About
Documentation and links.

---

## Usage — Command-Line Interface (CLI)

The CLI exposes the same functionality as the dashboard and is intended for scripting, batch processing, and CI pipelines. For interactive analysis, prefer the [Web Dashboard](#usage--web-dashboard).

Run `strada --help` to see all commands:

```
 Usage: strada [OPTIONS] COMMAND [ARGS]...

 STRADA Data Quality Assessment Toolkit

╭─ Commands ────────────────────────────────────────────────────╮
│ preprocess   Convert a STRADA Excel workbook to CSV           │
│ verify       Run data-quality verification checks             │
│ classify     Classify micromobility types (cycling analysis)  │
│ web          Launch the web dashboard                         │
╰───────────────────────────────────────────────────────────────╯
```

### 1. `preprocess`

Converts a STRADA Excel workbook (`.xlsx`) into two CSV files and optionally filters by year range.

```bash
strada preprocess \
    --excel-file "Olyckor_Personer_2005-2024.xlsx" \
    --output-dir ./data \
    --start-year 2016 \
    --end-year 2024
```

| Option | Description |
|--------|-------------|
| `--excel-file`, `-e` | Path to the `.xlsx` workbook **(required)** |
| `--output-dir`, `-o` | Directory for output CSV files **(required)** |
| `--start-year` | Start of year filter (inclusive) |
| `--end-year` | End of year filter (inclusive) |
| `--olyckor-sheet` | Sheet name for crashes (default: `Olyckor`) |
| `--personer-sheet` | Sheet name for persons (default: `Personer`) |

**What it does:**
- Reads the `Olyckor` and `Personer` sheets from the Excel file
- Replaces in-cell line breaks (`\n`, `\r`) with spaces
- Saves `Olyckor.csv` and `Personer.csv` in the output directory
- If year range is given, also saves `Olyckor-2016-2024.csv` and `Personer-2016-2024.csv`

### 2. `verify`

Runs data-quality verification checks on a pair of CSV files.

```bash
# Run all generic checks
strada verify \
    --olyckor Olyckor.csv \
    --personer Personer.csv

# Include cycling-specific checks
strada verify \
    --olyckor Olyckor.csv \
    --personer Personer.csv \
    --cycling

# Run only specific checks
strada verify \
    --olyckor Olyckor.csv \
    --personer Personer.csv \
    --checks G1 G4 G5

# Change output directory and format
strada verify \
    --olyckor Olyckor.csv \
    --personer Personer.csv \
    --output-dir ./reports \
    --format csv
```

| Option | Description |
|--------|-------------|
| `--olyckor` | Path to crashes CSV **(required)** |
| `--personer` | Path to persons CSV **(required)** |
| `--output-dir`, `-o` | Directory for reports (default: `.`) |
| `--cycling` | Include cycling-specific checks C1–C3 |
| `--checks` | Space-separated check IDs to run (e.g. `G1 G4 C2`) |
| `--format` | Report format: `txt`, `csv`, or `both` (default: `both`) |

**Output files:**
- `strada_quality_report.txt` — Human-readable text report
- `strada_quality_report.csv` — Machine-readable CSV (one row per issue)

### 3. `classify` (Cycling-specific)

Classifies Cykel entries into micromobility types and adds a Micromobility_type column.

```bash
strada classify \
    --personer Personer-verified.csv \
    --output-dir ./data \
    --output-name Personer-analysis-ready.csv
```

| Option | Description |
|--------|-------------|
| `--personer` | Path to persons CSV **(required)** |
| `--output-dir`, `-o` | Directory for output (default: `.`) |
| `--output-name` | Output file name (default: `Personer-analysis-ready.csv`) |

**What it adds:**
- `Micromobility_type` column: `Conventional bicycle`, `E-bike`, `E-scooter`, `rullstol/permobil`, `other_micromobility`, or `N/A` (non-Cykel rows)
- `Classification_confidence` column: `high`, `medium`, or `low` depending on how much evidence supported the classification
- `Classification_step` column: Which pipeline step produced the result (e.g. `Step 1 – P keywords`, `Step 3 – Undergrupp fallback`, `Step 4 – default`)

### 4. `web` (Dashboard)

```bash
strada web              # default port 8501
strada web --port 8080  # custom port
```

Opens the browser-based dashboard — see the [Web Dashboard](#usage--web-dashboard) section above for the walkthrough.

---

## Verification Checks Reference

### Generic Checks (G1–G6)

These checks apply to **any** STRADA analysis, regardless of road-user type.

#### G1 — Crash-ID inconsistency

Verifies that every `Olycksnummer` in the Olyckor dataset has at least one matching entry in the Personer dataset, and vice versa.

- **Why it matters:** Missing crash IDs indicate data extraction issues or incomplete joins.
- **What is flagged:** IDs that exist in one dataset but not the other.

#### G2 — Crash-Type (Olyckstyp) inconsistency

Two sub-checks:
- **G2.1:** Checks for missing `Olyckstyp` values in both datasets.
- **G2.2:** For each crash ID present in both datasets, verifies that the `Olyckstyp` value matches.

- **Why it matters:** Inconsistent crash types between datasets may indicate data entry errors or misaligned records.

#### G3 — Road-User Category (Trafikantkategori) inconsistency

Four sub-checks on the Personer dataset:
- **G3.1:** At least one of the three category columns (`Trafikantkategori (P) - Undergrupp`, `Trafikantkategori (S) - Undergrupp`, `Sammanvägd Trafikantkategori - Undergrupp`) must be filled.
- **G3.2:** When both P and S are filled, they should match.
- **G3.3:** When P or S is filled, it should match `Sammanvägd` (allows prefix matching, e.g. `"Lastbil (lätt)"` matches `"Lastbil"`).
- **G3.4:** When both P and S are filled, at least one should match `Sammanvägd`.

- **Why it matters:** The `Sammanvägd` (combined) category is derived from P (Police) and S (Hospital) reports. Discrepancies may indicate classification errors.

#### G4 — Timeline inconsistency

For each crash with multiple person entries, verifies that:
1. The date (`År`, `Månad`, `Dag`) is the same across all entries.
2. The time (`Klockslag grupp (timme)`) is the same across all entries.

Date mismatches are reported first, followed by time mismatches sorted by the magnitude of the time difference.

- **Why it matters:** All persons in the same crash should have the same date and time.

#### G5 — Location inconsistency (Län / Kommun)

For each crash with multiple person entries, verifies that `Län` (county) and `Kommun` (municipality) are consistent.

- **Why it matters:** All persons in the same crash should be at the same location.

#### G6 — Duplicate Person Detection

Identifies potential duplicate person entries across *different* crashes. Groups persons by:
- Age (`Ålder`), Gender (`Kön`)
- Date (`År`, `Månad`, `Dag`), Time (`Klockslag grupp (timme)`)
- Location (`Län`, `Kommun`, `Olycksväg/-gata`)
- **Road-user type** (`Sammanvägd Trafikantkategori - Huvudgrupp`)

If the same combination of all these values appears in multiple different crash IDs, it is flagged as a potential duplicate. Rows with missing age or unknown gender are excluded.

- **Why it matters:** The same traffic incident may have been registered as multiple separate crashes. Including the road-user type ensures that different road users at the same time/place are not incorrectly flagged.

### Cycling-Specific Checks (C1–C3)

These checks are relevant when the dataset has been filtered to cycling / micromobility crashes. Enable them with `--cycling`.

#### C1 — Single Cyclist Crash Validation

For crashes whose STRADA *Olyckstyp* code is `G1 (cykel singel)` — the
single-cyclist crash-type, unrelated to our check ID `G1`:
- There should be exactly **one** person entry.
- That entry should have `Sammanvägd Trafikantkategori - Huvudgrupp == "Cykel"`.
- When multiple persons exist, the count of passengers (identified by `"Passagerare"` in role columns) is reported.

#### C2 — Cyclist Presence in every crash

Verifies that every crash has at least one person with `Huvudgrupp == "Cykel"`. Relevant only when the dataset was extracted as a cycling dataset.

#### C3 — Cyclist (Driver) Missing in Crash

Flags crashes where **all** Cykel entries are passengers (no driver/cyclist). This can indicate a data-entry issue where the cyclist is missing from the record.

---
## Quality Scoring

The toolbox produces a single **0–100 quality score** with a 0–5 star rating (EuroNCAP-style) plus a per-category breakdown. The score is shown in the Verify tab and in the text report.

### How the overall score is calculated

The score starts at 100 and accumulates a deduction from every failing check (a check is "failing" when it found ≥ 1 issue). Each failing check contributes a severity-based base penalty plus a rate-dependent term:

| Severity     | Per-failing-check deduction       |
|--------------|-----------------------------------|
| critical     | `10 + 30 · √rate`                 |
| non-critical | `5  + 30 · √rate`                 |

where `rate = issue_count / denominator`. The denominator is:
- `len(df_olyckor)`  for per-crash checks (G1, G2, G4, G5, C1, C2, C3)
- `len(df_personer)` for per-person checks (G3, G6)

Then:

```
overall = max(0, round(100 − Σ deductions))
```

This means:
- **Each failing critical check costs ~10 points**, so the number of failing criticals dominates the score.
- **Each failing non-critical check costs ~5 points** — meaningful but not catastrophic on its own.
- **The rate term grows sub-linearly (√rate)**, so the score stays comparable across datasets of different sizes — the same issue *rate* yields the same deduction whether the dataset has 1,000 or 100,000 rows.
- Checks that were **not run** contribute nothing (no penalty, no credit).

### Star rating

The numeric score maps to a star rating via fixed thresholds:

| Score range | Stars | Label        |
|-------------|-------|--------------|
| ≥ 90        | ★★★★★ | EXCELLENT    |
| 75–89       | ★★★★☆ | ACCEPTABLE   |
| 60–74       | ★★★☆☆ | NEEDS WORK   |
| 40–59       | ★★☆☆☆ | POOR         |
| < 40        | ☆☆☆☆☆ | FAILING      |

### Score breakdown (per-category aggregation)

Alongside the overall score, the dashboard shows a **Score breakdown** by category. Checks are grouped into four categories:

| Category               | Checks    |
|------------------------|-----------|
| Identifier integrity   | G1, G2, G3 |
| Temporal & spatial     | G4, G5    |
| Duplicates             | G6        |
| Cycling structure      | C1, C2, C3 |

For each category, the same additive deduction formula is applied to *only* that category's checks:

```
cat_score = max(0, round(100 − Σ (deductions of checks in this category)))
```

When a category was only **partially run** (e.g. Quick Scan runs G1, G2, G3 but skips G4–G6), the deduction is up-scaled by `len(all_checks_in_category) / len(checks_that_ran)` before subtracting from 100, so partial coverage doesn't inflate the category score. Categories where **no** checks ran are shown as "— · not run".

The category bars are a diagnostic view — they help locate where issues concentrate (e.g. identifier integrity vs. cycling structure) — and are computed independently of the overall score.

### Tuning the penalties

All four scoring constants live at the top of the `QUALITY SCORING` block in [strada/core/verify.py](strada/core/verify.py):

```python
CRITICAL_BASE_PENALTY = 10.0
CRITICAL_RATE_PENALTY = 30.0
NONCRIT_BASE_PENALTY  = 5.0
NONCRIT_RATE_PENALTY  = 30.0
```

Adjust these in one place to re-calibrate how harshly the score treats failing checks; no other code needs to change.

---

## Micromobility Classification

The `classify` command / Classify tab is specific to cycling/micromobility analyses. It classifies each Cykel entry by searching the free-text event descriptions and structured STRADA fields.

| Type | Description |
|------|-------------|
| `Conventional bicycle` | Standard pedal-powered bicycle (default) |
| `E-bike` | Electrically assisted bicycle |
| `E-scooter` | Electric kick-scooter (elsparkcykel) |
| `rullstol/permobil` | Wheelchair / powered wheelchair |
| `other_micromobility` | Skateboard, hoverboard, inlines, etc. |
| `N/A` | Not a Cykel entry |

### Classification pipeline

The classifier uses a **4-step guarded pipeline** designed to handle a key data challenge: the police narrative `Händelseförlopp (P)` is shared by all persons in the same crash. In multi-Cykel crashes (e.g. a conventional bicycle and an e-scooter in the same collision), naively scanning `(P)` would mis-label every person with whatever keyword appears first. The guards prevent this contamination.

#### Step 1 — Police narrative `(P)` with guards

Search `Händelseförlopp (P)` for micromobility keywords.

| Guard | Condition | Action |
|-------|-----------|--------|
| **A – Solo Cykel** | Only one Cykel person in the crash | Accept the match directly (no ambiguity) |
| **B – Trafikelement Nr** | Person's `Trafikelement Nr (P)` appears next to the keyword in the text | Accept (keyword is about this person) |
| **C – Undergrupp cross-ref** | Person's own Undergrupp confirms the matched type | Accept |
| **D – Fallthrough** | None of the above hold | Do **not** trust `(P)` for this person; fall through to Step 2 |

#### Step 2 — Hospital narrative `(S)` with guards

Search `Händelseförlopp (S)` for micromobility keywords. `(S)` is written per-person, so contamination is less likely, but the *conflict partner* can still be mentioned.

| Guard | Condition | Action |
|-------|-----------|--------|
| **A – Solo Cykel** | Only one Cykel person in the crash | Accept the match directly |
| **B – Conflict partner** | The person's `I Konflikt med – Undergrupp` matches the keyword type | Reject (the keyword describes the opponent, not the person) |
| **C – Per-person** | Guard B did not fire | Accept (assume `(S)` describes this person) |

#### Step 3 — Undergrupp fallback

If neither narrative produced a match, map the person's `Sammanvägd Trafikantkategori – Undergrupp` value (e.g. `Elcykel` → E-bike, `Eldrivet enpersonsfordon` → E-scooter, `Eldriven rullstol` → rullstol/permobil).

#### Step 4 — Default

If all previous steps produced no match, classify as `Conventional bicycle`.

### Keyword matching details

- **Case-insensitive** search for Swedish keywords (e.g. *elcykel*, *elsparkcykel*, *kickbike*).
- **Whole-word matching** for brand names (`voi`, `lime`, `bird`, `tier`, `bolt`) to avoid false positives.
- **Multi-match resolution:** If keywords from multiple categories match in the same text, priority order is: E-scooter > E-bike > rullstol/permobil > other_micromobility > Conventional bicycle.

### Confidence levels

Each classified person receives a `Classification_confidence` value:

| Confidence | Meaning |
|------------|---------|
| `high` | Keyword found in narrative and confirmed by a guard |
| `medium` | Classified via Undergrupp fallback (Step 3) |
| `low` | No evidence found; defaulted to Conventional bicycle (Step 4) |

---

## Report Formats

### Text report (`strada_quality_report.txt`)

Human-readable summary with:
- Overview table showing pass/fail status for each check
- Detailed sections listing every flagged record
- Suitable for quick review and documentation

### CSV report (`strada_quality_report.csv`)

Machine-readable table with columns:
| Column | Description |
|--------|-------------|
| `check_id` | Check identifier (e.g. G1, G3.2) |
| `check_name` | Human-readable check name |
| `crash_id` | Affected Olycksnummer |
| `issue` | Summary of the issue |
| `details` | Semicolon-separated key=value pairs |

This format is ideal for:
- Opening in Excel for review
- Filtering and sorting issues
- Programmatic downstream processing

---

## Project Structure

```
STRADA_toolbox/
├── pyproject.toml              # Package build configuration
├── requirements.txt            # Dependencies (alternative to pip install .)
├── README.md                   # This file
│
└── strada/                     # Python package
    ├── __init__.py
    ├── cli.py                  # Typer CLI (entry point: strada)
    ├── app.py                  # Streamlit web dashboard
    │
    ├── config/
    │   ├── __init__.py         # Re-exports from constants
    │   ├── constants.py        # All column names, keywords, magic strings
    │   └── styles.py           # Dashboard CSS
    │
    ├── core/
    │   ├── __init__.py
    │   ├── preprocess.py       # Excel→CSV conversion, year filtering
    │   ├── checks.py           # The 9 check functions (G1–G6, C1–C3)
    │   ├── verify.py           # Check registry (CheckSpec), runner, quality scoring
    │   └── classify.py         # Micromobility classification
    │
    ├── web/
    │   ├── __init__.py
    │   └── components.py       # HTML builders for the dashboard
    │
    └── io/
        ├── __init__.py
        ├── readers.py          # CSV / Excel loading with encoding handling
        └── reporters.py        # Text and CSV report generation
```

### Key design principles

- **Separation of concerns:** Core logic (`core/`) is independent of the interface. Both `cli.py` and `app.py` call the same functions.
- **Centralised constants:** All column names, keywords, and magic strings are in `config/constants.py`. If the STRADA schema changes, only one file needs updating.
- **Registry-driven checks:** Every check is one `CheckSpec` entry in `core/verify.py`. Severity tags, score categories, generic-vs-cycling grouping, dashboard checkbox labels, and the About-tab tables all derive from this single list — adding a check is a two-file edit (see [Adding new checks](#adding-new-checks)).
- **Structured results:** Every check returns a `VerificationResult` dataclass, making it easy to add new report formats or interfaces.
- **Pure HTML components:** Dashboard rendering helpers live in `web/components.py` as plain functions returning HTML strings — no Streamlit calls — so they're easy to test and reuse.
- **No hardcoded paths:** All file paths are passed as arguments.

---

## Configuration & Customisation

### Modifying keywords

To add or remove micromobility keywords, edit `strada/config/constants.py`:

```python
MICROMOBILITY_KEYWORDS = {
    "E-scooter": [
        "elscooter", "elspark", ...
        # Add your keywords here
    ],
    ...
}
```

### Adding new checks

Checks are registry-driven, so adding one is a **two-file edit**:

**1.** In `strada/core/checks.py`, define the function and add its severity to `CHECK_SEVERITY`:

```python
CHECK_SEVERITY: dict[str, str] = {
    ...,
    "G7": "non-critical",   # ← add your check's severity here
}

def check_g7_my_new_check(df_olyckor, df_personer) -> VerificationResult:
    # ... your logic ...
    return VerificationResult(
        check_id="G7",
        check_name="My new check",
        status=_status_for("G7", n),   # auto-derives from CHECK_SEVERITY
        summary="...",
        issue_count=n,
        details=df_details,
    )
```

**2.** In `strada/core/verify.py`, import the function and append a `CheckSpec` entry to `CHECK_SPECS`:

```python
from strada.core.checks import (
    ...,
    check_g7_my_new_check,
)

CHECK_SPECS: list[CheckSpec] = [
    ...,
    CheckSpec(
        id="G7",
        name="My new check",                       # used for checkbox + result name
        description="My new check, longer text",   # used in About tab
        severity=CHECK_SEVERITY["G7"],
        category="temporal_spatial",               # one of CATEGORY_META keys
        family="generic",                          # "generic" or "cycling"
        func=check_g7_my_new_check,
    ),
]
```

That's it — the CLI, web dashboard checkboxes, bundle presets, score categories, and About-tab tables all pick it up automatically. To add a new score category instead of reusing an existing one, also extend `CATEGORY_META` in `verify.py`.

### Changing column names

All column names are defined as constants in `strada/config/constants.py`. If a STRADA export uses different column names, update the constants there.

---

## Workflow Diagram

```
┌────────────────────┐
│  STRADA Excel file │
│  (.xlsx workbook)  │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  strada preprocess │  ← Converts Excel → CSV, optional year filter
│                    │
│  Output:           │
│  • Olyckor.csv     │
│  • Personer.csv    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  strada verify     │  ← Runs G1–G6 (generic) + C1–C3 (cycling, optional)
│                    │
│  Output:           │
│  • .txt report     │
│  • .csv report     │
└────────┬───────────┘
         │
         │  (User reviews report, decides which records
         │   to exclude from analysis)
         │
         ▼
┌────────────────────┐
│  strada classify   │  ← Cycling-specific: E-scooter / E-bike / etc.
│  (optional)        │
│                    │
│  Output:           │
│  • Personer-       │
│    analysis-       │
│    ready.csv       │
└────────────────────┘
```

---

## Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/my-new-check`)
3. Make your changes and add tests
4. Run `pip install -e ".[dev]"` and `pytest`
5. Submit a pull request

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

*Developed for the Swedish STRADA research community.*
