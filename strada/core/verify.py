"""
Data-quality verification checks for STRADA datasets.

This module provides **generic** checks (G1–G6) that apply to any STRADA
analysis, and **cycling-specific** checks (C1–C3) that are relevant only when
the dataset is filtered to cycling / micromobility crashes.

Every public ``check_*`` function follows the same contract:

    Parameters
    ----------
    df_olyckor : pd.DataFrame   (crashes table — may be ``None`` for some checks)
    df_personer : pd.DataFrame  (persons table)

    Returns
    -------
    VerificationResult
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from strada.config.constants import (
    COL_CRASH_ID,
    COL_CRASH_TYPE,
    COL_YEAR,
    COL_MONTH,
    COL_DAY,
    COL_TIME,
    COL_AGE,
    COL_GENDER,
    COL_COUNTY,
    COL_MUNICIPALITY,
    COL_STREET,
    COL_CATEGORY_MAIN,
    COL_CATEGORY_SUB,
    COL_CATEGORY_P,
    COL_CATEGORY_S,
    COL_ROLE_P,
    COL_ROLE_S,
    CYKEL_CATEGORY,
    G1_CRASH_TYPE,
    GENDER_UNKNOWN,
    PASSENGER_ROLES,
    DUPLICATE_DETECTION_COLS,
)
from strada.io.reporters import VerificationResult


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  GENERIC CHECKS  (G1 – G6)                                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


def check_g1_id_consistency(
    df_olyckor: pd.DataFrame,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G1 — Crash-ID consistency** between Olyckor and Personer.

    Verifies that every ``Olycksnummer`` in Olyckor has at least one
    corresponding row in Personer and vice-versa.
    """
    olyckor_ids = set(df_olyckor[COL_CRASH_ID].unique())
    personer_ids = set(df_personer[COL_CRASH_ID].unique())

    olyckor_only = sorted(olyckor_ids - personer_ids)
    personer_only = sorted(personer_ids - olyckor_ids)

    rows = []
    for cid in olyckor_only:
        rows.append({"Olycksnummer": cid, "Found_in": "Olyckor only"})
    for cid in personer_only:
        rows.append({"Olycksnummer": cid, "Found_in": "Personer only"})

    details = pd.DataFrame(rows) if rows else None
    n_issues = len(rows)

    if n_issues == 0:
        summary = (
            f"✓ All Olycksnummer match perfectly. "
            f"Total unique crashes: {len(olyckor_ids):,}"
        )
        status = "pass"
    else:
        summary = (
            f"⚠ {len(olyckor_only)} in Olyckor only, "
            f"{len(personer_only)} in Personer only"
        )
        status = "warning"

    return VerificationResult(
        check_id="G1",
        check_name="Crash-ID (Olycksnummer) consistency",
        status=status,
        summary=summary,
        issue_count=n_issues,
        details=details,
    )


