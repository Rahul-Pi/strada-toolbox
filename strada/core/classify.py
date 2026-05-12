"""
Micromobility classification for cycling-specific STRADA analyses.

This module implements a **4-step guarded classification pipeline**:

  1. **Step 1** — Keyword search on the police narrative ``(P)``, which is
     shared per-crash and therefore needs contamination guards for
     multi-Cykel crashes.
  2. **Step 2** — Keyword search on the hospital narrative ``(S)``, which is
     per-person and therefore safer, but still guarded against conflict-
     partner contamination.
  3. **Step 3** — Structured ``Undergrupp`` fallback using ``UNDERGRUPP_MAP``.
  4. **Step 4** — Default to ``Conventional bicycle``.

The module also adds:
  - Cross-verification against the ``Undergrupp`` column.
  - A ``Conflict_partner`` column listing the other road-user types involved
    in the same crash.

These functions are relevant **only** when the dataset has been filtered to
cycling / micromobility crashes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from strada.config.constants import (
    COL_CRASH_ID,
    COL_CATEGORY_MAIN,
    COL_CATEGORY_SUB,
    COL_CATEGORY_P,
    COL_EVENT_P,
    COL_EVENT_S,
    COL_TE_NR_P,
    COL_KONFLIKT_UG,
    CYKEL_CATEGORY,
    MICROMOBILITY_KEYWORDS,
    WHOLE_WORD_KEYWORDS,
    MICROMOBILITY_PRIORITY,
    ELECTRIC_UNDERGRUPP,
    UNDERGRUPP_MAP,
    CONFLICT_PARTNER_EXCLUSIONS,
    SPECIFIC_UNDERGRUPP_P,
)
from strada.io.reporters import VerificationResult


# ═══════════════════════════════════════════════════════════════════════════════
# Result container for classification statistics
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassificationStats:
    """Aggregate statistics produced by the classification pipeline."""

    total_cykel: int = 0
    solo_cykel_crashes: int = 0
    multi_cykel_crashes: int = 0
    multi_cykel_persons: int = 0

    step_counts: dict[str, int] = field(default_factory=lambda: {
        "Step 1": 0, "Step 2": 0, "Step 3": 0, "Step 4": 0,
    })
    guard_counts: dict[str, int] = field(default_factory=lambda: {
        "Step1_GuardA": 0, "Step1_GuardB": 0,
        "Step1_GuardC": 0, "Step1_GuardD": 0,
        "Step2_GuardA": 0, "Step2_GuardB": 0, "Step2_GuardC": 0,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword matching
# ═══════════════════════════════════════════════════════════════════════════════

def _find_keyword_matches(
    text: str,
    keywords_dict: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return a list of category names that have at least one keyword match.

    Parameters
    ----------
    text : str
        The free-text narrative to search (already expected to be non-empty).
    keywords_dict : dict, optional
        ``{category_name: [keyword, …]}``.  Defaults to
        ``MICROMOBILITY_KEYWORDS``.

    Returns
    -------
    list[str] — matched category names (may be empty).
    """
    if keywords_dict is None:
        keywords_dict = MICROMOBILITY_KEYWORDS

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


def _resolve_priority(matches: list[str]) -> str | None:
    """Given a list of matched categories, return the highest-priority one."""
    for cat in MICROMOBILITY_PRIORITY:
        if cat in matches:
            return cat
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1 Guard B: Trafikelement Nr disambiguation
# ═══════════════════════════════════════════════════════════════════════════════

def _try_trafikelement_disambiguation(
    text_p: str,
    person_te_nr: Any,
    keywords_dict: dict[str, list[str]],
) -> str | None:
    """Try to associate keyword mentions in a shared (P) narrative with a
    specific ``Trafikelement Nr``.

    Police narratives often use numbered references like
    ``'cyklist 1 (elsparkcykel)'`` or ``'fordon 2 (elcykel)'``.

    Returns the category for *this* person's TE nr, or ``None`` if
    disambiguation is not possible.
    """
    if pd.isna(text_p) or text_p == "" or pd.isna(person_te_nr):
        return None

    text_lower = str(text_p).lower()
    te_nr = str(person_te_nr).replace(".0", "")  # "1.0" → "1"

    ref_patterns = [
        r"(?:cyklist|förare|trafikant|fordon|part)\s*"
        + re.escape(te_nr)
        + r"\s*\(?\s*(.{1,80})",
    ]

    for pattern in ref_patterns:
        match = re.search(pattern, text_lower)
        if match:
            context_after = match.group(1)
            found = _find_keyword_matches(context_after, keywords_dict)
            if found:
                return _resolve_priority(found)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1 Guard C: Cross-reference Undergrupp (P) of other Cykel persons
