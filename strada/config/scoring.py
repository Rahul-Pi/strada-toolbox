"""
Quality score computation for STRADA verification results.

Scoring model
-------------
Start at 100 and deduct for each check that has issues.

  deduction = BASE_PENALTY + min(issue_count * PER_ISSUE_RATE, MAX_CAP)
  if critical: deduction *= CRITICAL_MULT

Sub-checks do NOT get an individual base_penalty — their issues are
already rolled up into the parent's issue_count by the verify backend.

Checks that were not run are excluded entirely (no penalty, no credit).

Category sub-scores use the same formula, applied independently to the
checks in each category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from strada.io.reporters import VerificationResult


# ── Severity mapping ──

CHECK_SEVERITY: dict[str, str] = {
    "G1": "critical",
    "G2": "critical",
    "G3": "non-critical",
    "G4": "non-critical",
    "G5": "non-critical",
    "G6": "non-critical",
    "C1": "non-critical",
    "C2": "critical",
    "C3": "non-critical",
}

# ── Weights ──

BASE_PENALTY   = 3.0
PER_ISSUE_RATE = 0.02
MAX_CAP        = 12.0
CRITICAL_MULT  = 2.0

# ── Grade thresholds ──

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


# ── Category grouping ──

SCORE_CATEGORIES: dict[str, dict] = {
    "Identifier integrity": {
        "checks": ["G1", "G2", "G3"],
        "sub_label": "G1, G2, G3",
    },
    "Temporal & spatial": {
        "checks": ["G4", "G5"],
        "sub_label": "G4, G5",
    },
    "Duplicates": {
        "checks": ["G6"],
        "sub_label": "G6",
    },
    "Cycling structure": {
        "checks": ["C1", "C2", "C3"],
        "sub_label": "C1\u2013C3",
    },
}


# ── Result containers ──

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


# ── Core computation ──

def _deduction_for(check_id: str, issue_count: int) -> float:
    """Compute deduction for a single parent-level check."""
    if issue_count == 0:
        return 0.0
    raw = BASE_PENALTY + min(issue_count * PER_ISSUE_RATE, MAX_CAP)
    if CHECK_SEVERITY.get(check_id) == "critical":
        raw *= CRITICAL_MULT
    return raw


def compute_quality_score(results: list[VerificationResult]) -> QualityScore:
    """Compute overall quality score and per-category breakdown.

    Parameters
    ----------
    results : list[VerificationResult]
        Parent-level results only (G1, G2, ...).  Sub-results are read
        from each result's sub_results list; their issue counts are
        already rolled up into the parent.
    """
    result_map: dict[str, VerificationResult] = {r.check_id: r for r in results}
    ran_ids = set(result_map.keys())

    # ── Overall score ──
    total_deduction = 0.0
    critical_count = 0
    warning_count = 0
    pass_count = 0
    critical_failed = 0

    for r in results:
        ded = _deduction_for(r.check_id, r.issue_count)
        total_deduction += ded

        if r.issue_count == 0:
            pass_count += 1
        elif CHECK_SEVERITY.get(r.check_id) == "critical":
            critical_count += r.issue_count
            critical_failed += 1
        else:
            warning_count += r.issue_count

    overall = max(0, min(100, round(100 - total_deduction)))
    grade, grade_label = _grade_for(overall)

    # ── Category sub-scores ──
    categories: list[CategoryScore] = []
    for cat_name, cat_info in SCORE_CATEGORIES.items():
        cat_check_ids = cat_info["checks"]
        cat_ran = [cid for cid in cat_check_ids if cid in ran_ids]

        if not cat_ran:
            categories.append(CategoryScore(
                name=cat_name,
                sub_label=cat_info["sub_label"] + " \u00b7 not run",
                score=None,
                check_ids=cat_check_ids,
            ))
            continue

        cat_ded = sum(_deduction_for(cid, result_map[cid].issue_count) for cid in cat_ran)
        # Scale if only a subset of checks in the category were run
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
        parts.append(str(critical_failed) + " critical " + noun + " failed")
    w_checks = sum(
        1 for r in results
        if r.issue_count > 0 and CHECK_SEVERITY.get(r.check_id) != "critical"
    )
    if w_checks > 0:
        noun = "check" if w_checks == 1 else "checks"
        parts.append(str(w_checks) + " " + noun + " need attention")

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
