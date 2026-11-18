"""
Results dashboard.

Self-contained: draws every results section from one AnalysisResponse dict.
It reads the same fields the old component files read, so the backend is
untouched. HTML strings are flush-left with no blank lines on purpose, because
Streamlit treats blank lines and 4-space indents as markdown.
"""
import html
from typing import Any, Dict, List

import streamlit as st

# Max score per component (matches backend/core/config.py SCORE_WEIGHTS).
COMPONENTS = [
    ("Formatting", "formatting", 20),
    ("Keywords and skills", "keywords", 25),
    ("Content quality", "content", 25),
    ("Skill validation", "skill_validation", 15),
    ("ATS compatibility", "ats_compatibility", 15),
]

SEVERITY_ORDER = ["critical", "high", "moderate", "medium", "low"]
SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITY_ORDER)}
TIER_LABEL = {"good": "Strong", "fair": "Fair", "poor": "Needs work"}


# ---------- small helpers ----------

def _e(value: Any) -> str:
    """Escape text for HTML. '$' is escaped so Streamlit doesn't treat it as math."""
    if value is None:
        return ""
    return html.escape(str(value)).replace("$", "&#36;")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tier(fraction: float) -> str:
    if fraction >= 0.8:
        return "good"
    if fraction >= 0.6:
        return "fair"
    return "poor"


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _heading(title: str, sub: str = "") -> None:
    sub_html = f'<p class="res-sub">{_e(sub)}</p>' if sub else ""
    _html(f'<h2 class="res-h">{_e(title)}</h2>{sub_html}')


def _list_html(items: List[str], risk: bool = False, scroll: bool = False) -> str:
    cls = "dotlist" + (" risk" if risk else "") + (" scrollbox" if scroll else "")
    lis = "".join(f"<li>{_e(i)}</li>" for i in items)
    return f'<ul class="{cls}">{lis}</ul>'


def _chips_html(items: List[str], kind: str) -> str:
    return '<div class="chips">' + "".join(f'<span class="chip {kind}">{_e(i)}</span>' for i in items) + "</div>"


# ---------- sections ----------

def _overall_score(analysis: Dict[str, Any]) -> None:
    score = _num(analysis.get("ATS_score", analysis.get("ats_score", 0)))
    tier = _tier(score / 100.0)
    interpretation = _e(analysis.get("interpretation", ""))
    _html(
        f'<div class="rcard score-hero tier-{tier}">'
        f'<div class="ring" style="--p:{score:.0f}"><div class="ring-inner">'
        f'<span class="ring-num">{score:.0f}</span><span class="ring-of">out of 100</span>'
        f'</div></div>'
        f'<div><span class="chip tier-chip">{TIER_LABEL[tier]}</span>'
        f'<h3 class="score-title">Overall ATS score</h3>'
        f'<p class="score-interp">{interpretation}</p></div>'
        f'</div>'
    )


def _score_breakdown(analysis: Dict[str, Any]) -> None:
    component_scores = analysis.get("component_scores") or {}
    _heading("Score breakdown", "Each part is scored on its own scale, so you can see where points were lost.")
    rows = []
    for label, key, max_score in COMPONENTS:
        value = _num(component_scores.get(key, 0))
        frac = min(max(value / max_score, 0.0), 1.0) if max_score else 0.0
        tier = _tier(frac)
        rows.append(
            f'<div class="brow"><span class="brow-label">{_e(label)}</span>'
            f'<div class="bar tier-{tier}"><i style="width:{frac * 100:.0f}%"></i></div>'
            f'<span class="brow-val">{value:.0f} / {max_score}</span></div>'
        )
    _html('<div class="rcard">' + "".join(rows) + "</div>")