# ═══════════════════════════════════════════════════════════════════════════════

def _try_undergrupp_p_cross_reference(
    matches: list[str],
    person_ug_p: Any,
    other_persons_ug_p: list[Any],
) -> list[str]:
    """Filter out categories that likely belong to *another* Cykel person.

    If *this* person's ``Undergrupp(P)`` is generic ("Cykel") but another
    Cykel person in the same crash has a specific ``Undergrupp(P)`` matching
    one of the keyword categories, the keyword mention likely belongs to that
    *other* person.

    Returns filtered matches, or the original list if no cross-reference is
    possible.
    """
    if not matches or pd.isna(person_ug_p):
        return matches

    person_ug = str(person_ug_p).strip()

    # Only apply if THIS person has a generic classification
    if person_ug in SPECIFIC_UNDERGRUPP_P:
        return matches

    # Check if any OTHER person has a specific Undergrupp (P)
    other_specific: set[str] = set()
    for ug in other_persons_ug_p:
        if pd.notna(ug) and str(ug).strip() in SPECIFIC_UNDERGRUPP_P:
            other_specific.add(str(ug).strip())

    if not other_specific:
        return matches

    # Map other persons' Undergrupp(P) → categories and exclude those
    exclude_categories: set[str] = set()
    for ug in other_specific:
        mapped = UNDERGRUPP_MAP.get(ug)
        if mapped and mapped in matches:
            exclude_categories.add(mapped)

    if exclude_categories:
        return [m for m in matches if m not in exclude_categories]

    return matches


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2 Guard B: I Konflikt med exclusion (hospital-only)
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_conflict_partner_exclusion(
    matches: list[str],
    konflikt_undergrupp: Any,
) -> list[str]:
    """Exclude categories when the conflict partner IS the matched type.

    If this person's ``I Konflikt med - Undergrupp`` indicates that the
    collision partner is (e.g.) an E-scooter, and the (S) narrative contains
    E-scooter keywords, those keywords describe the *partner*, not this
    person.
    """
    if not matches or pd.isna(konflikt_undergrupp):
        return matches

    konflikt = str(konflikt_undergrupp).strip()
    exclude: set[str] = set()

    for category, exclusion_values in CONFLICT_PARTNER_EXCLUSIONS.items():
        if konflikt in exclusion_values and category in matches:
            exclude.add(category)

    if exclude:
        return [m for m in matches if m not in exclude]

    return matches


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Undergrupp agreement check
# ═══════════════════════════════════════════════════════════════════════════════

def _undergrupp_agrees(category: str, sammanvagd_ug: Any) -> bool:
    """Return ``True`` if the Sammanvägd Undergrupp corroborates *category*."""
    if pd.isna(sammanvagd_ug):
        return False
    return UNDERGRUPP_MAP.get(str(sammanvagd_ug).strip()) == category


# ═══════════════════════════════════════════════════════════════════════════════
# Core: crash-aware 4-step guarded classification
# ═══════════════════════════════════════════════════════════════════════════════

