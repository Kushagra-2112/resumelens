from typing import Optional

import requests
import streamlit as st
from frontend.services import api_client
from frontend.components.dashboard import display_results_dashboard


def _read_jd(jd_file, jd_text: str) -> str:
    """
    Turn whatever the user provided into a plain JD string for the backend.

    For .txt files we decode in-process — that's a trivial operation, no need
    for a backend round-trip. For PDF/DOCX, we'd need the backend's parser;
    we don't have a public endpoint for that, so we ask the user to paste text
    instead for non-txt JDs.
    """
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning(
        "Job description files must be `.txt` for now — paste the JD text instead "
        "if you have a PDF or DOCX."
    )
    return ""


def _show_backend_error(exc: Exception, label: str = "") -> None:
    """Translate a `requests` exception into a friendly Streamlit error."""
    prefix = f"[{label}] " if label else ""
    if isinstance(exc, requests.ConnectionError):
        st.error(f"{prefix}Could not reach the backend. Is `uvicorn backend.main:app` running on port 8000?")
    elif isinstance(exc, requests.Timeout):
        st.error(f"{prefix}The backend took too long to respond. Try a smaller resume or check the server logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"{prefix}Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"{prefix}Unexpected error: {exc}")


def _get_score(analysis: dict) -> float:
    """Pull the ATS score out of an analysis dict."""
    try:
        return float(analysis.get("ats_score", 0))
    except (TypeError, ValueError):
        return 0.0


def _display_name(key_suffix: str) -> str:
    """Strip the leading index prefix ('0_filename.pdf' -> 'filename.pdf') for display."""
    if "_" in key_suffix:
        idx, rest = key_suffix.split("_", 1)
        if idx.isdigit():
            return rest
    return key_suffix


def _summary_text(analysis: dict) -> str:
    """Tiny client-side text summary for a single resume's Download button."""
    score = _get_score(analysis)
    lines = [f"ATS Score: {score:.0f}/100", ""]
    if analysis.get("strengths"):
        lines.append("STRENGTHS:")
        lines.extend(f"  - {s}" for s in analysis["strengths"])
        lines.append("")
    if analysis.get("critical_issues"):
        lines.append("CRITICAL ISSUES:")
        lines.extend(f"  - {s}" for s in analysis["critical_issues"])
        lines.append("")
    if analysis.get("suggestions"):
        lines.append("SUGGESTIONS:")
        lines.extend(f"  - {s}" for s in analysis["suggestions"])
    return "\n".join(lines)


def _combined_report_text(results: dict, analysis_mode: str, job_description: str = "") -> str:
    """
    One consolidated report across every analyzed resume: ranking, the winner,
    and a per-resume breakdown. This is the single file the user downloads
    when comparing multiple resumes for one role.
    """
    ranked = sorted(results.items(), key=lambda kv: _get_score(kv[1]), reverse=True)

    lines = ["ATS RESUME COMPARISON REPORT", "=" * 40, ""]

    if analysis_mode == "Job Description Comparison" and job_description:
        snippet = job_description.strip().splitlines()[0][:120]
        lines.append(f"Job Description (excerpt): {snippet}")
        lines.append("")

    lines.append(f"Resumes compared: {len(ranked)}")
    lines.append("")
    lines.append("RANKING")
    lines.append("-" * 40)
    for rank, (key_suffix, analysis) in enumerate(ranked, start=1):
        lines.append(f"{rank}. {_display_name(key_suffix)} — {_get_score(analysis):.0f}/100")
    lines.append("")

    top_key, top_analysis = ranked[0]
    lines.append(f">>> BEST FIT: {_display_name(top_key)} ({_get_score(top_analysis):.0f}/100) <<<")
    lines.append("")

    if len(ranked) > 1:
        gap = _get_score(top_analysis) - _get_score(ranked[1][1])
        if gap < 3:
            lines.append(
                f"Note: {_display_name(top_key)} and {_display_name(ranked[1][0])} are close "
                f"({gap:.0f} point gap) — worth a manual look at both."
            )
            lines.append("")

    lines.append("=" * 40)
    lines.append("DETAILED BREAKDOWN")
    lines.append("=" * 40)
    for rank, (key_suffix, analysis) in enumerate(ranked, start=1):
        lines.append("")
        lines.append(f"[{rank}] {_display_name(key_suffix)} — Score: {_get_score(analysis):.0f}/100")
        lines.append("-" * 40)
        if analysis.get("strengths"):
            lines.append("Strengths:")
            lines.extend(f"  - {s}" for s in analysis["strengths"])
        if analysis.get("critical_issues"):
            lines.append("Critical Issues:")
            lines.extend(f"  - {s}" for s in analysis["critical_issues"])
        if analysis.get("suggestions"):
            lines.append("Suggestions:")
            lines.extend(f"  - {s}" for s in analysis["suggestions"])

    return "\n".join(lines)


