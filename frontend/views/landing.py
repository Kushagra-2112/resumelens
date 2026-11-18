import streamlit as st

# NOTE: Streamlit treats blank lines and 4-space indents inside HTML as markdown,
# which breaks layout. Keep every HTML string flush-left with no empty lines.

HERO_COPY = """<h1 class="hero-title">A resume review that checks more than keywords.</h1>
<p class="hero-sub">Most ATS checkers stop at “does this keyword appear.” ResumeLens goes further: it verifies that the skills you list are backed up by your experience, and flags personal information you probably shouldn’t be putting on a resume in the first place.</p>"""

# Illustrative sample. Names match the five real score components.
PREVIEW = """<div class="preview">
<div class="preview-head"><span class="preview-file">Sample report</span><span class="preview-tag">Example data</span></div>
<div class="score-row"><span class="score-num">77</span><span class="score-of">out of 100</span></div>
<div class="metric"><div class="metric-top"><span>Formatting</span><b>91</b></div><div class="bar"><i style="width:91%"></i></div></div>
<div class="metric"><div class="metric-top"><span>Keywords</span><b>88</b></div><div class="bar"><i style="width:88%"></i></div></div>
<div class="metric"><div class="metric-top"><span>Content quality</span><b>74</b></div><div class="bar"><i style="width:74%"></i></div></div>
<div class="metric"><div class="metric-top"><span>Skill validation</span><b>62</b></div><div class="bar warn"><i style="width:62%"></i></div></div>
<div class="metric"><div class="metric-top"><span>ATS compatibility</span><b>92</b></div><div class="bar"><i style="width:92%"></i></div></div>
<div class="flag">Street address found in the header. This cost 6 points.</div>
</div>"""

FEATURES = """<h2 class="section-title">What makes ResumeLens different</h2>
<div class="feature-row">
<div class="feature-text"><h3>Skills have to be earned, not just named</h3><p>Most tools check whether a keyword like “Python” appears anywhere on the page. ResumeLens checks whether it’s actually demonstrated, tied to a project or a line of real experience, using semantic matching rather than a simple text search.</p><p>A skill with nothing behind it gets flagged as unvalidated, so you know before a recruiter does.</p></div>
<div class="demo">
<div class="demo-title">Skill validation</div>
<div class="skill"><div class="skill-head"><b>Python</b><span class="chip ok">Backed by experience</span></div><div class="evidence">“Built a <mark>FastAPI service</mark> that parses 2,000 resumes a day.”</div></div>
<div class="skill"><div class="skill-head"><b>Kubernetes</b><span class="chip warn">No evidence found</span></div><div class="evidence none">Listed under Skills, but no project or role mentions it.</div></div>
</div>
</div>
<div class="feature-row flip">
<div class="feature-text"><h3>Your resume shouldn’t be a privacy risk</h3><p>Full street addresses and ZIP codes are outdated on a resume, and once it’s on a public job board, that information is exposed to anyone.</p><p>ResumeLens detects address and location data in the text and penalizes the score for it, the same way it would flag a formatting issue.</p></div>
<div class="demo">
<div class="demo-title">Privacy check</div>
<div class="doc-name">Alex Morgan</div>
<div class="doc-line">alex.morgan@email.com</div>
<div class="doc-line hit">42 Maple Street, Springfield 62704</div>
<div class="hit-note"><b>Score −6.</b> A street address and ZIP code are visible to anyone once this is posted. Keep the city only.</div>
</div>
</div>
<div class="feature-row">
<div class="feature-text"><h3>A breakdown you can act on</h3><p>Formatting, keywords, content quality, skill validation and ATS compatibility are scored independently.</p><p>Every issue comes with where it appears, why it matters and a concrete fix, not just a number and a shrug.</p></div>
<div class="demo">
<div class="demo-title">One finding</div>
<div class="finding-head"><b>Bullet has no measurable result</b><span class="chip warn">Content quality</span></div>
<dl class="finding"><dt>Where</dt><dd>Experience, Acme Corp, second bullet</dd><dt>Why it matters</dt><dd>Recruiters and ranking systems both favor results they can count.</dd><dt>Fix</dt><dd>Add the outcome: “Cut report generation from 4 hours to 20 minutes.”</dd></dl>
</div>
</div>"""

STEPS = """<h2 class="section-title">How it works</h2>
<div class="steps">
<div class="step"><span class="step-n">1</span><h3>Upload</h3><p>PDF, DOC or DOCX. One resume, or several to compare against the same role.</p></div>
<div class="step"><span class="step-n">2</span><h3>Analyze</h3><p>Skills are checked against your own experience text, personal information is scanned for exposure risk, and the resume is scored against an optional job description.</p></div>
<div class="step"><span class="step-n">3</span><h3>Review</h3><p>Get five scores, and for every issue, where it is, why it matters and how to fix it.</p></div>
</div>"""

CLOSING = """<div class="closing"><h2>See your resume the way a machine does.</h2><p>It takes about a minute. Sign in from the sidebar to run your first analysis.</p></div>"""


def render():
    left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")

    with left:
        st.markdown(HERO_COPY, unsafe_allow_html=True)
        if st.button("Analyze a resume", type="primary", key="landing_cta_top"):
            st.session_state.current_view = "scorer"
            st.rerun()

    with right:
        st.markdown(PREVIEW, unsafe_allow_html=True)

    st.markdown(FEATURES, unsafe_allow_html=True)
    st.markdown(STEPS, unsafe_allow_html=True)
    st.markdown(CLOSING, unsafe_allow_html=True)

    if st.button("Analyze a resume", type="primary", key="landing_cta_bottom"):
        st.session_state.current_view = "scorer"
        st.rerun()