"""
HTML builders for the Streamlit dashboard.

Pure functions: each returns an HTML string. No ``st.*`` calls live here —
the dashboard layer (``strada/app.py``) wraps these outputs in ``st.html(...)``.
Keeping the builders Streamlit-free makes them trivially callable from any
context.
"""

from __future__ import annotations

from strada.core.verify import CheckSpec, QualityScore


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


def render_quality_banner_html(qs: QualityScore) -> str:
    """Return the HTML for the two-card overall-quality + per-category banner.

    Uses inline-only HTML (no leading whitespace per line) so a markdown
    fallback renderer never re-interprets it as code blocks.
    """
    text_col, bg_col = _GRADE_PILL_COLORS.get(qs.grade, ("#444", "#eee"))

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

    sentences = [s.strip() for s in qs.summary.split(". ") if s.strip()]
    sentences = [s if s.endswith(".") else s + "." for s in sentences]
    summary_html = "<br>".join(sentences) if sentences else qs.summary

    return f"""
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


# ─────────────────────────────────────────────────────────────────────────────
#  Ready-to-run banner (Verify tab)
# ─────────────────────────────────────────────────────────────────────────────

def render_ready_banner_html(display_label: str, n_checks: int, runtime_est: str) -> str:
    """Return the HTML for the navy 'READY TO RUN' banner content."""
    checks_word = "check" if n_checks == 1 else "checks"
    return (
        '<div class="strada-banner-text">'
        '<div class="lbl">READY TO RUN</div>'
        f'<div class="ttl">{display_label} · {n_checks} {checks_word} · est. {runtime_est}</div>'
        '</div>'
        '<div class="strada-banner-marker"></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
#  About tab
# ─────────────────────────────────────────────────────────────────────────────

def _ref_row(rid: str, name: str, desc: str) -> str:
    return (
        '<div class="strada-refrow">'
        f'<div class="strada-refrow-id">{rid}</div>'
        f'<div><div class="strada-refrow-name">{name}</div>'
        f'<div class="strada-refrow-desc">{desc}</div></div>'
        '</div>'
    )


def _checks_table(specs: list[CheckSpec]) -> str:
    header = (
        '<div class="strada-ct-hdr">'
        '<div>ID</div><div>Check</div>'
        '<div class="strada-ct-sev-col">Severity</div>'
        '</div>'
    )
    body = "".join(
        '<div class="strada-ct-row">'
        f'<div class="strada-ct-id">{s.id}</div>'
        f'<div class="strada-ct-desc">{s.description}</div>'
        '<div class="strada-ct-sev-col">'
        f'<span class="strada-pill strada-pill-{"red" if s.severity == "critical" else "amber"}">'
        f'{s.severity.upper()}</span></div>'
        '</div>'
        for s in specs
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


def render_about_html(
    generic_specs: list[CheckSpec],
    cycling_specs: list[CheckSpec],
    *,
    version: str,
    last_updated: str,
) -> str:
    """Return the full HTML body for the About tab."""
    core_tables = (
        '<div class="strada-about-card">'
        '<div class="strada-about-sectitle">Core tables</div>'
        '<div class="strada-about-secsub">The two CSV exports this toolkit works with</div>'
        '<div class="strada-refrow-list">'
        f'{_ref_row("Olyckor",  "Crashes", "One row per crash event")}'
        f'{_ref_row("Personer", "Persons", "One row per person involved")}'
        '</div></div>'
    )
    classify_card = (
        '<div class="strada-about-card">'
        '<div class="strada-about-sectitle">What gets added by Classify</div>'
        '<div class="strada-about-secsub">New column appended to Personer</div>'
        '<div class="strada-refrow-list">'
        f'{_ref_row("Micromobility_type", "Vehicle classification", "E-scooter, E-bike, Conventional bicycle, …")}'
        '</div></div>'
    )

    return f"""
<div class="strada-about">
<section>
<div class="strada-about-eyebrow">About</div>
<div class="strada-about-title">STRADA Data Quality Toolkit</div>
<p class="strada-about-intro"><strong>STRADA</strong> (Swedish Traffic Accident Data Acquisition) is the national information system for road-traffic injuries managed by the Swedish Transport Agency (Transportstyrelsen). This toolkit provides automated data-quality checks plus micromobility classification helpers for STRADA exports.</p>
</section>
<div class="strada-about-grid2">
{core_tables}
{classify_card}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Generic checks</div>
<div class="strada-about-secsub">Apply to any STRADA analysis</div>
{_checks_table(generic_specs)}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Cycling-specific checks</div>
<div class="strada-about-secsub">Enable when analysing cykel datasets</div>
{_checks_table(cycling_specs)}
</div>
<div class="strada-about-card">
<div class="strada-about-sectitle">Resources</div>
<div class="strada-about-secsub">External references and documentation</div>
<div class="strada-grid2">
{_link_card("STRADA at Transportstyrelsen", "Official source documentation", "https://www.transportstyrelsen.se/strada")}
{_link_card("GitHub repository", "Source code, issues, releases", "https://github.com/Rahul-Pi/strada-toolbox")}
</div>
<div class="strada-footer">v{version} · Chalmers University of Technology · Vehicle Safety · last updated {last_updated}</div>
</div>
</div>
"""
