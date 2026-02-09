"""
Micromobility classification for cycling-specific STRADA analyses.

This module adds:
  1. A ``Micromobility_type`` column (E-scooter, E-bike, Conventional bicycle, …).
  2. Cross-verification against the ``Undergrupp`` column.
  3. A ``Conflict_partner`` column listing the other road-user types involved
     in the same crash.

These functions are relevant **only** when the dataset has been filtered to
cycling / micromobility crashes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from strada.config.constants import (
    COL_CRASH_ID,
    COL_CATEGORY_MAIN,
    COL_CATEGORY_SUB,
    COL_EVENT_P,
    COL_EVENT_S,
    CYKEL_CATEGORY,
    MICROMOBILITY_KEYWORDS,
    WHOLE_WORD_KEYWORDS,
    MICROMOBILITY_PRIORITY,
    ELECTRIC_UNDERGRUPP,
)
from strada.io.reporters import VerificationResult


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword matching
# ═══════════════════════════════════════════════════════════════════════════════

def _find_keyword_matches(
    text: str,
    keywords_dict: dict[str, list[str]],
) -> list[str]:
    """Return a list of category names that have at least one keyword match.

    Parameters
    ----------
    text : str
        The free-text narrative to search (already expected to be non-empty).
    keywords_dict : dict
        ``{category_name: [keyword, …]}``.

    Returns
    -------
    list[str] — matched category names (may be empty).
    """
    text_lower = text.lower()
    matches: list[str] = []

    for category, keywords in keywords_dict.items():
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in WHOLE_WORD_KEYWORDS:
                if re.search(r"\b" + re.escape(kw_lower) + r"\b", text_lower):
                    matches.append(category)
                    break
            else:
                if kw_lower in text_lower:
                    matches.append(category)
                    break

    return matches


# ═══════════════════════════════════════════════════════════════════════════════
# Row-level classification
# ═══════════════════════════════════════════════════════════════════════════════

def _classify_row(row: pd.Series) -> tuple[str, list[str], str | None]:
    """Classify one person row into a micromobility type.

    Returns
    -------
    (type, all_matches, source_column)
    """
    # Only classify Cykel rows
    if row.get(COL_CATEGORY_MAIN) != CYKEL_CATEGORY:
        return "N/A", [], None

    text_p = row.get(COL_EVENT_P, "")
    text_s = row.get(COL_EVENT_S, "")

    if pd.notna(text_p) and str(text_p).strip():
        primary_text = str(text_p)
        source = "P"
    elif pd.notna(text_s) and str(text_s).strip():
        primary_text = str(text_s)
        source = "S"
    else:
        return "Unknown", [], None

    matches = _find_keyword_matches(primary_text, MICROMOBILITY_KEYWORDS)

    if not matches:
        # Fallback: check Undergrupp
        undergrupp = str(row.get(COL_CATEGORY_SUB, ""))
        if undergrupp == "Elcykel":
            return "E-bike", [], "Undergrupp"
        elif undergrupp == "Eldrivet enpersonsfordon":
            return "E-scooter", [], "Undergrupp"
        else:
            return "Conventional bicycle", [], source

    # Apply priority
    for priority_cat in MICROMOBILITY_PRIORITY:
        if priority_cat in matches:
            return priority_cat, matches, source

    return "Conventional bicycle", matches, source


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def classify_micromobility(
    df_personer: pd.DataFrame,
) -> pd.DataFrame:
    """Add a ``Micromobility_type`` column to the Personer DataFrame.

    Non-Cykel rows receive ``"N/A"``.

    Parameters
    ----------
    df_personer : pd.DataFrame
        The persons table (modified in-place *and* returned).

    Returns
    -------
    pd.DataFrame with the new column.
    """
    results = df_personer.apply(_classify_row, axis=1, result_type="expand")
    df_personer["Micromobility_type"] = results[0]
    df_personer["_all_matches"] = results[1]
    df_personer["_source_col"] = results[2]
    return df_personer


def verify_classification(
    df_personer: pd.DataFrame,
) -> tuple[VerificationResult, VerificationResult, pd.DataFrame]:
    """Cross-check ``Micromobility_type`` against ``Undergrupp``.

    Returns
    -------
    (result_2a, result_2b, multi_matches)
        * result_2a: E-scooter / E-bike classified but Undergrupp ≠ electric.
        * result_2b: Conventional bicycle but Undergrupp = electric.
        * multi_matches: rows that matched multiple keyword categories.
    """
    electric_types = {"E-scooter", "E-bike"}

    # 2a
    mismatch_2a = df_personer[
        df_personer["Micromobility_type"].isin(electric_types)
        & ~df_personer[COL_CATEGORY_SUB].isin(ELECTRIC_UNDERGRUPP)
    ][[COL_CRASH_ID, "Micromobility_type", COL_CATEGORY_SUB]].copy()

    res_2a = VerificationResult(
        check_id="CL.1",
        check_name="E-scooter/E-bike without matching Undergrupp",
        status="pass" if len(mismatch_2a) == 0 else "warning",
        summary=(
            "✓ All E-scooter/E-bike classifications match Undergrupp"
            if len(mismatch_2a) == 0
            else f"⚠ {len(mismatch_2a)} electric types without matching Undergrupp"
        ),
        issue_count=len(mismatch_2a),
        details=mismatch_2a if len(mismatch_2a) > 0 else None,
    )

    # 2b
    mismatch_2b = df_personer[
        (df_personer["Micromobility_type"] == "Conventional bicycle")
        & df_personer[COL_CATEGORY_SUB].isin(ELECTRIC_UNDERGRUPP)
    ][[COL_CRASH_ID, "Micromobility_type", COL_CATEGORY_SUB]].copy()

    res_2b = VerificationResult(
        check_id="CL.2",
        check_name="Conventional bicycle with electric Undergrupp",
        status="pass" if len(mismatch_2b) == 0 else "warning",
        summary=(
            "✓ No Conventional bicycle with electric Undergrupp"
            if len(mismatch_2b) == 0
            else f"⚠ {len(mismatch_2b)} Conventional bicycle with electric Undergrupp"
        ),
        issue_count=len(mismatch_2b),
        details=mismatch_2b if len(mismatch_2b) > 0 else None,
    )

    # Multi-category matches
    multi = df_personer[df_personer["_all_matches"].apply(lambda x: len(x) > 1)]
    multi_out = multi[[COL_CRASH_ID, "Micromobility_type", "_all_matches"]].copy()

    return res_2a, res_2b, multi_out


def add_conflict_partner(
    df_personer: pd.DataFrame,
) -> pd.DataFrame:
    """Add a ``Conflict_partner`` column for Cykel persons.

    For each Cykel person in a crash, lists the ``Huvudgrupp`` of all *other*
    persons in the same crash.  For single-person crashes (singel), the value
    is ``"Single"``

    Parameters
    ----------
    df_personer : pd.DataFrame
        Modified in-place and returned.

    Returns
    -------
    pd.DataFrame
    """
    # Build a mapping: crash_id → list of all Huvudgrupp values
    crash_categories = (
        df_personer
        .groupby(COL_CRASH_ID)[COL_CATEGORY_MAIN]
        .apply(list)
        .to_dict()
    )

    def _get_partners(row):
        if row[COL_CATEGORY_MAIN] != CYKEL_CATEGORY:
            return "N/A"
        crash_id = row[COL_CRASH_ID]
        all_cats = crash_categories.get(crash_id, [])
        # Remove one instance of Cykel (the current person)
        others = list(all_cats)
        if CYKEL_CATEGORY in others:
            others.remove(CYKEL_CATEGORY)
        if not others:
            return "Single"
        # Unique partners in order of appearance
        seen = []
        for c in others:
            if c not in seen and pd.notna(c):
                seen.append(c)
        return ", ".join(seen)

    df_personer["Conflict_partner"] = df_personer.apply(_get_partners, axis=1)
    return df_personer


def run_classification_pipeline(
    df_personer: pd.DataFrame,
) -> tuple[pd.DataFrame, list[VerificationResult], pd.DataFrame]:
    """Full classification pipeline.

    1. Classify micromobility types.
    2. Verify classifications.
    3. Add conflict partners.

    Returns
    -------
    (df, verification_results, multi_matches)
    """
    df = classify_micromobility(df_personer)
    res_2a, res_2b, multi = verify_classification(df)
    df = add_conflict_partner(df)

    # Clean up internal columns
    df.drop(columns=["_all_matches", "_source_col"], inplace=True, errors="ignore")

    return df, [res_2a, res_2b], multi