def _strengths_and_issues(analysis: Dict[str, Any]) -> None:
    strengths = analysis.get("strengths") or []
    critical = analysis.get("critical_issues") or []
    summary = analysis.get("issues_summary") or []

    _heading("Strengths and critical issues")
    left, right = st.columns(2, gap="large")

    with left:
        if strengths:
            body = _list_html(strengths)
        else:
            body = '<p class="empty">No standout strengths yet. Work through the actions below to build them.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Strengths</div>{body}</div>')

    with right:
        if critical:
            body = _list_html(critical, risk=True)
        else:
            body = '<p class="empty">No critical issues found. Nothing urgent is holding your score back.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Critical issues</div>{body}</div>')

    extra = [s for s in summary if s not in critical]
    if extra:
        with st.expander(f"Additional flagged items ({len(extra)})"):
            _html(_list_html(extra, risk=True))


def _skill_validation(analysis: Dict[str, Any]) -> None:
    details = analysis.get("skill_validation_details") or {}
    validated = details.get("validated", []) or []
    unvalidated = details.get("unvalidated", []) or []
    total = int(_num(details.get("total", len(validated) + len(unvalidated))))
    pct = _num(details.get("validation_pct", 0.0))

    _heading("Skill validation", "Listed skills are checked against the projects and experience on your resume.")

    if total == 0:
        st.info("No skills were detected on the resume.")
        return

    frac = min(max(pct / 100.0, 0.0), 1.0)
    tier = _tier(frac)
    _html(
        f'<div class="stats">'
        f'<div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Skills found</div></div>'
        f'<div class="stat"><div class="stat-num">{len(validated)}</div><div class="stat-label">Backed by experience</div></div>'
        f'<div class="stat tier-{tier}"><div class="stat-num">{pct:.0f}%</div><div class="stat-label">Validation rate</div>'
        f'<div class="bar tier-{tier}" style="margin-top:.6rem"><i style="width:{frac * 100:.0f}%"></i></div></div>'
        f'</div>'
    )

    left, right = st.columns(2, gap="large")

    with left:
        if validated:
            rows = []
            for entry in validated:
                skill = _e(entry.get("skill", "?"))
                projects = entry.get("projects", []) or []
                where = ", ".join(_e(p) for p in projects[:3]) if projects else "Experience section"
                similarity = entry.get("similarity")
                chip = (
                    f'<span class="chip ok">{similarity * 100:.0f}% match</span>'
                    if isinstance(similarity, (int, float)) else ""
                )
                rows.append(
                    f'<div class="vrow"><div><b>{skill}</b><span class="vrow-sub">{where}</span></div>{chip}</div>'
                )
            body = '<div class="scrollbox">' + "".join(rows) + "</div>"
        else:
            body = '<p class="empty">None of your listed skills are tied to a project or role yet.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Backed by experience ({len(validated)})</div>{body}</div>')

    with right:
        if unvalidated:
            body = (
                '<p class="empty" style="margin-top:0">Listed, but not tied to a project or experience bullet.</p>'
                + _chips_html([str(s) for s in unvalidated], "warn")
            )
        else:
            body = '<p class="empty">Every listed skill is backed by your experience.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Not backed up ({len(unvalidated)})</div>{body}</div>')


def _jd_match(jd: Dict[str, Any]) -> None:
    match_pct = _num(jd.get("match_percentage", 0))
    semantic = _num(jd.get("semantic_similarity", 0))
    matched = jd.get("matched_keywords", []) or []
    missing = jd.get("missing_keywords", []) or []
    gap = jd.get("skills_gap", []) or []

    _heading("Job description match", "How closely this resume lines up with the role you provided.")

    mt = _tier(match_pct / 100.0)
    st_ = _tier(semantic)
    _html(
        f'<div class="stats two">'
        f'<div class="stat tier-{mt}"><div class="stat-num">{match_pct:.0f}%</div><div class="stat-label">Keyword match</div>'
        f'<div class="bar tier-{mt}" style="margin-top:.6rem"><i style="width:{min(max(match_pct, 0), 100):.0f}%"></i></div></div>'
        f'<div class="stat tier-{st_}"><div class="stat-num">{semantic * 100:.0f}%</div><div class="stat-label">Semantic similarity</div>'
        f'<div class="bar tier-{st_}" style="margin-top:.6rem"><i style="width:{min(max(semantic, 0), 1) * 100:.0f}%"></i></div></div>'
        f'</div>'
    )

    left, right = st.columns(2, gap="large")
    with left:
        body = _chips_html([str(k) for k in matched[:20]], "ok") if matched else '<p class="empty">No keywords matched yet.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Matched keywords</div>{body}</div>')
    with right:
        body = _chips_html([str(k) for k in missing[:20]], "warn") if missing else '<p class="empty">All key terms are present.</p>'
        _html(f'<div class="rcard"><div class="rcard-title">Missing keywords</div>{body}</div>')

    body = _chips_html([str(s) for s in gap[:12]], "risk") if gap else '<p class="empty">No significant skills gap detected.</p>'
    _html(f'<div class="rcard" style="margin-top:1rem"><div class="rcard-title">Skills gap</div>{body}</div>')