def check_g2_crash_type(
    df_olyckor: pd.DataFrame,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G2 — Crash-type (Olyckstyp) consistency**.

    Three sub-checks:
      * G2.1  Missing Olyckstyp in either dataset.
      * G2.2  Olyckstyp mismatch between Olyckor and Personer for the same
              crash ID.
    """
    sub_results = []

    # --- G2.1 — missing values ---
    def _is_empty(s):
        return s.isna() | (s.astype(str).str.strip() == "")

    missing_o = df_olyckor[_is_empty(df_olyckor[COL_CRASH_TYPE])]
    missing_p = df_personer[_is_empty(df_personer[COL_CRASH_TYPE])]
    missing_p_crashes = missing_p[COL_CRASH_ID].unique()

    n_missing = len(missing_o) + len(missing_p_crashes)
    if n_missing == 0:
        sub1_summary = "✓ All records have Olyckstyp filled"
    else:
        sub1_summary = (
            f"⚠ Missing in Olyckor: {len(missing_o)}, "
            f"Missing in Personer (unique crashes): {len(missing_p_crashes)}"
        )
    rows_missing = []
    for cid in missing_o[COL_CRASH_ID].values:
        rows_missing.append({"Olycksnummer": cid, "Source": "Olyckor"})
    for cid in missing_p_crashes:
        rows_missing.append({"Olycksnummer": cid, "Source": "Personer"})

    sub_results.append(VerificationResult(
        check_id="G2.1",
        check_name="Missing Olyckstyp",
        status="pass" if n_missing == 0 else "warning",
        summary=sub1_summary,
        issue_count=n_missing,
        details=pd.DataFrame(rows_missing) if rows_missing else None,
    ))

    # --- G2.2 — mismatch between datasets ---
    # Take one Olyckstyp per crash from Personer (they should all agree)
    personer_types = (
        df_personer[[COL_CRASH_ID, COL_CRASH_TYPE]]
        .drop_duplicates(COL_CRASH_ID)
    )
    merged = df_olyckor[[COL_CRASH_ID, COL_CRASH_TYPE]].merge(
        personer_types,
        on=COL_CRASH_ID,
        suffixes=("_olyckor", "_personer"),
    )
    col_o = f"{COL_CRASH_TYPE}_olyckor"
    col_p = f"{COL_CRASH_TYPE}_personer"
    mismatched = merged[merged[col_o] != merged[col_p]].copy()
    mismatched = mismatched.rename(columns={
        col_o: "Olyckstyp_Olyckor",
        col_p: "Olyckstyp_Personer",
    })

    if len(mismatched) == 0:
        sub2_summary = "✓ All Olyckstyp values match between datasets"
    else:
        sub2_summary = f"⚠ {len(mismatched)} crashes with mismatched Olyckstyp"

    sub_results.append(VerificationResult(
        check_id="G2.2",
        check_name="Olyckstyp mismatch between datasets",
        status="pass" if len(mismatched) == 0 else "warning",
        summary=sub2_summary,
        issue_count=len(mismatched),
        details=mismatched[[COL_CRASH_ID, "Olyckstyp_Olyckor", "Olyckstyp_Personer"]] if len(mismatched) > 0 else None,
    ))

    # --- aggregate ---
    total_issues = sum(s.issue_count for s in sub_results)
    return VerificationResult(
        check_id="G2",
        check_name="Crash-type (Olyckstyp) consistency",
        status="pass" if total_issues == 0 else "warning",
        summary=f"{total_issues} total issues across sub-checks",
        issue_count=total_issues,
        sub_results=sub_results,
    )


def check_g3_road_user_category(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G3 — Road-user category (Trafikantkategori) consistency** in Personer.

    Sub-checks:
      * G3.1  All three category columns missing.
      * G3.2  P ≠ S when both filled.
      * G3.3  Filled P/S ≠ Sammanvägd.
      * G3.4  Neither P nor S matches Sammanvägd when both filled.
    """
    sub_results = []
    col_p = COL_CATEGORY_P
    col_s = COL_CATEGORY_S
    col_sam = COL_CATEGORY_SUB

    def _empty(series):
        return series.isna() | (series.astype(str).str.strip() == "")

    # --- G3.1 — all three missing ---
    all_missing = df_personer[_empty(df_personer[col_p]) & _empty(df_personer[col_s]) & _empty(df_personer[col_sam])]
    n31 = len(all_missing)
    details31 = all_missing[[COL_CRASH_ID]].drop_duplicates() if n31 > 0 else None
    sub_results.append(VerificationResult(
        check_id="G3.1",
        check_name="All three Trafikantkategori columns missing",
        status="pass" if n31 == 0 else "warning",
        summary=f"{'✓ All persons have at least one Trafikantkategori column filled' if n31 == 0 else f'⚠ {n31} persons with all three columns missing'}",
        issue_count=n31,
        details=details31,
    ))

    # --- G3.2 — P ≠ S when both filled ---
    both_filled = df_personer[~_empty(df_personer[col_p]) & ~_empty(df_personer[col_s])]
    if len(both_filled) > 0:
        mismatched_ps = both_filled[both_filled[col_p] != both_filled[col_s]]
    else:
        mismatched_ps = pd.DataFrame()
    n32 = len(mismatched_ps)
    details32 = mismatched_ps[[COL_CRASH_ID, col_p, col_s]].copy() if n32 > 0 else None
    sub_results.append(VerificationResult(
        check_id="G3.2",
        check_name="P and S categories mismatch when both filled",
        status="pass" if n32 == 0 else "warning",
        summary=(
            f"✓ All {len(both_filled)} persons with both P and S filled have matching values"
            if n32 == 0
            else f"⚠ {n32} persons where P ≠ S"
        ),
        issue_count=n32,
        details=details32,
    ))

    # --- G3.3 — filled P or S ≠ Sammanvägd ---
    # Exclude rows already flagged in G3.2
    if n32 > 0:
        df_check = df_personer.drop(mismatched_ps.index)
    else:
        df_check = df_personer

    # Get the "effective" category: P if available, else S
    eff_cat = df_check[col_p].where(~_empty(df_check[col_p]), df_check[col_s])
    has_eff = ~_empty(eff_cat)
    has_sam = ~_empty(df_check[col_sam])
    comparable = df_check[has_eff & has_sam].copy()
    comparable["_eff"] = eff_cat[has_eff & has_sam]

    # Smart match: exact OR eff starts with sam
    exact_match = comparable["_eff"] == comparable[col_sam]
    prefix_match = comparable["_eff"].astype(str).apply(
        lambda x: any(x.startswith(str(s)) for s in comparable[col_sam])
    )
    # Vectorised prefix match
    prefix_match = comparable.apply(
        lambda row: str(row["_eff"]).startswith(str(row[col_sam])), axis=1
    )
    mismatch_33 = comparable[~exact_match & ~prefix_match].copy()
    mismatch_33 = mismatch_33[[COL_CRASH_ID, "_eff", col_sam]].rename(
        columns={"_eff": "Filled_category"}
    )
    n33 = len(mismatch_33)
    sub_results.append(VerificationResult(
        check_id="G3.3",
        check_name="Filled P/S ≠ Sammanvägd",
        status="pass" if n33 == 0 else "warning",
        summary=(
            "✓ All filled P/S categories match Sammanvägd"
            if n33 == 0
            else f"⚠ {n33} discrepancies between filled category and Sammanvägd"
        ),
        issue_count=n33,
        details=mismatch_33 if n33 > 0 else None,
    ))

    # --- G3.4 — neither P nor S matches Sammanvägd when both filled ---
    rows_34 = []
    if len(both_filled) > 0:
        bf = both_filled.copy()
        bf_sam = bf[~_empty(bf[col_sam])].copy()
        if len(bf_sam) > 0:
            p_exact = bf_sam[col_p] == bf_sam[col_sam]
            s_exact = bf_sam[col_s] == bf_sam[col_sam]
            p_prefix = bf_sam.apply(lambda r: str(r[col_p]).startswith(str(r[col_sam])), axis=1)
            s_prefix = bf_sam.apply(lambda r: str(r[col_s]).startswith(str(r[col_sam])), axis=1)
            neither = ~(p_exact | s_exact | p_prefix | s_prefix)
            mismatch_34 = bf_sam[neither][[COL_CRASH_ID, col_p, col_s, col_sam]].copy()
        else:
            mismatch_34 = pd.DataFrame()
    else:
        mismatch_34 = pd.DataFrame()

    n34 = len(mismatch_34)
    sub_results.append(VerificationResult(
        check_id="G3.4",
        check_name="Neither P nor S matches Sammanvägd (both filled)",
        status="pass" if n34 == 0 else "warning",
        summary=(
            "✓ At least one of P/S matches Sammanvägd in all cases"
            if n34 == 0
            else f"⚠ {n34} cases where neither P nor S matches Sammanvägd"
        ),
        issue_count=n34,
        details=mismatch_34 if n34 > 0 else None,
    ))

    total = sum(s.issue_count for s in sub_results)
    return VerificationResult(
        check_id="G3",
        check_name="Road-user category (Trafikantkategori) consistency",
        status="pass" if total == 0 else "warning",
        summary=f"{total} total issues across sub-checks",
        issue_count=total,
        sub_results=sub_results,
    )


def check_g4_timeline(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G4 — Crash timeline consistency** within each crash.

    For each ``Olycksnummer`` with multiple person entries, checks that
    ``År``, ``Månad``, ``Dag`` are identical and that ``Klockslag grupp (timme)``
    is identical.  Date mismatches are reported first, then time mismatches
    sorted by the magnitude of the difference.
    """
    date_cols = [COL_YEAR, COL_MONTH, COL_DAY]

    # Only look at multi-person crashes
    counts = df_personer.groupby(COL_CRASH_ID).size()
    multi = counts[counts > 1].index
    df_multi = df_personer[df_personer[COL_CRASH_ID].isin(multi)]

    # Date uniqueness per crash
    date_nuniq = df_multi.groupby(COL_CRASH_ID)[date_cols].nunique()
    date_bad_mask = (date_nuniq > 1).any(axis=1)
    date_bad_ids = date_nuniq[date_bad_mask].index

    # Time uniqueness per crash (only for crashes with consistent dates)
    time_nuniq = df_multi.groupby(COL_CRASH_ID)[COL_TIME].nunique()
    time_bad_mask = (time_nuniq > 1) & ~time_nuniq.index.isin(date_bad_ids)
    time_bad_ids = time_nuniq[time_bad_mask].index

    rows = []
    for cid in date_bad_ids:
        crash = df_multi[df_multi[COL_CRASH_ID] == cid]
        dates = crash[date_cols].drop_duplicates()
        vals = [f"{r[COL_YEAR]}-{r[COL_MONTH]}-{r[COL_DAY]}" for _, r in dates.iterrows()]
        rows.append({
            "Olycksnummer": cid,
            "Reason": "Date mismatch",
            "Details": ", ".join(vals),
        })

    # Time issues — compute difference for sorting
    time_rows = []
    for cid in time_bad_ids:
        crash = df_multi[df_multi[COL_CRASH_ID] == cid]
        times = crash[COL_TIME].dropna().unique()
        try:
            nums = [float(t) for t in times]
            diff = max(nums) - min(nums)
        except (ValueError, TypeError):
            diff = 0
        time_rows.append({
            "Olycksnummer": cid,
            "Reason": "Time mismatch",
            "Details": ", ".join(str(t) for t in times),
            "_diff": diff,
        })
    time_rows.sort(key=lambda x: x["_diff"], reverse=True)
    for r in time_rows:
        r.pop("_diff")
    rows.extend(time_rows)

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)
    n_date = len(date_bad_ids)
    n_time = len(time_bad_ids)

    if n == 0:
        summary = "✓ All crashes have consistent date and time"
    else:
        summary = f"⚠ {n_date} date mismatches, {n_time} time mismatches"

    return VerificationResult(
        check_id="G4",
        check_name="Crash timeline consistency",
        status="pass" if n == 0 else "warning",
        summary=summary,
        issue_count=n,
        details=details,
    )


def check_g5_location(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G5 — Location consistency** (Län / Kommun) within each crash."""
    counts = df_personer.groupby(COL_CRASH_ID).size()
    multi = counts[counts > 1].index
    df_multi = df_personer[df_personer[COL_CRASH_ID].isin(multi)]

    lan_nuniq = df_multi.groupby(COL_CRASH_ID)[COL_COUNTY].nunique()
    kom_nuniq = df_multi.groupby(COL_CRASH_ID)[COL_MUNICIPALITY].nunique()

    lan_bad = set(lan_nuniq[lan_nuniq > 1].index)
    kom_bad = set(kom_nuniq[kom_nuniq > 1].index)
    all_bad = lan_bad | kom_bad

    rows = []
    for cid in sorted(all_bad):
        crash = df_multi[df_multi[COL_CRASH_ID] == cid]
        reasons = []
        details_parts = []
        if cid in lan_bad:
            reasons.append("Län mismatch")
            vals = crash[COL_COUNTY].dropna().unique()
            details_parts.append(f"Län: {', '.join(str(v) for v in vals)}")
        if cid in kom_bad:
            reasons.append("Kommun mismatch")
            vals = crash[COL_MUNICIPALITY].dropna().unique()
            details_parts.append(f"Kommun: {', '.join(str(v) for v in vals)}")
        rows.append({
            "Olycksnummer": cid,
            "Reason": ", ".join(reasons),
            "Details": "; ".join(details_parts),
        })

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)

    return VerificationResult(
        check_id="G5",
        check_name="Location consistency (Län / Kommun)",
        status="pass" if n == 0 else "warning",
        summary=(
            "✓ All crashes have consistent location"
            if n == 0
            else f"⚠ {n} crashes with location inconsistencies"
        ),
        issue_count=n,
        details=details,
    )


def check_g6_duplicate_persons(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**G6 — Potential duplicate persons** across different crashes.

    Groups persons by demographics + road-user type + date/time/location.
    If the same combination appears in multiple different crashes, it is
    flagged as a potential duplicate.  Rows with missing age or unknown
    gender (``Uppgift saknas``) are excluded.
    """
    dup_cols = DUPLICATE_DETECTION_COLS

    # Check that all columns exist
    missing_cols = [c for c in dup_cols if c not in df_personer.columns]
    if missing_cols:
        return VerificationResult(
            check_id="G6",
            check_name="Duplicate person detection",
            status="fail",
            summary=f"✗ Missing columns: {missing_cols}",
            issue_count=0,
        )

    df_dup = df_personer.copy()
    for col in dup_cols:
        df_dup[col] = df_dup[col].fillna("").astype(str)

    # Exclude unknowns
    df_dup = df_dup[
        (df_dup[COL_AGE] != "")
        & (df_dup[COL_GENDER] != "")
        & (df_dup[COL_GENDER].str.lower() != GENDER_UNKNOWN.lower())
    ]

    grouped = df_dup.groupby(dup_cols)

    rows = []
    for name, group in grouped:
        unique_crashes = group[COL_CRASH_ID].unique()
        if len(unique_crashes) > 1:
            info = dict(zip(dup_cols, name))
            rows.append({
                "Olycksnummer": ", ".join(str(c) for c in sorted(unique_crashes)),
                "Num_crashes": len(unique_crashes),
                "Num_entries": len(group),
                "Age": info.get(COL_AGE, ""),
                "Gender": info.get(COL_GENDER, ""),
                "Date": f"{info.get(COL_YEAR, '')}-{info.get(COL_MONTH, '')}-{info.get(COL_DAY, '')}",
                "Time": info.get(COL_TIME, ""),
                "County": info.get(COL_COUNTY, ""),
                "Municipality": info.get(COL_MUNICIPALITY, ""),
                "Street": info.get(COL_STREET, ""),
                "Road_user_type": info.get(COL_CATEGORY_MAIN, ""),
            })

    # Sort by number of crashes descending
    rows.sort(key=lambda x: x["Num_crashes"], reverse=True)

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)

    return VerificationResult(
        check_id="G6",
        check_name="Duplicate person detection (all road-user types)",
        status="pass" if n == 0 else "warning",
        summary=(
            "✓ No potential duplicate persons found"
            if n == 0
            else f"⚠ {n} potential duplicate-person groups across different crashes"
        ),
        issue_count=n,
        details=details,
    )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  CYCLING-SPECIFIC CHECKS  (C1 – C3)                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


def check_c1_g1_single_cyclist(
    df_olyckor: pd.DataFrame,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**C1 — G1 (cykel singel) crash validation**.

    For crashes typed ``G1 (cykel singel)``:
      - There should be exactly one person entry.
      - That entry should have ``Huvudgrupp == 'Cykel'``.

    When multiple persons exist, passengers are counted via the keyword
    ``Passagerare`` in the role columns.
    """
    g1_ids = df_olyckor.loc[
        df_olyckor[COL_CRASH_TYPE] == G1_CRASH_TYPE, COL_CRASH_ID
    ].unique()
    g1_persons = df_personer[df_personer[COL_CRASH_ID].isin(g1_ids)]
    person_counts = g1_persons.groupby(COL_CRASH_ID).size()

    rows = []

    # Multi-person G1 crashes
    multi_ids = person_counts[person_counts > 1].index
    for cid in multi_ids:
        grp = g1_persons[g1_persons[COL_CRASH_ID] == cid]
        n_persons = len(grp)
        # Count passengers
        p_roles = grp[COL_ROLE_P].fillna("").str.lower()
        s_roles = grp[COL_ROLE_S].fillna("").str.lower()
        n_passengers = int(
            (p_roles.str.contains("passagerare") | s_roles.str.contains("passagerare")).sum()
        )
        if n_passengers > 0:
            reason = f"Multiple entries ({n_persons} persons, {n_passengers} passengers)"
        else:
            reason = f"Multiple entries ({n_persons} persons)"
        rows.append({"Olycksnummer": cid, "Reason": reason})

    # Single-person but not Cykel
    single_ids = person_counts[person_counts == 1].index
    single = g1_persons[g1_persons[COL_CRASH_ID].isin(single_ids)]
    not_cykel = single[single[COL_CATEGORY_MAIN] != CYKEL_CATEGORY]
    for _, r in not_cykel.iterrows():
        rows.append({
            "Olycksnummer": r[COL_CRASH_ID],
            "Reason": f"Single entry but not Cykel (is: {r[COL_CATEGORY_MAIN]})",
        })

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)

    return VerificationResult(
        check_id="C1",
        check_name="G1 (cykel singel) crash validation",
        status="pass" if n == 0 else "warning",
        summary=(
            f"✓ All {len(g1_ids)} G1 crashes have exactly one Cykel entry"
            if n == 0
            else f"⚠ {n} G1 crashes with issues"
        ),
        issue_count=n,
        details=details,
    )


def check_c2_cykel_presence(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**C2 — Cykel presence** in every crash.

    Verifies that each ``Olycksnummer`` has at least one person with
    ``Huvudgrupp == 'Cykel'``.
    """
    has_cykel = df_personer.groupby(COL_CRASH_ID)[COL_CATEGORY_MAIN].apply(
        lambda g: (g == CYKEL_CATEGORY).any()
    )
    missing_ids = has_cykel[~has_cykel].index

    rows = []
    for cid in missing_ids:
        grp = df_personer[df_personer[COL_CRASH_ID] == cid]
        cats = grp[COL_CATEGORY_MAIN].dropna().unique().tolist()
        rows.append({
            "Olycksnummer": cid,
            "Huvudgrupp_values": ", ".join(str(v) for v in cats) if cats else "No values",
        })

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)

    return VerificationResult(
        check_id="C2",
        check_name="Cykel presence in every crash",
        status="pass" if n == 0 else "warning",
        summary=(
            f"✓ All {len(has_cykel)} crashes have at least one Cykel entry"
            if n == 0
            else f"⚠ {n} crashes without any Cykel entry"
        ),
        issue_count=n,
        details=details,
    )


def check_c3_cykel_passengers_only(
    df_olyckor: pd.DataFrame | None,
    df_personer: pd.DataFrame,
) -> VerificationResult:
    """**C3 — Cykel crashes with only passengers, no driver**.

    Flags crashes where *every* Cykel entry has a passenger role
    (``Passagerare bak``, ``Passagerare fram``, etc.) and none is a
    driver / cyclist.
    """
    cykel = df_personer[df_personer[COL_CATEGORY_MAIN] == CYKEL_CATEGORY].copy()

    if len(cykel) == 0:
        return VerificationResult(
            check_id="C3",
            check_name="Cykel crashes with only passengers (no driver)",
            status="pass",
            summary="No Cykel entries in dataset",
            issue_count=0,
        )

    cykel["_is_pax"] = False
    for role in PASSENGER_ROLES:
        cykel["_is_pax"] |= cykel[COL_ROLE_P].fillna("").str.contains(role, na=False)
        cykel["_is_pax"] |= cykel[COL_ROLE_S].fillna("").str.contains(role, na=False)

    agg = cykel.groupby(COL_CRASH_ID)["_is_pax"].agg(["all", "sum", "count"])
    agg.columns = ["all_pax", "n_pax", "n_cykel"]
    only_pax = agg[agg["all_pax"]]

    rows = [
        {"Olycksnummer": cid, "Num_passengers": int(r["n_pax"])}
        for cid, r in only_pax.iterrows()
    ]

    details = pd.DataFrame(rows) if rows else None
    n = len(rows)

    return VerificationResult(
        check_id="C3",
        check_name="Cykel crashes with only passengers (no driver)",
        status="pass" if n == 0 else "warning",
        summary=(
            f"✓ All Cykel crashes have at least one driver/cyclist"
            if n == 0
            else f"⚠ {n} Cykel crashes with only passengers"
        ),
        issue_count=n,
        details=details,
    )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  RUNNER                                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Registry of checks
GENERIC_CHECKS = [
    check_g1_id_consistency,
    check_g2_crash_type,
    check_g3_road_user_category,
    check_g4_timeline,
    check_g5_location,
    check_g6_duplicate_persons,
]

CYCLING_CHECKS = [
    check_c1_g1_single_cyclist,
    check_c2_cykel_presence,
    check_c3_cykel_passengers_only,
]


def run_checks(
    df_olyckor: pd.DataFrame,
    df_personer: pd.DataFrame,
    *,
    include_cycling: bool = False,
    checks: list[str] | None = None,
) -> list[VerificationResult]:
    """Run selected verification checks and return results.

    Parameters
    ----------
    df_olyckor : pd.DataFrame
    df_personer : pd.DataFrame
    include_cycling : bool
        If ``True``, cycling-specific checks (C1–C3) are also run.
    checks : list[str], optional
        Run only checks whose ``check_id`` appears in this list
        (e.g. ``["G1", "G4", "C2"]``).  If ``None``, run all applicable.

    Returns
    -------
    list[VerificationResult]
    """
    all_funcs = list(GENERIC_CHECKS)
    if include_cycling:
        all_funcs.extend(CYCLING_CHECKS)

    results = []
    for func in all_funcs:
        # Determine check_id from the function (convention: last part of name)
        # We'll just run it and check the result's id
        result = func(df_olyckor, df_personer)
        if checks is None or result.check_id in checks:
            results.append(result)

    return results
