# STRADA Toolbox

**Data quality assessment toolkit for STRADA (Swedish Traffic Accident Data Acquisition) datasets.**

STRADA is a national information system for road traffic injuries managed by the Swedish Transport Agency (Transportstyrelsen). This toolbox automates data-quality checks for the two core STRADA tables — **Olyckor** (Crashes) and **Personer** (Persons) — and provides both a **command-line interface** and a **web dashboard** so that researchers with any level of coding experience can use it.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Usage — Command-Line Interface (CLI)](#usage--command-line-interface-cli)
   - [preprocess](#1-preprocess)
   - [verify](#2-verify)
   - [classify](#3-classify-cycling-specific)
   - [web](#4-web-dashboard)
4. [Usage — Web Dashboard](#usage--web-dashboard)
5. [Verification Checks Reference](#verification-checks-reference)
   - [Generic Checks (G1–G6)](#generic-checks-g1g6)
   - [Cycling-Specific Checks (C1–C3)](#cycling-specific-checks-c1c3)
6. [Micromobility Classification](#micromobility-classification)
7. [Report Formats](#report-formats)
8. [Project Structure](#project-structure)
9. [Configuration & Customisation](#configuration--customisation)
10. [Workflow Diagram](#workflow-diagram)
11. [Contributing](#contributing)
12. [License](#license)

---

## Quick Start

```bash
# 1. Install
cd STRADA_toolbox
pip install .

# 2. Run all generic data-quality checks
strada verify \
    --olyckor path/to/Olyckor.csv \
    --personer path/to/Personer.csv

# 3. Include cycling-specific checks
strada verify \
    --olyckor path/to/Olyckor.csv \
    --personer path/to/Personer.csv \
    --cycling

# 4. Or launch the web dashboard (no terminal needed after this)
strada web
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

## Usage — Command-Line Interface (CLI)

After installation, the `strada` command is available in your terminal.
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

Opens a browser-based dashboard. See the [Web Dashboard](#usage--web-dashboard) section for details.

---

## Usage — Web Dashboard

The web dashboard provides the same functionality as the CLI but through a graphical interface. It is designed for users who are less comfortable with command-line tools.

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

## Verification Checks Reference

### Generic Checks (G1–G6)

These checks apply to **any** STRADA analysis, regardless of road-user type.

#### G1 — Crash-ID Consistency

Verifies that every `Olycksnummer` in the Olyckor dataset has at least one matching entry in the Personer dataset, and vice versa.

- **Why it matters:** Missing crash IDs indicate data extraction issues or incomplete joins.
- **What is flagged:** IDs that exist in one dataset but not the other.

#### G2 — Crash-Type (Olyckstyp) Consistency

Two sub-checks:
- **G2.1:** Checks for missing `Olyckstyp` values in both datasets.
- **G2.2:** For each crash ID present in both datasets, verifies that the `Olyckstyp` value matches.

- **Why it matters:** Inconsistent crash types between datasets may indicate data entry errors or misaligned records.

#### G3 — Road-User Category (Trafikantkategori) Consistency

Four sub-checks on the Personer dataset:
- **G3.1:** At least one of the three category columns (`Trafikantkategori (P) - Undergrupp`, `Trafikantkategori (S) - Undergrupp`, `Sammanvägd Trafikantkategori - Undergrupp`) must be filled.
- **G3.2:** When both P and S are filled, they should match.
- **G3.3:** When P or S is filled, it should match `Sammanvägd` (allows prefix matching, e.g. `"Lastbil (lätt)"` matches `"Lastbil"`).
- **G3.4:** When both P and S are filled, at least one should match `Sammanvägd`.

- **Why it matters:** The `Sammanvägd` (combined) category is derived from P (Police) and S (Hospital) reports. Discrepancies may indicate classification errors.

#### G4 — Timeline Consistency

For each crash with multiple person entries, verifies that:
1. The date (`År`, `Månad`, `Dag`) is the same across all entries.
2. The time (`Klockslag grupp (timme)`) is the same across all entries.

Date mismatches are reported first, followed by time mismatches sorted by the magnitude of the time difference.

- **Why it matters:** All persons in the same crash should have the same date and time.

#### G5 — Location Consistency (Län / Kommun)

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

#### C1 — G1 (cykel singel) Crash Validation

For crashes typed `G1 (cykel singel)`:
- There should be exactly **one** person entry.
- That entry should have `Sammanvägd Trafikantkategori - Huvudgrupp == "Cykel"`.
- When multiple persons exist, the count of passengers (identified by `"Passagerare"` in role columns) is reported.

#### C2 — Cykel Presence

Verifies that every crash has at least one person with `Huvudgrupp == "Cykel"`. Relevant only when the dataset was extracted as a cycling dataset.

#### C3 — Cykel Passengers Only

Flags crashes where **all** Cykel entries are passengers (no driver/cyclist). This can indicate a data-entry issue where the cyclist is missing from the record.

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
    │   └── constants.py        # All column names, keywords, magic strings
    │
    ├── core/
    │   ├── __init__.py
    │   ├── preprocess.py       # Excel→CSV conversion, year filtering
    │   ├── verify.py           # All 9 verification checks (G1–G6, C1–C3)
    │   └── classify.py         # Micromobility classification
    │
    └── io/
        ├── __init__.py
        ├── readers.py          # CSV / Excel loading with encoding handling
        └── reporters.py        # Text and CSV report generation
```

### Key design principles

- **Separation of concerns:** Core logic (`core/`) is independent of the interface. Both `cli.py` and `app.py` call the same functions.
- **Centralised constants:** All column names, keywords, and magic strings are in `config/constants.py`. If the STRADA schema changes, only one file needs updating.
- **Structured results:** Every check returns a `VerificationResult` dataclass, making it easy to add new report formats or interfaces.
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

1. Create a new function in `strada/core/verify.py` following the pattern:

```python
def check_g7_my_new_check(df_olyckor, df_personer) -> VerificationResult:
    # ... your logic ...
    return VerificationResult(
        check_id="G7",
        check_name="My new check",
        status="pass" if no_issues else "warning",
        summary="...",
        issue_count=n,
        details=df_details,
    )
```

2. Add it to the `GENERIC_CHECKS` or `CYCLING_CHECKS` list at the bottom of the file.
3. The CLI and web dashboard will automatically pick it up.

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
