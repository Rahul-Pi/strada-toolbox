"""
STRADA Toolbox — Streamlit web dashboard.

Launch with::

    strada web                    # via CLI entry-point
    streamlit run strada/app.py   # directly

This dashboard provides a graphical interface for users who prefer not to
work with terminal commands.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="STRADA Data Quality Toolkit",
    page_icon="🛣️",
    layout="wide",
)

# Hide deploy button and menu items
st.markdown("""
    <style>
        .stAppDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)

st.title("🛣️ STRADA Data Quality Assessment Toolkit")
st.markdown(
    "Upload your **Olyckor** and **Personer** CSV files, select which checks "
    "to run, and download a data-quality report."
)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading CSV…")
def _load_df(uploaded_file) -> pd.DataFrame:
    """Read an uploaded CSV into a DataFrame."""
    return pd.read_csv(uploaded_file, encoding="utf-8-sig", low_memory=False)


# ─────────────────────────────────────────────────────────────────────────────
#  Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab_verify, tab_classify, tab_preprocess, tab_about = st.tabs([
    "🔍 Verify",
    "🚲 Classify (Cycling)",
    "📥 Preprocess",
    "ℹ️ About",
])


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — VERIFY
# ═══════════════════════════════════════════════════════════════════════════════

with tab_verify:
    st.header("Data Quality Verification")

    col_left, col_right = st.columns(2)
    with col_left:
        olyckor_file = st.file_uploader(
            "Upload **Olyckor** CSV", type=["csv"], key="verify_olyckor"
        )
    with col_right:
        personer_file = st.file_uploader(
            "Upload **Personer** CSV", type=["csv"], key="verify_personer"
        )

    if olyckor_file and personer_file:
        df_olyckor = _load_df(olyckor_file)
        df_personer = _load_df(personer_file)

        st.success(
            f"Loaded **{len(df_olyckor):,}** crashes and **{len(df_personer):,}** persons."
        )

        st.subheader("Select checks")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Generic checks**")
            run_g1 = st.checkbox("G1 — Crash-ID consistency", value=True)
            run_g2 = st.checkbox("G2 — Crash-type consistency", value=True)
            run_g3 = st.checkbox("G3 — Road-user category consistency", value=True)
            run_g4 = st.checkbox("G4 — Timeline consistency", value=True)
            run_g5 = st.checkbox("G5 — Location consistency", value=True)
            run_g6 = st.checkbox("G6 — Duplicate person detection", value=True)

        with col2:
            st.markdown("**Cycling-specific checks**")
            run_c1 = st.checkbox("C1 — G1 (cykel singel) validation", value=False)
            run_c2 = st.checkbox("C2 — Cykel presence", value=False)
            run_c3 = st.checkbox("C3 — Cykel passengers only", value=False)

        selected = []
        if run_g1: selected.append("G1")
        if run_g2: selected.append("G2")
        if run_g3: selected.append("G3")
        if run_g4: selected.append("G4")
        if run_g5: selected.append("G5")
        if run_g6: selected.append("G6")
        if run_c1: selected.append("C1")
        if run_c2: selected.append("C2")
        if run_c3: selected.append("C3")

        include_cycling = any(c.startswith("C") for c in selected)

        if st.button("▶ Run selected checks", type="primary", key="btn_verify"):
            from strada.core.verify import run_checks
            from strada.io.reporters import write_text_report, write_csv_report

            with st.spinner("Running verification checks…"):
                results = run_checks(
                    df_olyckor,
                    df_personer,
                    include_cycling=include_cycling,
                    checks=selected if selected else None,
                )

            # ── Summary table ─────────────────────────────────────────────
            st.subheader("Results")

            summary_rows = []
            for r in results:
                icon = {"pass": "✓", "warning": "⚠", "fail": "✗"}.get(r.status, "?")
                summary_rows.append({
                    "Check": r.check_id,
                    "Status": f"{icon} {r.status}",
                    "Issues": r.issue_count,
                    "Description": r.check_name,
                })
                for sub in r.sub_results:
                    sub_icon = {"pass": "✓", "warning": "⚠", "fail": "✗"}.get(sub.status, "?")
                    summary_rows.append({
                        "Check": f"  {sub.check_id}",
                        "Status": f"{sub_icon} {sub.status}",
                        "Issues": sub.issue_count,
                        "Description": sub.check_name,
                    })

            st.dataframe(
                pd.DataFrame(summary_rows),
                width='stretch',
                hide_index=True,
            )

            # ── Expandable details ────────────────────────────────────────
            all_res = []
            for r in results:
                all_res.append(r)
                all_res.extend(r.sub_results)

            for r in all_res:
                if r.details is not None and len(r.details) > 0:
                    with st.expander(
                        f"{r.check_id}: {r.check_name} — {len(r.details):,} issues"
                    ):
                        st.dataframe(r.details, width='stretch', hide_index=True)

            # ── Download buttons ──────────────────────────────────────────
            st.subheader("Download reports")
            dl1, dl2 = st.columns(2)

            with tempfile.TemporaryDirectory() as tmpdir:
                txt_path = write_text_report(
                    results,
                    Path(tmpdir) / "report.txt",
                    olyckor_count=len(df_olyckor),
                    personer_count=len(df_personer),
                )
                csv_path = write_csv_report(
                    results,
                    Path(tmpdir) / "report.csv",
                )

                with dl1:
                    st.download_button(
                        "📄 Download text report",
                        data=txt_path.read_text(encoding="utf-8"),
                        file_name="strada_quality_report.txt",
                        mime="text/plain",
                    )
                with dl2:
                    st.download_button(
                        "📊 Download CSV report",
                        data=csv_path.read_bytes(),
                        file_name="strada_quality_report.csv",
                        mime="text/csv",
                    )
    else:
        st.info("👆 Upload both CSV files to get started.")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — CLASSIFY (Cycling)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_classify:
    st.header("Micromobility Classification")
    st.markdown(
        "Classify Cykel entries into **E-scooter**, **E-bike**, "
        "**Conventional bicycle**, etc. and add a **Conflict partner** column."
    )

    personer_cls = st.file_uploader(
        "Upload **Personer** CSV", type=["csv"], key="classify_personer"
    )

    if personer_cls:
        df_cls = _load_df(personer_cls)
        st.success(f"Loaded **{len(df_cls):,}** person records.")

        if st.button("▶ Run classification", type="primary", key="btn_classify"):
            from strada.core.classify import run_classification_pipeline

            with st.spinner("Classifying…"):
                df_out, verif_results, multi_matches = run_classification_pipeline(df_cls)

            # Summary
            cykel = df_out[df_out["Micromobility_type"] != "N/A"]
            if len(cykel) > 0:
                st.subheader("Classification Summary")
                counts = cykel["Micromobility_type"].value_counts().reset_index()
                counts.columns = ["Type", "Count"]
                counts["Percentage"] = (counts["Count"] / counts["Count"].sum() * 100).round(1)
                st.dataframe(counts, width='stretch', hide_index=True)

            if len(multi_matches) > 0:
                with st.expander(f"⚠ {len(multi_matches)} entries with multiple category matches"):
                    st.dataframe(multi_matches, width='stretch', hide_index=True)

            for v in verif_results:
                icon = {"pass": "✓", "warning": "⚠"}.get(v.status, "?")
                if v.status == "pass":
                    st.success(f"{icon} {v.check_id}: {v.summary}")
                else:
                    st.warning(f"{icon} {v.check_id}: {v.summary}")
                    if v.details is not None:
                        with st.expander(f"Details for {v.check_id}"):
                            st.dataframe(v.details, width='stretch', hide_index=True)

            # Download
            csv_buf = io.BytesIO()
            df_out.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "📥 Download classified dataset",
                data=csv_buf.getvalue(),
                file_name="Personer-analysis-ready.csv",
                mime="text/csv",
            )
    else:
        st.info("👆 Upload a Personer CSV file to classify micromobility types.")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — PREPROCESS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_preprocess:
    st.header("Preprocess Excel → CSV")
    st.markdown(
        "Convert a STRADA Excel workbook into CSV files. "
        "Optionally filter by year range."
    )

    excel_file = st.file_uploader(
        "Upload STRADA **.xlsx** workbook", type=["xlsx"], key="preprocess_excel"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        olyckor_sheet = st.text_input("Olyckor sheet name", value="Olyckor")
    with col_b:
        personer_sheet = st.text_input("Personer sheet name", value="Personer")

    filter_years = st.checkbox("Filter by year range")
    if filter_years:
        cy, cy2 = st.columns(2)
        with cy:
            start_year = st.number_input("Start year", value=2016, min_value=1990, max_value=2100)
        with cy2:
            end_year = st.number_input("End year", value=2024, min_value=1990, max_value=2100)
    else:
        start_year = None
        end_year = None

    if excel_file:
        if st.button("▶ Convert", type="primary", key="btn_preprocess"):
            from strada.io.readers import load_excel_sheet, save_csv
            from strada.core.preprocess import filter_by_year

            with st.spinner("Reading Excel file…"):
                # Save uploaded file to temp location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(excel_file.read())
                    tmp_path = Path(tmp.name)

                df_o = load_excel_sheet(tmp_path, olyckor_sheet)
                df_p = load_excel_sheet(tmp_path, personer_sheet)

            st.success(
                f"Read **{len(df_o):,}** crashes and **{len(df_p):,}** persons."
            )

            downloads = {}

            # Full dataset
            buf_o = io.BytesIO()
            df_o.to_csv(buf_o, index=False, encoding="utf-8-sig")
            downloads["Olyckor.csv"] = buf_o.getvalue()

            buf_p = io.BytesIO()
            df_p.to_csv(buf_p, index=False, encoding="utf-8-sig")
            downloads["Personer.csv"] = buf_p.getvalue()

            if filter_years and start_year and end_year:
                df_o_f = filter_by_year(df_o, start_year, end_year)
                df_p_f = filter_by_year(df_p, start_year, end_year)

                st.info(
                    f"Filtered: **{len(df_o_f):,}** crashes, **{len(df_p_f):,}** persons "
                    f"({start_year}–{end_year})"
                )

                buf_of = io.BytesIO()
                df_o_f.to_csv(buf_of, index=False, encoding="utf-8-sig")
                downloads[f"Olyckor-{start_year}-{end_year}.csv"] = buf_of.getvalue()

                buf_pf = io.BytesIO()
                df_p_f.to_csv(buf_pf, index=False, encoding="utf-8-sig")
                downloads[f"Personer-{start_year}-{end_year}.csv"] = buf_pf.getvalue()

            st.subheader("Download converted files")
            cols = st.columns(len(downloads))
            for i, (name, data) in enumerate(downloads.items()):
                with cols[i]:
                    st.download_button(f"📥 {name}", data=data, file_name=name, mime="text/csv")
    else:
        st.info("👆 Upload a STRADA Excel workbook to get started.")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — ABOUT
# ═══════════════════════════════════════════════════════════════════════════════

with tab_about:
    st.header("About STRADA Toolbox")
    st.markdown("""
**STRADA** (Swedish Traffic Accident Data Acquisition) is a national information
system for road traffic injuries managed by the Swedish Transport Agency
(Transportstyrelsen).

### What this toolbox does

This toolkit provides automated data-quality checks for the two core STRADA
tables:

| Table | Description |
|-------|-------------|
| **Olyckor** (Crashes) | One row per crash event |
| **Personer** (Persons) | One row per person involved in a crash |

### Available checks

#### Generic (apply to any STRADA analysis)

| ID | Check |
|----|-------|
| **G1** | Crash-ID consistency between datasets |
| **G2** | Crash-type (Olyckstyp) consistency |
| **G3** | Road-user category (Trafikantkategori) consistency |
| **G4** | Crash timeline consistency (date & time) |
| **G5** | Location consistency (Län / Kommun) |
| **G6** | Duplicate person detection (all road-user types) |

#### Cycling-specific (enable with `--cycling` flag)

| ID | Check |
|----|-------|
| **C1** | G1 (cykel singel) crash validation |
| **C2** | Cykel presence in every crash |
| **C3** | Cykel crashes with only passengers (no driver) |

### Classification (cycling analysis)

The **Classify** tab / `strada classify` command adds:
- **Micromobility_type** — E-scooter, E-bike, Conventional bicycle, etc.
- **Conflict_partner** — Other road-user types involved in the same crash.

### Links

- [STRADA — Transportstyrelsen](https://www.transportstyrelsen.se/strada)
""")