def _render_upload_area(analysis_mode: str):
    """Two-column upload widgets. Returns (resume_files, jd_file, jd_text)."""
    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Upload Resume(s)")
        resume_files = st.file_uploader(
            "Choose your resume file(s)",
            type=["pdf", "doc", "docx"],
            help="Supported: PDF, DOC, DOCX (max 5 MB each). Select multiple files to compare against one role.",
            key="resume_upload",
            accept_multiple_files=True,
        )
        if resume_files:
            for f in resume_files:
                st.success(f"✅ {f.name} ({f.size / 1024:.1f} KB)")

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        if analysis_mode == "Job Description Comparison":
            st.markdown("### 📋 Job Description")
            jd_method = st.radio(
                "Input method:",
                ["Paste Text", "Upload .txt File"],
                horizontal=True,
                key="jd_input_method",
            )
            if jd_method == "Upload .txt File":
                jd_file = st.file_uploader(
                    "Choose JD file (.txt only)",
                    type=["txt"],
                    key="jd_upload",
                )
                if jd_file:
                    st.success(f"✅ {jd_file.name}")
            else:
                jd_text = st.text_area(
                    "Paste job description text:",
                    height=200,
                    placeholder="Paste the JD here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.markdown("### 📋 Job Description")
            st.info("Switch to 'Job Description Comparison' mode to enable JD matching.")

    return resume_files, jd_file, jd_text


def _render_comparison(results: dict, analysis_mode: str, job_description: str = "") -> None:
    """
    Ranked side-by-side comparison across all analyzed resumes, plus a single
    consolidated download so the user gets one file naming the best fit.
    Only meaningful with 2+ resumes, so callers should check len(results) > 1.
    """
    st.markdown("## 🏆 Comparison")
    if analysis_mode == "Job Description Comparison":
        st.caption("Ranked by fit against the job description you provided.")
    else:
        st.caption("Ranked by general ATS score.")

    ranked = sorted(results.items(), key=lambda kv: _get_score(kv[1]), reverse=True)

    rows = []
    for rank, (key_suffix, analysis) in enumerate(ranked, start=1):
        rows.append(
            {
                "Rank": rank,
                "Resume": _display_name(key_suffix),
                "Score": round(_get_score(analysis), 1),
                "Strengths": len(analysis.get("strengths", [])),
                "Critical Issues": len(analysis.get("critical_issues", [])),
                "Suggestions": len(analysis.get("suggestions", [])),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    top_key, top_analysis = ranked[0]
    top_score = _get_score(top_analysis)
    label = "best match for this job description" if analysis_mode == "Job Description Comparison" else "highest overall ATS score"
    st.success(f"🥇 **{_display_name(top_key)}** is the {label} — {top_score:.0f}/100.")

    if len(ranked) > 1:
        second_key, second_analysis = ranked[1]
        gap = top_score - _get_score(second_analysis)
        if gap < 3:
            st.info(
                f"Note: **{_display_name(top_key)}** and **{_display_name(second_key)}** "
                f"are close ({gap:.0f} point gap) — worth reviewing both in detail below."
            )

    # The single consolidated file: ranking + winner + every resume's breakdown.
    st.download_button(
        "📥 Download Best-Fit Report (.txt)",
        data=_combined_report_text(results, analysis_mode, job_description),
        file_name="ats_best_fit_report.txt",
        mime="text/plain",
        use_container_width=True,
        type="primary",
        key="download_combined_report",
    )

    st.markdown("---")


def _render_export_buttons(analysis: dict, key_suffix: str) -> None:
    st.markdown("##### 📥 Export this resume")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("📑 Generate PDF Report", use_container_width=True, key=f"gen_pdf_{key_suffix}"):
            try:
                with st.spinner("Generating PDF on backend..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state["access_token"],
                    )
                st.session_state[f"scorer_pdf_bytes_{key_suffix}"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc, label=key_suffix)

        if f"scorer_pdf_bytes_{key_suffix}" in st.session_state:
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state[f"scorer_pdf_bytes_{key_suffix}"],
                file_name=f"ats_resume_report_{key_suffix}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"download_pdf_report_{key_suffix}",
            )

    with c2:
        st.download_button(
            "📄 Download Summary (.txt)",
            data=_summary_text(analysis),
            file_name=f"ats_summary_{key_suffix}.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"download_summary_{key_suffix}",
        )


def render() -> None:
    st.title("🎯 ATS Resume Scorer")
    st.markdown("Upload one or more resumes — and optionally a job description — for a comprehensive analysis.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 📊 Analysis Options")
        st.info(
            "**General ATS Score**: resume only — overall compatibility.\n\n"
            "**JD Comparison**: resume + job description — targeted match analysis."
        )

    st.markdown("---")

    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
    )

    st.markdown("---")

    resume_files, jd_file, jd_text = _render_upload_area(analysis_mode)

    st.markdown("---")

    if not resume_files:
        st.info("👆 Upload one or more resumes to begin.")
        if st.session_state.get("scorer_analyses"):
            results = st.session_state["scorer_analyses"]
            mode = st.session_state.get("scorer_mode", analysis_mode)
            jd = st.session_state.get("scorer_jd", "")
            if len(results) > 1:
                _render_comparison(results, mode, jd)
            for key_suffix, analysis in results.items():
                st.markdown(f"#### Results: {_display_name(key_suffix)}")
                display_results_dashboard(analysis)
        return

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("⚠️ Sign in from the sidebar to analyze a resume.")
        return

    st.caption(f"{len(resume_files)} resume(s) ready for analysis.")

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button("🚀 Analyze Resume(s)", use_container_width=True, type="primary")

    if not analyze:
        # Re-show previous results on rerun (e.g. after downloading the report).
        if st.session_state.get("scorer_analyses"):
            results = st.session_state["scorer_analyses"]
            mode = st.session_state.get("scorer_mode", analysis_mode)
            jd = st.session_state.get("scorer_jd", "")
            if len(results) > 1:
                _render_comparison(results, mode, jd)
            for key_suffix, analysis in results.items():
                with st.expander(f"📄 {_display_name(key_suffix)}", expanded=len(results) == 1):
                    display_results_dashboard(analysis)
                    _render_export_buttons(analysis, key_suffix)
        return

    # Fresh analysis — drop any cached PDFs/results.
    for k in list(st.session_state.keys()):
        if k.startswith("scorer_pdf_bytes_") or k in ("scorer_analyses", "scorer_mode", "scorer_jd"):
            del st.session_state[k]

    job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""

    results: dict = {}
    progress = st.progress(0.0, text="Starting analysis...")

    for i, resume_file in enumerate(resume_files):
        key_suffix = f"{i}_{resume_file.name}"
        progress.progress(
            i / len(resume_files),
            text=f"Analyzing {resume_file.name} ({i + 1}/{len(resume_files)})...",
        )
        try:
            analysis = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=access_token,
                job_description=job_description,
            )
            results[key_suffix] = analysis
        except requests.RequestException as exc:
            _show_backend_error(exc, label=resume_file.name)

    progress.progress(1.0, text="Done!")
    progress.empty()

    if not results:
        st.error("No resumes were analyzed successfully — see errors above.")
        return

    st.session_state["scorer_analyses"] = results
    st.session_state["scorer_mode"] = analysis_mode
    st.session_state["scorer_jd"] = job_description
    st.success(f"✅ Analysis complete for {len(results)}/{len(resume_files)} resume(s)!")

    if len(results) > 1:
        _render_comparison(results, analysis_mode, job_description)

    for key_suffix, analysis in results.items():
        with st.expander(f"📄 {_display_name(key_suffix)}", expanded=len(results) == 1):
            display_results_dashboard(analysis)
            _render_export_buttons(analysis, key_suffix)