import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.api.auth import get_current_user
from backend.models.schemas import (
    AnalysisResponse,
    BulkAnalysisResponse,
    BulkResumeResult,
    ComponentScores,
    JDComparison,
    SkillValidationDetails,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])

# Concurrency cap — respects Groq API rate limits. Tune based on your Groq
# tier's requests-per-minute limit.
BULK_CONCURRENCY_LIMIT = 3


@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
    user_id: str = Depends(get_current_user),
):
    nlp = request.app.state.nlp
    embedder = request.app.state.embedder

    try:
        file_bytes = await resume.read()
        filename = resume.filename or 'resume'

        from backend.services.resume_parser import (
            FileParsingError,
            FileValidationError,
            parse_resume_file,
        )

        resume_text, _metadata = parse_resume_file(file_bytes, filename)
        logger.info(f"Parsed '{filename}': {len(resume_text)} chars extracted")

    except Exception as exc:
        logger.error(f'File parsing failed: {exc}')
        raise HTTPException(
            status_code=422,
            detail=f'Could not read or parse the resume: {exc}',
        )

    try:
        from backend.services.resume_analyzer import analyze_full_resume

        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description,
        )
    except Exception as exc:
        logger.error(f'Full analysis pipeline failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Analysis pipeline failed: {exc}')

    jd_comparison_result = None
    if result.get('jd_comparison'):
        jd_comparison_result = JDComparison(
            match_percentage=round(float(result['jd_comparison'].get('match_percentage', 0.0)), 1),
            semantic_similarity=round(float(result['jd_comparison'].get('semantic_similarity', 0.0)), 3),
            matched_keywords=result['jd_comparison'].get('matched_keywords', [])[:20],
            missing_keywords=result['jd_comparison'].get('missing_keywords', [])[:15],
            skills_gap=result['jd_comparison'].get('skills_gap', [])[:10],
        )

    svd_raw = result.get('skill_validation_details') or {}
    skill_val_details = SkillValidationDetails(
        validated=svd_raw.get('validated', []),
        unvalidated=svd_raw.get('unvalidated', []),
        total=svd_raw.get('total', 0),
        validated_count=svd_raw.get('validated_count', 0),
        validation_pct=svd_raw.get('validation_pct', 0.0),
    )

    response = AnalysisResponse(
        ats_score=result['ats_score'],
        component_scores=ComponentScores(**result['component_scores']),
        issues_summary=result['issues_summary'],
        detailed_feedback=result.get('detailed_feedback', []),
        jd_comparison=jd_comparison_result,
        skill_validation_details=skill_val_details,
        keyword_match=jd_comparison_result.match_percentage if jd_comparison_result else 0.0,
        missing_keywords=result.get('missing_keywords', []),
        matched_keywords=result.get('matched_keywords', []),
        skills=list(result.get('skills', [])[:20]),
        interpretation=result.get('interpretation', ''),
        strengths=result.get('strengths', []),
        critical_issues=result.get('critical_issues', []),
        suggestions=result.get('suggestions', []),
    )

    try:
        from backend.database.supabase_db import save_analysis
        await save_analysis(user_id, filename, result)
    except Exception as exc:
        logger.warning(f'History save failed (non-blocking): {exc}')

    return response


async def _analyze_one_resume(
    file: UploadFile,
    job_description: str,
    nlp,
    embedder,
    semaphore: asyncio.Semaphore,
):
    from backend.services.resume_parser import parse_resume_file
    from backend.services.resume_analyzer import analyze_full_resume

    filename = file.filename or "resume"

    async with semaphore:
        try:
            file_bytes = await file.read()
            resume_text, _ = parse_resume_file(file_bytes, filename)

            # analyze_full_resume is sync/CPU-bound (embeddings, regex, etc.)
            # — run it in a thread so it doesn't block the event loop while
            # other resumes in the batch are waiting on their own Groq calls.
            result = await asyncio.to_thread(
                analyze_full_resume,
                resume_text=resume_text,
                nlp=nlp,
                embedder=embedder,
                job_description=job_description,
            )

            return BulkResumeResult(
                filename=filename,
                status="success",
                ats_score=result["ats_score"],
                analysis=None,  # full per-resume AnalysisResponse omitted from bulk payload to keep it light; stored in DB instead
            ), result

        except Exception as exc:
            logger.error(f"Bulk analysis failed for '{filename}': {exc}")
            return BulkResumeResult(
                filename=filename,
                status="failed",
                error_message=str(exc),
            ), None


