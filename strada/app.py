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

from strada.core.verify import (
    CHECK_SEVERITY,
    QualityScore,
    compute_quality_score,
)
from strada.config.styles import inject_css

# ─────────────────────────────────────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="STRADA Data Quality Toolkit",
    page_icon="🛣️",
    layout="wide",
)

inject_css()

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
#  Verify-tab bundles & checks
# ─────────────────────────────────────────────────────────────────────────────

BUNDLES: dict[str, dict] = {
    "quick": {
        "name": "Quick scan",
        "icon": "",
        "description": "Fast sanity check. Runs the 3 essential identifier checks.",
        "checks": ["G1", "G2", "G3"],
        "checks_label": "G1, G2, G3",
        "runtime": "~6s",
        "recommended": True,
    },
    "full": {
        "name": "Full audit",
        "icon": "",
        "description": "All generic checks for a publication-ready dataset.",
        "checks": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "checks_label": "G1, G2, G3, G4, G5, G6",
        "runtime": "~18s",
    },
    "cycling": {
        "name": "Cycling audit",
        "icon": "🚲",
        "description": "Full audit plus the three cycling-specific structural checks.",
        "checks": ["G1", "G2", "G3", "G4", "G5", "G6", "C1", "C2", "C3"],
        "checks_label": "G1–G6 · C1, C2, C3",
        "runtime": "~24s",
    },
}

# (id, label) — severity tag ("C" critical / "W" warning) is derived from
# CHECK_SEVERITY in strada.core.verify (single source of truth).
_CHECK_LABELS: list[tuple[str, str]] = [
    ("G1", "Crash-ID consistency"),
    ("G2", "Crash-type consistency"),
    ("G3", "Road-user category"),
    ("G4", "Timeline consistency"),
    ("G5", "Location consistency"),
    ("G6", "Duplicate person"),
    ("C1", "Cykel singel validation"),
    ("C2", "Cykel presence"),
    ("C3", "Cykel passengers only"),
]
CHECKS: list[tuple[str, str, str]] = [
    (cid, label, "C" if CHECK_SEVERITY.get(cid) == "critical" else "W")
    for cid, label in _CHECK_LABELS
]


def _apply_bundle(bundle_id: str) -> None:
    """Apply a preset to the check checkboxes."""
    st.session_state.active_bundle = bundle_id
    wanted = set(BUNDLES[bundle_id]["checks"])
    for cid, _, _ in CHECKS:
        st.session_state[f"chk_{cid}"] = cid in wanted


def _on_check_toggle() -> None:
    """If the new check set matches a preset, snap to it; otherwise mark Custom."""
    current = {cid for cid, _, _ in CHECKS if st.session_state.get(f"chk_{cid}", False)}
    for bid, b in BUNDLES.items():
        if set(b["checks"]) == current:
            st.session_state.active_bundle = bid
            return
    st.session_state.active_bundle = "custom"


# ─────────────────────────────────────────────────────────────────────────────
#  Quality-score banner
# ─────────────────────────────────────────────────────────────────────────────

_GRADE_PILL_COLORS: dict[str, tuple[str, str]] = {
    # grade letter → (text color, background color)
    "A": ("#0e5e2c", "#d4f4dd"),
    "B": ("#8a5a00", "#fff3cd"),
    "C": ("#a04500", "#ffe4cc"),
    "D": ("#a02020", "#fcd5d5"),
    "F": ("#7a1414", "#f7c1c1"),
}


def _score_color(score: int) -> str:
    if score >= 90:
        return "#1f8a45"   # green
    if score >= 75:
        return "#c89020"   # amber
    if score >= 60:
        return "#d97706"   # orange
    if score >= 40:
        return "#dc2626"   # red
    return "#7c1c1c"       # dark red


