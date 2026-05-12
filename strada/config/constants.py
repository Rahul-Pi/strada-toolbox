"""
Configuration constants for the STRADA Toolbox.

All column names, keywords, and magic strings used across the toolbox are
centralised here so that upstream schema changes need only one edit.

Organised into three sections:
  1. Schema columns       — exact column names used in the CSV exports
  2. Domain constants     — sentinel values, role lists, encoding, etc.
  3. Micromobility config — keyword dictionaries used by classify.py
"""


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  1. SCHEMA COLUMNS                                                        ║
# ║     Exact column names from STRADA CSV exports.                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# ── Shared between Olyckor and Personer ──

COL_CRASH_ID   = "Olycksnummer"
COL_CRASH_TYPE = "Olyckstyp"
COL_YEAR       = "År"
COL_MONTH      = "Månad"
COL_DAY        = "Dag"
COL_TIME       = "Klockslag grupp (timme)"
COL_REFERENCE  = "Referens"

# ── Personer only — demographics & location ──

COL_AGE          = "Ålder"
COL_GENDER       = "Kön"
COL_COUNTY       = "Län"
COL_MUNICIPALITY = "Kommun"
COL_STREET       = "Olycksväg/-gata"

# ── Personer only — road-user category ──

COL_CATEGORY_MAIN = "Sammanvägd Trafikantkategori - Huvudgrupp"
COL_CATEGORY_SUB  = "Sammanvägd Trafikantkategori - Undergrupp"
COL_CATEGORY_P    = "Trafikantkategori (P) - Undergrupp"
COL_CATEGORY_S    = "Trafikantkategori (S) - Undergrupp"

# ── Personer only — roles & free-text narratives ──

COL_ROLE_P   = "Trafikantroll (P)"
COL_ROLE_S   = "Trafikantroll (S)"
COL_EVENT_P  = "Händelseförlopp (P)"
COL_EVENT_S  = "Händelseförlopp (S)"

# ── Personer only — reporting source & injury ──

COL_TE_NR_P         = "Trafikelement Nr (P)"           # police-specific
COL_KONFLIKT_UG     = "I Konflikt med - Undergrupp"    # hospital-specific
COL_POLICE_REPORT   = "Polisrapport"
COL_HOSPITAL_REPORT = "Sjukvårdsrapport"
COL_MAIS            = "MAIS"
COL_INJURY_SEVERITY = "Sammanvägd skadegrad"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  2. DOMAIN CONSTANTS                                                      ║
# ║     Sentinel values, role lists, and the duplicate-detection column set.  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

CYKEL_CATEGORY    = "Cykel"
CYKEL_SINGEL_TYPE = "G1 (cykel singel)"
GENDER_UNKNOWN    = "Uppgift saknas"

PASSENGER_ROLES = [
    "Passsagerare övrig/okänd plats",   # NB: triple 's' is in the original data
    "Passagerare bak",
    "Passagerare fram",
]

# Columns compared when looking for duplicate persons across crashes (G6).
DUPLICATE_DETECTION_COLS = [
    COL_AGE,
    COL_YEAR,
    COL_MONTH,
    COL_DAY,
    COL_GENDER,
    COL_COUNTY,
    COL_MUNICIPALITY,
    COL_TIME,
    COL_STREET,
    COL_CATEGORY_MAIN,
]

# Default encoding for STRADA CSV reads & writes.
CSV_ENCODING = "utf-8-sig"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  3. MICROMOBILITY CLASSIFICATION                                          ║
# ║     Keyword dictionaries and lookup tables for strada.core.classify.      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

