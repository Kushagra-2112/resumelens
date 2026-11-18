import html
from typing import Dict, List

import streamlit as st

DOS = [
    "Use standard section headings",
    "Include relevant keywords from the job description",
    "Use simple, clean formatting",
    "List skills explicitly",
    "Quantify achievements with numbers",
    "Use standard fonts (Arial, Calibri, Times New Roman)",
    "Save as PDF or DOCX",
]

DONTS = [
    "Avoid tables and text boxes",
    "Don’t put important information in headers or footers",
    "Avoid images and graphics",
    "Don’t use unusual fonts",
    "Avoid columns; use a single-column layout",
    "Don’t keyword stuff",
    "Spell out abbreviations the first time you use them",
]

# Weights match backend/core/config.py SCORE_WEIGHTS. Descriptions are general summaries.
SCORE_PARTS = [
    ("Formatting", 20, "Whether the layout and structure can be read cleanly by an ATS parser."),
    ("Keywords and skills", 25, "How well your terms and listed skills match what employers search for."),
    ("Content quality", 25, "Clear, specific bullets with measurable results rather than vague duties."),
    ("Skill validation", 15, "Whether each skill you list is backed by a project or real experience."),
    ("ATS compatibility", 15, "File type and layout choices that affect whether a system can parse the resume at all."),
]

KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "Tech": {
        "Programming languages": ["Python", "Java", "JavaScript"],
        "Frameworks": ["React", "Django", "Spring"],
        "Tools": ["Git", "Docker", "Kubernetes"],
        "Methodologies": ["Agile", "Scrum", "CI/CD"],
    },
    "Business": {
        "Management and planning": [
            "Project management", "Stakeholder engagement", "Budget management",
            "Strategic planning", "Team leadership",
        ],
    },
    "Creative": {
        "Design skills": [
            "Adobe Creative Suite", "UI/UX design", "Wireframing and prototyping",
            "Brand identity", "Visual communication",
        ],
    },
}


def _e(text: str) -> str:
    return html.escape(text)


def _list_html(items: List[str], risk: bool = False) -> str:
    cls = "dotlist" + (" risk" if risk else "")
    return f'<ul class="{cls}">' + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>"


def render() -> None:
    st.markdown(
        '<h1 class="page-title">Resources</h1>'
        '<p class="page-sub">Practical guidance for getting your resume through applicant tracking systems.</p>',
        unsafe_allow_html=True,
    )

    # Do and don't
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f'<div class="rcard"><div class="rcard-title">Do</div>{_list_html(DOS)}</div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="rcard"><div class="rcard-title">Don’t</div>{_list_html(DONTS, risk=True)}</div>',
            unsafe_allow_html=True,
        )

    # How the score is built
    st.markdown(
        '<h2 class="res-h">How your score is built</h2>'
        '<p class="res-sub">Five parts add up to 100 points. Bigger bars carry more weight.</p>',
        unsafe_allow_html=True,
    )
    rows = "".join(
        f'<div class="wrow"><div><b>{_e(name)}</b><span class="vrow-sub">{_e(desc)}</span></div>'
        f'<div class="bar"><i style="width:{weight / 25 * 100:.0f}%"></i></div>'
        f'<span class="brow-val">{weight} pts</span></div>'
        for name, weight, desc in SCORE_PARTS
    )
    st.markdown(f'<div class="rcard">{rows}</div>', unsafe_allow_html=True)

    # Keywords by industry
    st.markdown(
        '<h2 class="res-h">Common keywords by industry</h2>'
        '<p class="res-sub">Use the terms that genuinely describe your work, and back each one up with a project or result.</p>',
        unsafe_allow_html=True,
    )
    tabs = st.tabs(list(KEYWORDS.keys()))
    for tab, (industry, groups) in zip(tabs, KEYWORDS.items()):
        with tab:
            blocks = "".join(
                f'<div class="kw-group"><div class="kw-title">{_e(group)}</div>'
                + '<div class="chips">'
                + "".join(f'<span class="chip neutral">{_e(k)}</span>' for k in words)
                + "</div></div>"
                for group, words in groups.items()
            )
            st.markdown(f'<div class="rcard" style="margin-top:.8rem">{blocks}</div>', unsafe_allow_html=True)

    # Templates
    st.markdown('<h2 class="res-h">ATS-friendly resume templates</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rcard"><p class="empty" style="margin:0">Coming soon: downloadable resume templates built to pass ATS parsing.</p></div>',
        unsafe_allow_html=True,
    )