def classify_micromobility(
    df_personer: pd.DataFrame,
) -> tuple[pd.DataFrame, ClassificationStats]:
    """Add micromobility classification columns using the 4-step guarded
    pipeline.

    Columns added:

    * ``Micromobility_type`` — E-scooter | E-bike | rullstol/permobil |
      other_micromobility | Conventional bicycle | N/A
    * ``Classification_confidence`` — high | medium | low | default
    * ``Classification_step`` — which pipeline step produced the result
    * ``_all_matches`` — (internal) all keyword categories found

    Non-Cykel rows receive ``"N/A"`` for all classification columns.

    Parameters
    ----------
    df_personer : pd.DataFrame
        The persons table (modified in-place *and* returned).

    Returns
    -------
    (df, stats)
        The modified DataFrame and classification statistics.
    """
    stats = ClassificationStats()

    # ── Initialise output columns ──────────────────────────────────────────
    df = df_personer
    df["Micromobility_type"] = "N/A"
    df["Classification_confidence"] = ""
    df["Classification_step"] = ""
    df["_all_matches"] = None
    df["_all_matches"] = df["_all_matches"].astype(object)
    for i in df.index:
        df.at[i, "_all_matches"] = []

    # ── Identify Cykel persons ─────────────────────────────────────────────
    cykel_mask = df[COL_CATEGORY_MAIN] == CYKEL_CATEGORY
    cykel_indices = df[cykel_mask].index
    stats.total_cykel = len(cykel_indices)

    # PRE-STEP: per-crash Cykel count
    cykel_per_crash = df[cykel_mask].groupby(COL_CRASH_ID).size()
    stats.solo_cykel_crashes = int((cykel_per_crash == 1).sum())
    stats.multi_cykel_crashes = int((cykel_per_crash > 1).sum())
    stats.multi_cykel_persons = int(
        cykel_per_crash[cykel_per_crash > 1].sum()
    )

    # Pre-compute: crash → list of Cykel-person indices (for Guard C)
    crash_cykel_groups = df[cykel_mask].groupby(COL_CRASH_ID).groups

    # ── Classify each Cykel person ─────────────────────────────────────────
    kw = MICROMOBILITY_KEYWORDS

    for idx in cykel_indices:
        row = df.loc[idx]
        olycksnummer = row[COL_CRASH_ID]
        n_cykel = cykel_per_crash.get(olycksnummer, 1)
        is_solo = n_cykel == 1

        text_p = row.get(COL_EVENT_P, "")
        text_s = row.get(COL_EVENT_S, "")
        has_p = pd.notna(text_p) and str(text_p).strip() != ""
        has_s = pd.notna(text_s) and str(text_s).strip() != ""

        sammanvagd_ug = row.get(COL_CATEGORY_SUB, "")
        result: str | None = None
        all_matches: list[str] = []
        confidence = ""
        step = ""

        # ── STEP 1: (P) narrative with guards ─────────────────────────
        if has_p and result is None:
            matches_p = _find_keyword_matches(str(text_p), kw)

            if matches_p:
                if is_solo:
                    # Guard A: solo Cykel — safe
                    result = _resolve_priority(matches_p)
                    all_matches = matches_p
                    step = "Step 1 (P, solo)"
                    stats.guard_counts["Step1_GuardA"] += 1
                else:
                    # Guard B: Trafikelement Nr
                    te_nr = row.get(COL_TE_NR_P, "")
                    guard_b = _try_trafikelement_disambiguation(
                        str(text_p), te_nr, kw
                    )
                    if guard_b is not None:
                        result = guard_b
                        all_matches = matches_p
                        step = "Step 1 (P, Guard B: TE Nr)"
                        stats.guard_counts["Step1_GuardB"] += 1
                    else:
                        # Guard C: cross-ref other persons' Undergrupp(P)
                        crash_indices = crash_cykel_groups.get(
                            olycksnummer, []
                        )
                        other_ug_p = [
                            df.at[oi, COL_CATEGORY_P]
                            for oi in crash_indices
                            if oi != idx
                        ]
                        person_ug_p = row.get(COL_CATEGORY_P, "")
                        filtered = _try_undergrupp_p_cross_reference(
                            matches_p, person_ug_p, other_ug_p
                        )
                        if filtered:
                            result = _resolve_priority(filtered)
                            all_matches = matches_p
                            step = "Step 1 (P, Guard C: UG cross-ref)"
                            stats.guard_counts["Step1_GuardC"] += 1
                        else:
                            # Guard D: can't disambiguate — fall through
                            stats.guard_counts["Step1_GuardD"] += 1

            if result is not None:
                stats.step_counts["Step 1"] += 1

        # ── STEP 2: (S) narrative with guards ─────────────────────────
        if has_s and result is None:
            matches_s = _find_keyword_matches(str(text_s), kw)

            if matches_s:
                if is_solo:
                    # Guard A: solo — safe
                    result = _resolve_priority(matches_s)
                    all_matches = matches_s
                    step = "Step 2 (S, solo)"
                    stats.guard_counts["Step2_GuardA"] += 1
                else:
                    # Guard B: I Konflikt med exclusion
                    konflikt_ug = row.get(COL_KONFLIKT_UG, "")
                    filtered = _apply_conflict_partner_exclusion(
                        matches_s, konflikt_ug
                    )
                    if filtered:
                        if (
                            pd.notna(konflikt_ug)
                            and str(konflikt_ug).strip() != ""
                        ):
                            result = _resolve_priority(filtered)
                            all_matches = matches_s
                            step = "Step 2 (S, Guard B: I Konflikt med)"
                            stats.guard_counts["Step2_GuardB"] += 1
                        else:
                            # Guard C: (S) is per-person → keyword likely
                            # refers to this person
                            result = _resolve_priority(filtered)
                            all_matches = matches_s
                            step = (
                                "Step 2 (S, Guard C: per-person assumption)"
                            )
                            confidence = "medium"
                            stats.guard_counts["Step2_GuardC"] += 1

            if result is not None and step.startswith("Step 2"):
                stats.step_counts["Step 2"] += 1

        # ── STEP 3: Structured Undergrupp fallback ────────────────────
        if result is None:
            ug_val = (
                str(sammanvagd_ug).strip()
                if pd.notna(sammanvagd_ug)
                else ""
            )
            mapped = UNDERGRUPP_MAP.get(ug_val)
            if mapped and mapped != "Conventional bicycle":
                result = mapped
                step = "Step 3 (Undergrupp fallback)"
                confidence = "low"
                stats.step_counts["Step 3"] += 1

        # ── STEP 4: Default ───────────────────────────────────────────
        if result is None:
            result = "Conventional bicycle"
            step = "Step 4 (default)"
            confidence = "default"
            stats.step_counts["Step 4"] += 1

        # ── Determine confidence if not yet set ───────────────────────
        if confidence == "":
            if _undergrupp_agrees(result, sammanvagd_ug):
                confidence = "high"
            else:
                confidence = "medium"

        # ── Write results ─────────────────────────────────────────────
        df.at[idx, "Micromobility_type"] = result
        df.at[idx, "Classification_confidence"] = confidence
        df.at[idx, "Classification_step"] = step
        df.at[idx, "_all_matches"] = all_matches

    return df, stats