MICROMOBILITY_KEYWORDS: dict[str, list[str]] = {
    "E-scooter": [
        "elscooter", "elspark", "el-spark", "elkickbike", "el-kickbike",
        "kickbike", "elsparkcykel", "el-sparkcykel", "elsparkcyklar",
        "el-sparkcyklar", "elsparkscykel", "elsparkscyklar", "el-sparkscykel",
        "elsparken", "elscootern", "e-scooter", "e-scootern",
        "elscootrar", "elscootrarna", "scooter", "scootern", "scootrar",
        "skoter", "skotern", "skotrar", "elskoter", "el-skoter",
        "el sparkcykel", "el sparkscykel", "el sparkcyklar",
        "el scooter", "el-scooter",
        "elsparcykel", "el-sparcykel", "elsparcykeln",
        "elsparkcykeln", "elsparkcyklarna",
        "el-sparkcykeln", "el-sparkcyklarna",
        "elsarkcykel", "elparkcykel", "elsparlcykel", "el-sparlcykel",
        "el-sparlcyklar", "elsparlcyklar",
        "scotter", "elscotter", "el-scotter",
        "elscoter", "el-scotty", "sparkcykel",
        "voi", "voien", "VOJ", "lime", "bird", "tier", "ryde",
        "spark", "Eldrivet enpersonsfordon", "elsparcyklar", "El-kick",
        "eldrivet enpersonfordon", "Eldrivna enpersonsfordonet",
        "elsccoter",
    ],
    "E-bike": [
        "elcykel", "e-bike", "elcyklar", "el-cykel", "el-cyklar",
        "elcykler", "elcykeln", "elcyklarna", "elcykelar", "elcykelarna",
        "eldriven cyklar", "eldriven cykel",
        "el-driven cykel", "el driven cykel",
        "el driven cyklar", "el-driven cyklar",
        "el-cykeln", "el-cyklarna",
        "fatbike", "fat-bike", "fatbiken",
        "speed pedelec", "speedpedelec",
        "el-bike", "el bike", "elcyckel",
        "lådcykeln", "låd cykel", "lådcykel", "lådcykel", "lådcykeln",
        'elcyklist', 'el-cyklist',
    ],
    "rullstol/permobil": [
        "rullstol", "permobil", "elrullstol", "el-rullstol", "rullstolar",
    ],
    "other_micromobility": [
        "elskateboarden", "elskateboard", "enhjuling", "onewheel",
        "el-skateboard", "elmoped", "långboard", "el-långboard",
        "hoverboard", "elhoverboard", "el-hoverboard", "moped", "el-moped",
        "skateboard", "inlines",
    ],
}

# Keywords that should only match as whole words (e.g. brand names that are
# also common substrings).
WHOLE_WORD_KEYWORDS: set[str] = {
    "voi", "voien", "voj", "lime", "bird", "tier", "ryde", "spark",
}

# Order in which categories are resolved when an entry matches multiple.
MICROMOBILITY_PRIORITY: list[str] = [
    "E-scooter",
    "E-bike",
    "rullstol/permobil",
    "other_micromobility",
    "Conventional bicycle",
]

# Undergrupp values that already encode an electric/specific type.
ELECTRIC_UNDERGRUPP: set[str] = {
    "Elcykel",
    "Eldrivet enpersonsfordon",
    "Sparkcykel",
    "Eldriven rullstol",
}

# Undergrupp → Micromobility_type mapping (Step 3 fallback in classify.py).
UNDERGRUPP_MAP: dict[str, str] = {
    "Elcykel": "E-bike",
    "Eldrivet enpersonsfordon": "E-scooter",
    "Eldriven rullstol": "rullstol/permobil",
    "Sparkcykel": "E-scooter",
    "Rullstol": "rullstol/permobil",
    "Inlines": "other_micromobility",
    "Skateboard": "other_micromobility",
    "Cykel - Annan": "Conventional bicycle",
    "Cykel": "Conventional bicycle",
}

# "I Konflikt med - Undergrupp" values indicating the CONFLICT PARTNER is a
# specific micromobility type (hospital-only Guard B, Step 2 in classify.py).
CONFLICT_PARTNER_EXCLUSIONS: dict[str, set[str]] = {
    "E-scooter": {"Eldrivet enpersonsfordon", "Sparkcykelåkare"},
    "E-bike": {"Elcykel"},
    "rullstol/permobil": {"Eldriven rullstol", "Rullstolsburen"},
}

# Undergrupp (P) values that indicate a specific electric type (Step 1 Guard C).
SPECIFIC_UNDERGRUPP_P: set[str] = {
    "Eldrivet enpersonsfordon",
    "Elcykel",
    "Eldriven rullstol",
}
