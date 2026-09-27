import streamlit as st


def render():
    # ---- Headline ----
    st.markdown(
        """
        <div class="rl-ed-eyebrow">ATS RESUME ANALYSIS</div>
        <h1 class="rl-ed-headline">A resume review that checks more than keywords.</h1>
        <p class="rl-ed-sub">
            Most ATS checkers stop at "does this keyword appear." ResumeLens goes
            further — it verifies that the skills you list are actually backed up
            by your experience, and flags personal information you probably
            shouldn't be putting on a resume in the first place.
        </p>
        <hr class="rl-ed-rule">
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        if st.button("Analyze a resume", use_container_width=True, type="primary"):
            st.session_state.current_view = 'scorer'
            st.rerun()

    # ---- Trust strip ----
    st.markdown(
        """
        <div class="rl-trust-strip">
            <div class="rl-trust-item">
                <div class="num">01</div>
                <div class="label">Evidence-checked skills</div>
                <div class="desc">Skills are matched against your own project and experience text, not just listed.</div>
            </div>
            <div class="rl-trust-item">
                <div class="num">02</div>
                <div class="label">Privacy-aware scoring</div>
                <div class="desc">Flags exposed home addresses and ZIP codes before you post your resume publicly.</div>
            </div>
            <div class="rl-trust-item">
                <div class="num">03</div>
                <div class="label">Component-level detail</div>
                <div class="desc">Five separate scores, not one opaque number — you know exactly where points were lost.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- What makes it different ----
    st.markdown('<div class="rl-ed-section-label">WHAT MAKES THIS DIFFERENT</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rl-feature-row">
            <div class="rl-feature-mark">I.</div>
            <div class="rl-feature-body">
                <h4>Skills have to be earned, not just named</h4>
                <p>Most tools check whether a keyword like "Python" appears anywhere on the page.
                ResumeLens checks whether it's actually demonstrated — tied to a project or a line
                of real experience — using semantic matching rather than a simple text search.
                A skill with nothing behind it gets flagged as unvalidated, so you know before a
                recruiter does.</p>
                <span class="rl-feature-tag">Skill validation</span>
            </div>
        </div>
        <div class="rl-feature-row">
            <div class="rl-feature-mark">II.</div>
            <div class="rl-feature-body">
                <h4>Your resume shouldn't be a privacy risk</h4>
                <p>Full street addresses and ZIP codes are outdated on a resume — and once it's on a
                public job board, that information is exposed to anyone. ResumeLens detects address
                and location data in the text and penalizes the score for it, the same way it would
                flag a formatting issue.</p>
                <span class="rl-feature-tag">Privacy check</span>
            </div>
        </div>
        <div class="rl-feature-row">
            <div class="rl-feature-mark">III.</div>
            <div class="rl-feature-body">
                <h4>A breakdown you can act on</h4>
                <p>Formatting, keywords, content quality, skill validation, and ATS compatibility are
                scored independently. Every issue comes with where it appears, why it matters, and a
                concrete fix — not just a number and a shrug.</p>
                <span class="rl-feature-tag">Detailed feedback</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- How it works ----
    st.markdown('<div class="rl-ed-section-label">HOW IT WORKS</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rl-process-item">
            <div class="rl-process-index">1</div>
            <div class="rl-process-body">
                <h4>Upload</h4>
                <p>PDF, DOC, or DOCX — one resume, or several to compare against the same role.</p>
            </div>
        </div>
        <div class="rl-process-item">
            <div class="rl-process-index">2</div>
            <div class="rl-process-body">
                <h4>Analyze</h4>
                <p>Skills are checked against your own experience text, personal information is scanned
                for exposure risk, and the resume is scored against an optional job description.</p>
            </div>
        </div>
        <div class="rl-process-item">
            <div class="rl-process-index">3</div>
            <div class="rl-process-body">
                <h4>Fix</h4>
                <p>Get a ranked list of issues and concrete action items, then export a report.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Closing CTA ----
    st.markdown(
        """
        <div class="rl-ed-cta">
            <div>
                <h3>Ready to see where your resume stands?</h3>
                <p>Takes about a minute. No account setup beyond signing in.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, mid2, _ = st.columns([1, 1.2, 1])
    with mid2:
        if st.button("Start now", use_container_width=True, type="primary", key="cta_bottom"):
            st.session_state.current_view = 'scorer'
            st.rerun()