# ═══════════════════════════════════════════════════════════════════════════════
# Verification
# ═══════════════════════════════════════════════════════════════════════════════

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

    # CL.1 — electric classified without matching Undergrupp
    mismatch_2a = df_personer[
        df_personer["Micromobility_type"].isin(electric_types)
        & ~df_personer[COL_CATEGORY_SUB].isin(ELECTRIC_UNDERGRUPP)
    ][
        [
            COL_CRASH_ID,
            "Micromobility_type",
            COL_CATEGORY_SUB,
            "Classification_confidence",
            "Classification_step",
        ]
    ].copy()

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

    # CL.2 — conventional bicycle with electric Undergrupp
    mismatch_2b = df_personer[
        (df_personer["Micromobility_type"] == "Conventional bicycle")
        & df_personer[COL_CATEGORY_SUB].isin(ELECTRIC_UNDERGRUPP)
    ][
        [
            COL_CRASH_ID,
            "Micromobility_type",
            COL_CATEGORY_SUB,
            "Classification_confidence",
            "Classification_step",
        ]
    ].copy()

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
    multi = df_personer[
        df_personer["_all_matches"].apply(lambda x: len(x) > 1)
    ]
    multi_out = multi[
        [COL_CRASH_ID, "Micromobility_type", "_all_matches"]
    ].copy()

    return res_2a, res_2b, multi_out


# ═══════════════════════════════════════════════════════════════════════════════
# Public pipeline entry-point
# ═══════════════════════════════════════════════════════════════════════════════

def run_classification_pipeline(
    df_personer: pd.DataFrame,
) -> tuple[pd.DataFrame, list[VerificationResult], pd.DataFrame, ClassificationStats]:
    """Full classification pipeline.

    1. Classify micromobility types (4-step guarded).
    2. Verify classifications.

    Returns
    -------
    (df, verification_results, multi_matches, stats)
    """
    df, stats = classify_micromobility(df_personer)
    res_2a, res_2b, multi = verify_classification(df)

    # Clean up internal columns
    df.drop(
        columns=["_all_matches"],
        inplace=True,
        errors="ignore",
    )

    return df, [res_2a, res_2b], multi, stats