def _detailed_feedback(analysis: Dict[str, Any]) -> None:
    issues = analysis.get("detailed_feedback") or []
    if not issues:
        return

    _heading("Detailed feedback", f"{len(issues)} issue{'s' if len(issues) != 1 else ''} flagged, grouped by severity.")

    grouped: Dict[str, List[Dict[str, Any]]] = {level: [] for level in SEVERITY_ORDER}
    for issue in issues:
        level = (issue.get("severity_level") or "low").lower()
        grouped.setdefault(level, []).append(issue)

    for level in SEVERITY_ORDER:
        items = grouped.get(level, [])
        if not items:
            continue
        _html(f'<div class="sev-head sev-{level}"><i></i>{level.title()}<span>{len(items)}</span></div>')
        for n, issue in enumerate(items):
            title = issue.get("issue_title", "Untitled issue")
            with st.expander(str(title)):
                fields = []
                for label, key in (
                    ("What’s happening", "explanation"),
                    ("ATS impact", "ats_impact"),
                    ("Where it appears", "where_it_appears"),
                    ("How to fix", "how_to_fix"),
                ):
                    if issue.get(key):
                        fields.append(f"<dt>{label}</dt><dd>{_e(issue[key])}</dd>")
                actions = issue.get("action_items") or []
                if actions:
                    fields.append(f"<dt>Action items</dt><dd>{_list_html([str(a) for a in actions])}</dd>")
                if fields:
                    _html(f'<dl class="finding wide">{"".join(fields)}</dl>')
                if issue.get("example_improvement"):
                    st.caption("Example improvement")
                    st.code(issue["example_improvement"], language="text")


def _action_items(analysis: Dict[str, Any]) -> None:
    items = []
    for issue in analysis.get("detailed_feedback") or []:
        level = (issue.get("severity_level") or "low").lower()
        for action in issue.get("action_items") or []:
            items.append((level, issue.get("issue_title", ""), action))
    if not items:
        for suggestion in analysis.get("suggestions") or []:
            items.append(("medium", "General", suggestion))
    if not items:
        return
    items.sort(key=lambda row: SEVERITY_RANK.get(row[0], 99))

    _heading("Action items", "Concrete steps to raise your score, most urgent first.")
    rows = "".join(
        f'<div class="arow sev-{level if level in SEVERITY_RANK else "low"}"><i></i>'
        f'<div><span class="src">{_e(source)}</span>{_e(action)}</div></div>'
        for level, source, action in items
    )
    _html(f'<div class="rcard">{rows}</div>')


def _recommendations(analysis: Dict[str, Any]) -> None:
    suggestions = analysis.get("suggestions") or []
    if not suggestions:
        return
    _heading("Recommendations")
    _html(f'<div class="rcard">{_list_html([str(s) for s in suggestions])}</div>')


# ---------- entry point ----------

def display_results_dashboard(analysis: Dict[str, Any]) -> None:
    """Render the full results page from one backend response dict."""
    _overall_score(analysis)
    _score_breakdown(analysis)
    _strengths_and_issues(analysis)
    _skill_validation(analysis)

    # JD comparison only shows up if the user actually submitted a JD.
    jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")
    if jd_comparison:
        _jd_match(jd_comparison)

    _detailed_feedback(analysis)
    _action_items(analysis)
    _recommendations(analysis)