@router.post('/analyze-resumes-bulk', response_model=BulkAnalysisResponse)
async def analyze_resumes_bulk(
    request: Request,
    resumes: List[UploadFile] = File(..., description="Multiple resume files — PDF or DOCX"),
    job_description: str = Form(..., description="Job description text (required for bulk mode)"),
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import create_batch_job, save_batch_result, update_batch_counts

    if not resumes:
        raise HTTPException(status_code=422, detail="At least one resume file is required.")
    if len(resumes) > 30:
        raise HTTPException(status_code=422, detail="Maximum 30 resumes per batch.")

    nlp = request.app.state.nlp
    embedder = request.app.state.embedder

    batch_id = await create_batch_job(user_id, job_description, len(resumes))
    if batch_id is None:
        logger.warning("Could not create batch_jobs row — continuing without persistent batch tracking")

    semaphore = asyncio.Semaphore(BULK_CONCURRENCY_LIMIT)
    tasks = [
        _analyze_one_resume(file, job_description, nlp, embedder, semaphore)
        for file in resumes
    ]
    outcomes = await asyncio.gather(*tasks)

    results = []
    completed_count = 0
    failed_count = 0

    for bulk_result, full_result in outcomes:
        results.append(bulk_result)
        if bulk_result.status == "success":
            completed_count += 1
        else:
            failed_count += 1

        if batch_id is not None:
            await save_batch_result(
                batch_id=batch_id,
                filename=bulk_result.filename,
                status=bulk_result.status,
                ats_score=bulk_result.ats_score,
                error_message=bulk_result.error_message,
                analysis_result=full_result,
            )

    if batch_id is not None:
        await update_batch_counts(batch_id, completed_count, failed_count)

    # Rank successful results by score, descending; failed ones go to the end.
    results.sort(key=lambda r: (r.status != "success", -(r.ats_score or 0)))

    return BulkAnalysisResponse(
        batch_id=int(batch_id) if batch_id else 0,
        total_resumes=len(resumes),
        completed_count=completed_count,
        failed_count=failed_count,
        results=results,
    )


@router.get('/health')
async def health_check(request: Request):
    """Health check — confirms models are loaded and the API is ready."""
    return {
        'status': 'healthy',
        'nlp_loaded': request.app.state.nlp is not None,
        'embedder_loaded': request.app.state.embedder is not None,
    }


@router.get('/history')
async def get_history(user_id: str = Depends(get_current_user)):
    """Return the signed-in user's past analyses (identity comes from the JWT)."""
    from backend.database.supabase_db import get_user_history
    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.error(f'History fetch failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete one analysis from the signed-in user's history."""
    from backend.database.supabase_db import delete_analysis
    try:
        success = await delete_analysis(analysis_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail='Analysis not found or not owned by this user.')
        return {'status': 'deleted', 'id': analysis_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f'History delete failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not delete: {exc}')


@router.post('/generate-pdf')
async def generate_pdf(
    data: AnalysisResponse,
    user_id: str = Depends(get_current_user),
):
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    try:
        html_docs = generate_html_reports(data.model_dump())
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=ats_report.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")


@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import get_user_history
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    history = await get_user_history(user_id)
    analysis_data = next((item["analysis_result"] for item in history if item["id"] == analysis_id), None)

    if not analysis_data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        html_docs = generate_html_reports(analysis_data)
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ats_report_{analysis_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF for history: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")