def _render_quality_banner(qs: QualityScore) -> None:
    """Render the two-card overall-quality + per-category banner.

    Uses ``st.html`` (not ``st.markdown``) so the indented inner HTML doesn't
    get reinterpreted as Markdown code blocks. Right card uses Streamlit's
    theme variables so it adapts to light/dark themes.
    """
    text_col, bg_col = _GRADE_PILL_COLORS.get(qs.grade, ("#444", "#eee"))

    # Build category rows as a single inline string (no leading whitespace
    # per line, so even if rendering ever falls back to a markdown processor
    # we're safe).
    row_parts: list[str] = []
    for cat in qs.categories:
        head = (
            f'<div><span class="strada-cat-name">{cat.name}</span>'
            f' <code class="strada-cat-sub">{cat.sub_label}</code></div>'
        )
        if cat.score is None:
            row_parts.append(
                '<div class="strada-cat-row">'
                f'<div class="strada-cat-head">{head}'
                '<div class="strada-cat-pct strada-cat-na">&mdash;</div>'
                '</div>'
                '<div class="strada-bar-bg"></div>'
                '</div>'
            )
        else:
            color = _score_color(cat.score)
            row_parts.append(
                '<div class="strada-cat-row">'
                f'<div class="strada-cat-head">{head}'
                f'<div class="strada-cat-pct" style="color:{color};">{cat.score}%</div>'
                '</div>'
                '<div class="strada-bar-bg">'
                f'<div class="strada-bar-fill" style="width:{cat.score}%;background:{color};"></div>'
                '</div>'
                '</div>'
            )
    rows_html = "".join(row_parts)

    # Each sentence on its own line in the summary
    sentences = [s.strip() for s in qs.summary.split(". ") if s.strip()]
    sentences = [s if s.endswith(".") else s + "." for s in sentences]
    summary_html = "<br>".join(sentences) if sentences else qs.summary

    st.html(
        f"""
<div class="strada-score-grid">
<div class="strada-score-left">
<div class="strada-score-label">OVERALL DATA QUALITY</div>
<div class="strada-score-num"><span class="strada-score-big">{qs.overall}</span><span class="strada-score-tot">/ 100</span></div>
<div><span class="strada-grade-pill" style="background:{bg_col};color:{text_col};">GRADE {qs.grade} &middot; {qs.grade_label}</span></div>
<div class="strada-score-summary">{summary_html}</div>
</div>
<div class="strada-score-right">
<div class="strada-score-breakhead">Score breakdown</div>
{rows_html}
</div>
</div>
"""
    )


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
        st.caption("Pick a preset for common workflows or customize for full control.")

        # Initialise state once per session
        if "active_bundle" not in st.session_state:
            _apply_bundle("full")

        # ── Bundle preset cards ───────────────────────────────────────
        bcols = st.columns(3, gap="medium")
        for col, bid in zip(bcols, BUNDLES.keys()):
            b = BUNDLES[bid]
            is_active = st.session_state.active_bundle == bid
            with col:
                with st.container(border=True):
                    head_l, head_r = st.columns([3, 2])
                    with head_l:
                        title = f"{b['icon']} {b['name']}".strip()
                        st.markdown(f"#### {title}")
                    with head_r:
                        if is_active:
                            st.markdown(
                                "<div style='text-align:right;font-size:1.3em;color:#1f77b4'>✓</div>",
                                unsafe_allow_html=True,
                            )
                        elif b.get("recommended"):
                            st.markdown(
                                "<div style='text-align:right'><span style='background:#fff3cd;"
                                "color:#664d03;padding:2px 8px;border-radius:10px;"
                                "font-size:0.7em;font-weight:600;letter-spacing:0.5px'>"
                                "RECOMMENDED</span></div>",
                                unsafe_allow_html=True,
                            )

                    st.caption(b["description"])

                    meta_l, meta_r = st.columns(2)
                    with meta_l:
                        st.markdown(
                            f"<div style='font-size:0.7em;color:#888;letter-spacing:0.5px'>CHECKS</div>"
                            f"<div style='font-size:0.9em'>{b['checks_label']}</div>",
                            unsafe_allow_html=True,
                        )
                    with meta_r:
                        st.markdown(
                            f"<div style='font-size:0.7em;color:#888;letter-spacing:0.5px;text-align:right'>RUNTIME</div>"
                            f"<div style='font-size:0.9em;text-align:right'>{b['runtime']}</div>",
                            unsafe_allow_html=True,
                        )

                    st.button(
                        "✓ Selected" if is_active else "Select",
                        key=f"btn_bundle_{bid}",
                        on_click=_apply_bundle,
                        args=(bid,),
                        disabled=is_active,
                        type="primary" if is_active else "secondary",
                        use_container_width=True,
                    )

        # ── Customize checks (collapsible grid) ───────────────────────
        selected = [cid for cid, _, _ in CHECKS if st.session_state.get(f"chk_{cid}", False)]
        bundle_label = (
            "Custom"
            if st.session_state.active_bundle == "custom"
            else BUNDLES[st.session_state.active_bundle]["name"]
        )

        with st.expander(
            f"Customize checks  ·  {len(selected)} selected  ·  {bundle_label}",
            expanded=False,
        ):
            st.caption("Edits switch the bundle to *Custom*.")
            ccols = st.columns(3, gap="medium")
            for i, (cid, label, tag) in enumerate(CHECKS):
                with ccols[i % 3]:
                    tag_md = ":red[**C**]" if tag == "C" else ":orange[**W**]"
                    st.checkbox(
                        f"**{cid}** · {label} · {tag_md}",
                        key=f"chk_{cid}",
                        on_change=_on_check_toggle,
                    )

        include_cycling = any(c.startswith("C") for c in selected)

        # ── Ready-to-run banner ───────────────────────────────────────
        if st.session_state.active_bundle == "custom":
            runtime_est = f"~{max(3, len(selected) * 3)}s"
            display_label = "Custom"
        else:
            _b = BUNDLES[st.session_state.active_bundle]
            runtime_est = _b["runtime"]
            display_label = _b["name"]

        banner_l, banner_r = st.columns([4, 1.3], vertical_alignment="center", gap="small")
        with banner_l:
            checks_word = "check" if len(selected) == 1 else "checks"
            st.markdown(
                f"""
                <div class="strada-banner-text">
                  <div class="lbl">READY TO RUN</div>
                  <div class="ttl">{display_label} · {len(selected)} {checks_word} · est. {runtime_est}</div>
                </div>
                <div class="strada-banner-marker"></div>
                """,
                unsafe_allow_html=True,
            )
        with banner_r:
            run_clicked = st.button(
                "▶ Run verification",
                type="primary",
                key="btn_verify",
                disabled=len(selected) == 0,
                use_container_width=True,
            )

        if run_clicked:
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

            # ── Quality-score banner ──────────────────────────────────────
            quality = compute_quality_score(results)
            _render_quality_banner(quality)

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
        "**Conventional bicycle**, etc. and add a **Micromobility_type** column."
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
                df_out, verif_results, multi_matches, stats = run_classification_pipeline(df_cls)

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
    _generic_check_refs = [
        ("G1", "Crash-ID consistency between datasets",     "critical"),
        ("G2", "Crash-type (Olyckstyp) consistency",        "critical"),
        ("G3", "Road-user category (Trafikantkategori)",    "critical"),
        ("G4", "Crash timeline consistency (date & time)",  "warn"),
        ("G5", "Location consistency (Län / Kommun)",       "warn"),
        ("G6", "Duplicate person detection",                "warn"),
    ]
    _cycling_check_refs = [
        ("C1", "G1 (cykel singel) crash validation",        "critical"),
        ("C2", "Cykel presence in every crash",             "warn"),
        ("C3", "Cykel crashes with only passengers",        "warn"),
    ]

    def _ref_row(rid: str, name: str, desc: str) -> str:
        return (
            '<div class="strada-refrow">'
            f'<div class="strada-refrow-id">{rid}</div>'
            f'<div><div class="strada-refrow-name">{name}</div>'
            f'<div class="strada-refrow-desc">{desc}</div></div>'
            '</div>'
        )

    def _checks_table(rows: list[tuple[str, str, str]]) -> str:
        header = (
            '<div class="strada-ct-hdr">'
            '<div>ID</div><div>Check</div>'
            '<div class="strada-ct-sev-col">Severity</div>'
            '</div>'
        )
        body = "".join(
            '<div class="strada-ct-row">'
            f'<div class="strada-ct-id">{cid}</div>'
            f'<div class="strada-ct-desc">{desc}</div>'
            '<div class="strada-ct-sev-col">'
            f'<span class="strada-pill strada-pill-{"red" if sev == "critical" else "amber"}">'
            f'{sev.upper()}</span></div>'
            '</div>'
            for cid, desc, sev in rows
        )
        return f'<div class="strada-ct">{header}{body}</div>'

    def _link_card(title: str, sub: str, href: str) -> str:
        external = href.startswith("http")
        target_attr = ' target="_blank" rel="noopener noreferrer"' if external else ""
        return (
            f'<a class="strada-linkcard" href="{href}"{target_attr}>'
            f'<div class="strada-linkcard-title">{title}'
            '<span class="strada-linkcard-arrow">↗</span></div>'
            f'<div class="strada-linkcard-sub">{sub}</div>'
            '</a>'
        )

    _core_tables = (
        '<div class="strada-about-card">'
        '<div class="strada-about-sectitle">Core tables</div>'
        '<div class="strada-about-secsub">The two CSV exports this toolkit works with</div>'
        '<div class="strada-refrow-list">'
        f'{_ref_row("Olyckor",  "Crashes", "One row per crash event")}'
        f'{_ref_row("Personer", "Persons", "One row per person involved")}'
        '</div></div>'
    )
    _classify_card = (
        '<div class="strada-about-card">'
        '<div class="strada-about-sectitle">What gets added by Classify</div>'
        '<div class="strada-about-secsub">New column appended to Personer</div>'
        '<div class="strada-refrow-list">'
        f'{_ref_row("Micromobility_type", "Vehicle classification", "E-scooter, E-bike, Conventional bicycle, …")}'
        '</div></div>'
    )

    st.html(
        f"""
<div class="strada-about">
<section>
<div class="strada-about-eyebrow">About</div>
<div class="strada-about-title">STRADA Data Quality Toolkit</div>
<p class="strada-about-intro"><strong>STRADA</strong> (Swedish Traffic Accident Data Acquisition) is the national information system for road-traffic injuries managed by the Swedish Transport Agency (Transportstyrelsen). This toolkit provides automated data-quality checks plus micromobility classification helpers for STRADA exports.</p>
</section>
<div class="strada-about-grid2">
{_core_tables}
{_classify_card}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Generic checks</div>
<div class="strada-about-secsub">Apply to any STRADA analysis</div>
{_checks_table(_generic_check_refs)}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Cycling-specific checks</div>
<div class="strada-about-secsub">Enable when analysing cykel datasets</div>
{_checks_table(_cycling_check_refs)}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Resources</div>
<div class="strada-about-secsub">External references and documentation</div>
<div class="strada-grid2">
{_link_card("STRADA at Transportstyrelsen", "Official source documentation", "https://www.transportstyrelsen.se/strada")}
{_link_card("GitHub repository", "Source code, issues, releases", "https://github.com/Rahul-Pi/strada-toolbox")}
</div>
<div class="strada-footer">v1.0.0 · Chalmers University of Technology · Vehicle Safety · last updated May 2026</div>
</div>
</div>
"""
    )
