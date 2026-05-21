"""STRADA Toolbox — Streamlit dashboard CSS.

Centralised stylesheet for the dashboard. ``inject_css()`` is called once
near the top of ``app.py``; subsequent renders just produce widgets and
inline HTML that reference these classes.

The full stylesheet is split into four named string constants matching the
four logical sections of the dashboard. Search for the constant name to
jump to a section.
"""

from __future__ import annotations

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
#  1. App chrome — page-level overrides
# ─────────────────────────────────────────────────────────────────────────────

_CSS_CHROME = """
.stAppDeployButton { display: none; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  2. Quality-score banner
#     Rendered by render_quality_banner() in strada.web.components
# ─────────────────────────────────────────────────────────────────────────────

_CSS_QUALITY_BANNER = """
.strada-score-grid { display: grid; grid-template-columns: 1fr 2.3fr; gap: 16px; margin: 8px 0 24px 0; }
.strada-score-left { background: linear-gradient(135deg, #0a2540 0%, #0d2c4a 100%); color: #fff; border-radius: 12px; padding: 24px 28px; }
.strada-score-right { background: var(--secondary-background-color); border: 1px solid rgba(127, 127, 127, 0.2); border-radius: 12px; padding: 24px 28px; color: var(--text-color); }
.strada-score-label { font-size: 0.72em; color: #8ea4be; letter-spacing: 1.8px; font-weight: 700; }
.strada-score-num { margin: 10px 0 18px 0; line-height: 1; }
.strada-stars { display: inline-flex; align-items: center; vertical-align: middle; line-height: 1; margin-left: 4px; letter-spacing: 2px; }
.strada-grade-pill { display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 0.78em; font-weight: 700; letter-spacing: 0.5px; }
.strada-score-summary { margin-top: 18px; font-size: 0.92em; color: #cdd9e5; line-height: 1.5; }
.strada-score-breakhead { font-size: 1.05em; font-weight: 600; margin-bottom: 18px; color: var(--text-color); }
.strada-cat-row { margin-bottom: 16px; }
.strada-cat-row:last-child { margin-bottom: 0; }
.strada-cat-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.strada-cat-name { font-weight: 600; color: var(--text-color); }
.strada-cat-sub { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: rgba(127, 127, 127, 0.95); font-size: 0.82em; margin-left: 4px; background: rgba(127, 127, 127, 0.15); padding: 1px 6px; border-radius: 4px; }
.strada-cat-pct { font-weight: 700; font-size: 0.95em; }
.strada-cat-na { color: rgba(127, 127, 127, 0.7); }
.strada-bar-bg { background: rgba(127, 127, 127, 0.18); border-radius: 4px; height: 6px; overflow: hidden; }
.strada-bar-fill { height: 100%; border-radius: 4px; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  3. Ready-to-run banner
#     Rendered above the Run-verification button on the Verify tab.
# ─────────────────────────────────────────────────────────────────────────────

_CSS_READY_BANNER = """
/* Paint the whole columns row navy when it contains our marker */
div[data-testid="stHorizontalBlock"]:has(.strada-banner-marker) {
    background: #0a2540;
    border-radius: 10px;
    padding: 14px 22px;
    margin-top: 16px;
    align-items: center;
}
/* Tint the primary button inside the banner to cyan */
div[data-testid="stHorizontalBlock"]:has(.strada-banner-marker)
    button[data-testid="stBaseButton-primary"] {
    background: #29b6f6 !important;
    border: 1px solid #29b6f6 !important;
    color: #ffffff !important;
}
div[data-testid="stHorizontalBlock"]:has(.strada-banner-marker)
    button[data-testid="stBaseButton-primary"]:hover {
    background: #0288d1 !important;
    border-color: #0288d1 !important;
}
div[data-testid="stHorizontalBlock"]:has(.strada-banner-marker)
    button[data-testid="stBaseButton-primary"]:disabled {
    background: #2c4a6a !important;
    border-color: #2c4a6a !important;
    color: #8ea4be !important;
}
.strada-banner-text .lbl {
    font-size: 0.7em;
    color: #8ea4be;
    letter-spacing: 1.5px;
    font-weight: 700;
}
.strada-banner-text .ttl {
    font-size: 1.05em;
    font-weight: 600;
    margin-bottom: 10px;
    color: #e6edf5;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  4. About tab
#     Rendered by render_about_html() in strada.web.components
# ─────────────────────────────────────────────────────────────────────────────

_CSS_ABOUT = """
.strada-about { display: flex; flex-direction: column; gap: 22px; max-width: 1100px; padding: 8px 0 32px 0; }
.strada-about-eyebrow { font-size: 0.72em; color: rgba(127, 127, 127, 0.85); font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase; }
.strada-about-title { font-size: 1.7em; font-weight: 600; color: var(--text-color); letter-spacing: -0.3px; margin: 4px 0 0 0; padding: 0; }
.strada-about-intro { font-size: 0.95em; color: rgba(127, 127, 127, 0.95); margin: 10px 0 0 0; line-height: 1.6; }
.strada-about-intro strong { color: var(--text-color); }
.strada-about-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.strada-about-card { background: var(--secondary-background-color); border: 1px solid rgba(127, 127, 127, 0.18); border-radius: 12px; padding: 22px; }
.strada-about-sectitle { font-size: 1.05em; font-weight: 600; color: var(--text-color); }
.strada-about-secsub { font-size: 0.82em; color: rgba(127, 127, 127, 0.8); margin: 2px 0 14px 0; }

.strada-refrow-list { display: flex; flex-direction: column; gap: 10px; }
.strada-refrow { padding: 12px 14px; border: 1px solid rgba(127, 127, 127, 0.18); border-radius: 6px; display: grid; grid-template-columns: 180px 1fr; align-items: center; gap: 14px; }
/* Cyan ID pill (matches the Run-verification button) — readable on both light and dark theme */
.strada-refrow-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.78em; font-weight: 600; color: #ffffff; background: #29b6f6; padding: 3px 8px; border-radius: 4px; justify-self: start; }
.strada-refrow-name { font-size: 0.88em; font-weight: 500; color: var(--text-color); }
.strada-refrow-desc { font-size: 0.78em; color: rgba(127, 127, 127, 0.85); margin-top: 2px; }

.strada-ct { border: 1px solid rgba(127, 127, 127, 0.18); border-radius: 8px; overflow: hidden; }
.strada-ct-hdr { display: grid; grid-template-columns: 60px 1fr 110px; padding: 10px 16px; background: rgba(127, 127, 127, 0.08); font-size: 0.68em; letter-spacing: 0.8px; text-transform: uppercase; color: rgba(127, 127, 127, 0.85); font-weight: 600; border-bottom: 1px solid rgba(127, 127, 127, 0.18); }
.strada-ct-hdr .strada-ct-sev-col { text-align: right; }
.strada-ct-row { display: grid; grid-template-columns: 60px 1fr 110px; padding: 11px 16px; align-items: center; }
.strada-ct-row + .strada-ct-row { border-top: 1px solid rgba(127, 127, 127, 0.12); }
.strada-ct-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82em; color: rgba(127, 127, 127, 0.95); font-weight: 600; }
.strada-ct-desc { font-size: 0.88em; color: var(--text-color); }
.strada-ct-sev-col { text-align: right; }

.strada-pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.68em; font-weight: 700; letter-spacing: 0.4px; }
.strada-pill-red { background: rgba(220, 38, 38, 0.16); color: #b91c1c; }
.strada-pill-amber { background: rgba(200, 144, 32, 0.20); color: #8a5a00; }

.strada-grid2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.strada-linkcard { display: block; padding: 14px; border: 1px solid rgba(127, 127, 127, 0.18); border-radius: 8px; text-decoration: none; transition: border-color 0.12s ease, transform 0.12s ease; }
.strada-linkcard:hover { border-color: rgba(10, 37, 64, 0.45); transform: translateY(-1px); }
.strada-linkcard-title { font-size: 0.92em; font-weight: 600; color: #0a5fb4; display: flex; align-items: center; justify-content: space-between; }
.strada-linkcard-arrow { font-size: 0.78em; color: rgba(127, 127, 127, 0.7); }
.strada-linkcard-sub { font-size: 0.82em; color: rgba(127, 127, 127, 0.85); margin-top: 4px; }

.strada-footer { margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(127, 127, 127, 0.18); font-size: 0.78em; color: rgba(127, 127, 127, 0.8); }
"""


_CSS = f"<style>{_CSS_CHROME}{_CSS_QUALITY_BANNER}{_CSS_READY_BANNER}{_CSS_ABOUT}</style>"


def inject_css() -> None:
    """Inject all dashboard CSS. Call once near app startup."""
    st.html(_CSS)
