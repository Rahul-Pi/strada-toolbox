"""
STRADA verification — registry, runner, and quality scoring.

This module is the public API for data-quality verification. It exposes:

  - ``CHECK_SPECS``         — registry of all checks (single source of truth)
  - ``CHECK_SEVERITY``      — derived ``{check_id: severity}`` lookup
  - ``SCORE_CATEGORIES``    — derived ``{category_name: {checks, sub_label}}``
  - ``run_checks(...)``     — execute a selection of checks
  - ``compute_quality_score(results)`` — compute overall 0–100 score
  - ``QualityScore``, ``CategoryScore`` dataclasses

The check functions themselves live in :mod:`strada.core.checks` — to add a
new check, define the function there and add a :class:`CheckSpec` entry to
``CHECK_SPECS`` below. Everything downstream (severity lookup, generic-vs-
cycling grouping, score category grouping, app-side checkbox labels, About-tab
references) derives from this one list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

import pandas as pd

from strada.core.checks import (
    CHECK_SEVERITY,
    check_c1_cykel_singel,
    check_c2_cykel_presence,
    check_c3_cykel_passengers_only,
    check_g1_id_consistency,
    check_g2_crash_type,
    check_g3_road_user_category,
    check_g4_timeline,
    check_g5_location,
    check_g6_duplicate_persons,
)
from strada.io.reporters import VerificationResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  REGISTRY                                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

CheckFunc = Callable[[Optional[pd.DataFrame], pd.DataFrame], VerificationResult]


@dataclass(frozen=True)
class CheckSpec:
    """Metadata for a single data-quality check.

    To add a new check: define a ``check_*`` function in ``strada.core.checks``,
    add its severity to ``CHECK_SEVERITY`` there, then append a ``CheckSpec``
    to ``CHECK_SPECS`` below.
    """
    id: str                                       # "G1", "C2", ...
    name: str                                     # short label used everywhere
    description: str                              # longer text for the About tab
    severity: Literal["critical", "non-critical"]
    category: str                                 # CATEGORY_META key
    family: Literal["generic", "cycling"]
    func: CheckFunc
    denominator: Literal["olyckor", "personer"] = "olyckor"


CHECK_SPECS: list[CheckSpec] = [
    CheckSpec(
        id="G1",
        name="Crash-ID inconsistency",
        description="Every Olycksnummer should appear in both Olyckor and Personer.",
        severity=CHECK_SEVERITY["G1"],
        category="identifier",
        family="generic",
        func=check_g1_id_consistency,
        denominator="olyckor",
    ),
    CheckSpec(
        id="G2",
        name="Crash-type inconsistency",
        description="Olyckstyp should be filled and consistent between Olyckor and Personer.",
        severity=CHECK_SEVERITY["G2"],
        category="identifier",
        family="generic",
        func=check_g2_crash_type,
        denominator="olyckor",
    ),
    CheckSpec(
        id="G3",
        name="Road-user category inconsistency",
        description="Road-user category should be filled and consistent across the police (P), hospital (S), and combined (Sammanvägd) columns.",
        severity=CHECK_SEVERITY["G3"],
        category="identifier",
        family="generic",
        func=check_g3_road_user_category,
        denominator="personer",
    ),
    CheckSpec(
        id="G4",
        name="Crash time/date inconsistency",
        description="All persons in the same crash should report the same date and hour bucket.",
        severity=CHECK_SEVERITY["G4"],
        category="temporal_spatial",
        family="generic",
        func=check_g4_timeline,
        denominator="olyckor",
    ),
    CheckSpec(
        id="G5",
        name="Crash location inconsistency",
        description="All persons in the same crash should report the same Län and Kommun.",
        severity=CHECK_SEVERITY["G5"],
        category="temporal_spatial",
        family="generic",
        func=check_g5_location,
        denominator="olyckor",
    ),
    CheckSpec(
        id="G6",
        name="Duplicate person detection",
        description="Detect potential duplicate persons appearing under different crash IDs (matched on demographics, time, place, and road-user type).",
        severity=CHECK_SEVERITY["G6"],
        category="duplicates",
        family="generic",
        func=check_g6_duplicate_persons,
        denominator="personer",
    ),
    CheckSpec(
        id="C1",
        name="Single cyclist crash validation",
        description="Crashes coded as single cyclist should contain exactly one person, recorded as a cyclist.",
        severity=CHECK_SEVERITY["C1"],
        category="cycling_structure",
        family="cycling",
        func=check_c1_cykel_singel,
        denominator="olyckor",  # approx: true scope is single-cyclist crashes only
    ),
    CheckSpec(
        id="C2",
        name="Cyclist presence in every crash",
        description="Every crash in a cycling-filtered dataset should include at least one cyclist.",
        severity=CHECK_SEVERITY["C2"],
        category="cycling_structure",
        family="cycling",
        func=check_c2_cykel_presence,
        denominator="olyckor",
    ),
    CheckSpec(
        id="C3",
        name="Cyclist (driver) missing in crash",
        description="Cyclist crashes should record the cyclist (driver), not only passengers.",
        severity=CHECK_SEVERITY["C3"],
        category="cycling_structure",
        family="cycling",
        func=check_c3_cykel_passengers_only,
        denominator="olyckor",  # approx: true scope is cyclist crashes only
    ),
]


# ── Score-category display metadata ──
#
# Order here determines display order in the Quality-Score banner. The
# em-dash range in the cycling sub_label ("C1–C3") is presentation-only and
# can't be auto-derived, so this metadata is kept explicit.

CATEGORY_META: dict[str, tuple[str, str]] = {
    "identifier":         ("Identifier integrity", "G1, G2, G3"),
    "temporal_spatial":   ("Temporal & spatial",   "G4, G5"),
    "duplicates":         ("Duplicates",           "G6"),
    "cycling_structure":  ("Cycling structure",    "C1–C3"),
}


# ── Derived lookups (consumed by app.py, internal helpers, and scoring) ──

#: ``{category_name: {"checks": [...], "sub_label": "..."}}`` — derived from
#: ``CHECK_SPECS`` grouped by ``spec.category`` plus ``CATEGORY_META``.
SCORE_CATEGORIES: dict[str, dict] = {
    display_name: {
        "checks": [s.id for s in CHECK_SPECS if s.category == cat_key],
        "sub_label": sub_label,
    }
    for cat_key, (display_name, sub_label) in CATEGORY_META.items()
}


def _specs_for_family(family: str) -> list[CheckSpec]:
    return [s for s in CHECK_SPECS if s.family == family]


# Lists of bare functions, kept for any code that wants to iterate them
# directly (most callers should go through ``run_checks``).
GENERIC_CHECKS: list[CheckFunc] = [s.func for s in _specs_for_family("generic")]
CYCLING_CHECKS: list[CheckFunc] = [s.func for s in _specs_for_family("cycling")]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  RUNNER                                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


def run_checks(
    df_olyckor: pd.DataFrame,
    df_personer: pd.DataFrame,
    *,
    include_cycling: bool = False,
    checks: list[str] | None = None,
) -> list[VerificationResult]:
    """Run selected verification checks.

    Parameters
    ----------
    df_olyckor, df_personer : pd.DataFrame
    include_cycling : bool
        If ``True``, cycling-specific checks (C1–C3) are also run.
    checks : list[str], optional
        Run only checks whose ``check_id`` appears in this list
        (e.g. ``["G1", "G4", "C2"]``). If ``None``, run all applicable.

    Returns
    -------
    list[VerificationResult]
    """
    results = []
    for spec in CHECK_SPECS:
        if spec.family == "cycling" and not include_cycling:
            continue
        if checks is not None and spec.id not in checks:
            continue
        result = spec.func(df_olyckor, df_personer)
        result.check_name = spec.name   # single source of truth for parent names
        results.append(result)
    return results


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  QUALITY SCORING                                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Scoring model — additive per-failing-check penalties
# ----------------------------------------------------
# Each failing check (issue_count > 0) deducts a severity-based base penalty
# plus a rate-dependent term:
#
#   critical:      deduction = CRITICAL_BASE_PENALTY + CRITICAL_RATE_PENALTY * sqrt(rate)
#   non-critical:  deduction = NONCRIT_BASE_PENALTY  + NONCRIT_RATE_PENALTY  * sqrt(rate)
#
# Deductions accumulate: overall = max(0, 100 - sum of all deductions).
#
# This means "more failing checks → lower score" holds, and the rate term
# keeps scores comparable across datasets of different sizes (the same
# issue rate yields the same deduction regardless of total row count).
#
# Sub-checks do NOT get an individual deduction — their issues are already
# rolled up into the parent's issue_count by the check functions.
#
# Checks that were not run are excluded entirely (no penalty, no credit).
# Category sub-scores apply the same additive deduction, restricted to the
# category's checks, with an up-scaling factor when only a subset ran.


# Tunable scoring constants — adjust here after observing real datasets.
CRITICAL_BASE_PENALTY = 10.0   # flat deduction for any failing critical check
CRITICAL_RATE_PENALTY = 30.0   # additional rate-dependent deduction for critical checks
NONCRIT_BASE_PENALTY  = 5.0    # flat deduction for any failing non-critical check
NONCRIT_RATE_PENALTY  = 30.0   # additional rate-dependent deduction for non-critical checks


GRADE_THRESHOLDS: list[tuple[int, str, str]] = [
    (90, "A", "EXCELLENT"),
    (75, "B", "ACCEPTABLE"),
    (60, "C", "NEEDS WORK"),
    (40, "D", "POOR"),
    ( 0, "F", "FAILING"),
]


def _grade_for(score: int) -> tuple[str, str]:
    for threshold, letter, label in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter, label
    return "F", "FAILING"


@dataclass
class CategoryScore:
    name: str
    sub_label: str
    score: Optional[int]          # None = not run
    check_ids: list[str] = field(default_factory=list)


@dataclass
class QualityScore:
    overall: int                  # 0-100
    grade: str                    # A/B/C/D/F
    grade_label: str              # EXCELLENT / ACCEPTABLE / ...
    categories: list[CategoryScore] = field(default_factory=list)
    critical_count: int = 0       # total critical issues
    warning_count: int = 0        # total non-critical issues
    pass_count: int = 0           # checks with 0 issues
    critical_checks_failed: int = 0
    summary: str = ""


#: Spec lookup by id — built once, used by the scoring helpers below.
_SPEC_BY_ID: dict[str, CheckSpec] = {s.id: s for s in CHECK_SPECS}


def _denominator_for(spec: CheckSpec, n_olyckor: int, n_personer: int) -> int:
    return n_olyckor if spec.denominator == "olyckor" else n_personer


def _deduction_for(spec: CheckSpec, issue_count: int, denominator: int) -> float:
    """Deduction for a single failing check; 0 if it passes."""
    if denominator <= 0 or issue_count <= 0:
        return 0.0
    rate = min(issue_count / denominator, 1.0)
    if spec.severity == "critical":
        return CRITICAL_BASE_PENALTY + CRITICAL_RATE_PENALTY * math.sqrt(rate)
    return NONCRIT_BASE_PENALTY + NONCRIT_RATE_PENALTY * math.sqrt(rate)


def compute_quality_score(
    results: list[VerificationResult],
    *,
    n_olyckor: int,
    n_personer: int,
) -> QualityScore:
    """Compute overall quality score and per-category breakdown.

    ``results`` is the list of parent-level results returned by ``run_checks``.
    Sub-results are read from each result's ``sub_results`` list; their issue
    counts are already rolled up into the parent.

    ``n_olyckor`` / ``n_personer`` are the dataset row counts; they form the
    denominator for the rate-based per-check scoring.
    """
    result_map: dict[str, VerificationResult] = {r.check_id: r for r in results}
    ran_ids = set(result_map.keys())

    # ── Per-check deductions ──
    deductions: dict[str, float] = {}
    critical_count = 0
    warning_count = 0
    pass_count = 0
    critical_failed = 0

    for r in results:
        spec = _SPEC_BY_ID.get(r.check_id)
        if spec is None:
            continue
        denom = _denominator_for(spec, n_olyckor, n_personer)
        deductions[r.check_id] = _deduction_for(spec, r.issue_count, denom)

        if r.issue_count == 0:
            pass_count += 1
        elif spec.severity == "critical":
            critical_count += r.issue_count
            critical_failed += 1
        else:
            warning_count += r.issue_count

    # ── Overall: straight accumulation of deductions ──
    total_deduction = sum(deductions.values())
    overall = max(0, min(100, round(100 - total_deduction)))
    grade, grade_label = _grade_for(overall)

    # ── Category sub-scores (same additive deduction, restricted) ──
    categories: list[CategoryScore] = []
    for cat_name, cat_info in SCORE_CATEGORIES.items():
        cat_check_ids = cat_info["checks"]
        cat_ran = [cid for cid in cat_check_ids if cid in ran_ids]

        if not cat_ran:
            categories.append(CategoryScore(
                name=cat_name,
                sub_label=cat_info["sub_label"] + " · not run",
                score=None,
                check_ids=cat_check_ids,
            ))
            continue

        cat_ded = sum(deductions[cid] for cid in cat_ran)
        # Up-scale deduction if only a subset of category checks ran
        scale = len(cat_check_ids) / len(cat_ran) if len(cat_ran) < len(cat_check_ids) else 1.0
        cat_score = max(0, min(100, round(100 - cat_ded * scale)))

        categories.append(CategoryScore(
            name=cat_name,
            sub_label=cat_info["sub_label"],
            score=cat_score,
            check_ids=cat_check_ids,
        ))

    # ── Summary text ──
    parts = []
    if critical_failed > 0:
        noun = "check" if critical_failed == 1 else "checks"
        parts.append(f"{critical_failed} critical {noun} failed")
    w_checks = sum(
        1 for r in results
        if r.issue_count > 0 and CHECK_SEVERITY.get(r.check_id) != "critical"
    )
    if w_checks > 0:
        noun = "check" if w_checks == 1 else "checks"
        parts.append(f"{w_checks} non-critical {noun} failed")

    if not parts:
        summary = "All checks passed. Dataset is publication-ready."
    else:
        summary = "Some inconsistencies need review before publication. " + ". ".join(parts) + "."

    return QualityScore(
        overall=overall,
        grade=grade,
        grade_label=grade_label,
        categories=categories,
        critical_count=critical_count,
        warning_count=warning_count,
        pass_count=pass_count,
        critical_checks_failed=critical_failed,
        summary=summary,
    )
