import html
from datetime import datetime
from typing import Any

import requests
import streamlit as st

from frontend.services import api_client

# Max score per component (matches backend/core/config.py SCORE_WEIGHTS).
COMPONENTS = [
    ("Formatting", "formatting", 20),
    ("Keywords and skills", "keywords", 25),
    ("Content quality", "content", 25),
    ("Skill validation", "skill_validation", 15),
    ("ATS compatibility", "ats_compatibility", 15),
]


def _e(value: Any) -> str:
    """Escape for HTML; '$' is escaped so Streamlit doesn't treat it as math."""
    return html.escape(str(value)).replace("$", "&#36;") if value is not None else ""


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tier(fraction: float) -> str:
    return "good" if fraction >= 0.8 else "fair" if fraction >= 0.6 else "poor"


def _fmt_date(raw: Any) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return str(raw)


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is it running on port 8000?")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.error(f"Backend returned {exc.response.status_code}: {exc.response.text}")
    else:
        st.error(f"Unexpected error: {exc}")


def render() -> None:
    st.markdown(
        '<h1 class="page-title">History</h1>'
        '<p class="page-sub">Every analysis you have run, saved to your account.</p>',
        unsafe_allow_html=True,
    )

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("Sign in from the sidebar to view your history.")
        return

    try:
        history = api_client.get_history(access_token)
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    if not history:
        st.info("No analyses yet. Run your first one on the ATS scorer page.")
        if st.button("Go to ATS scorer", type="primary"):
            st.session_state.current_view = "scorer"
            st.rerun()
        return

    scores = [_num(entry.get("ats_score", 0)) for entry in history]
    average = sum(scores) / len(scores)
    best = max(scores)
    st.markdown(
        f'<div class="stats">'
        f'<div class="stat"><div class="stat-num">{len(history)}</div><div class="stat-label">Analyses</div></div>'
        f'<div class="stat"><div class="stat-num">{average:.0f}</div><div class="stat-label">Average score</div></div>'
        f'<div class="stat"><div class="stat-num">{best:.0f}</div><div class="stat-label">Best score</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for idx, entry in enumerate(history):
        filename = entry.get("filename", "resume")
        ats_score = _num(entry.get("ats_score", 0))
        created = _fmt_date(entry.get("created_at", ""))
        analysis = entry.get("analysis_result", {}) or {}
        component_scores = analysis.get("component_scores", {}) or {}
        jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

        label = f"{filename}  ({ats_score:.0f}/100" + (f", {created})" if created else ")")
        with st.expander(label):
            tier = _tier(ats_score / 100.0)
            jd_chip = ""
            if jd_comparison:
                jd_chip = f'<span class="chip ok">Job match {_num(jd_comparison.get("match_percentage", 0)):.0f}%</span>'
            st.markdown(
                f'<div class="hist-head tier-{tier}">'
                f'<span class="hist-score">{ats_score:.0f}</span>'
                f'<div><div class="hist-title">Overall ATS score</div><div class="hist-date">{_e(created)}</div></div>'
                f'{jd_chip}</div>',
                unsafe_allow_html=True,
            )

            rows = []
            for comp_label, key, max_score in COMPONENTS:
                value = _num(component_scores.get(key, 0))
                frac = min(max(value / max_score, 0.0), 1.0)
                rows.append(
                    f'<div class="brow"><span class="brow-label">{_e(comp_label)}</span>'
                    f'<div class="bar tier-{_tier(frac)}"><i style="width:{frac * 100:.0f}%"></i></div>'
                    f'<span class="brow-val">{value:.0f} / {max_score}</span></div>'
                )
            st.markdown('<div class="rcard">' + "".join(rows) + "</div>", unsafe_allow_html=True)

            entry_id = entry.get("id")
            if entry_id:
                if st.button("Delete this analysis", key=f"delete_{idx}"):
                    try:
                        api_client.delete_history_entry(str(entry_id), access_token)
                        st.toast("Analysis deleted")
                        st.rerun()
                    except requests.RequestException as exc:
                        _show_backend_error(exc)