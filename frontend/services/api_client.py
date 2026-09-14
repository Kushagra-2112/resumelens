import time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


DEFAULT_BACKEND_URL = "http://localhost:8000"

# How many times to retry a request that comes back with 429 (rate limited),
# and how long to wait between attempts. Groq's error messages have been
# quoting sub-second waits (e.g. "try again in 975ms"), so a short fixed
# backoff with a couple of retries covers the common case without making
# the user wait too long on a real failure.
MAX_RETRIES_ON_RATE_LIMIT = 3
RETRY_BACKOFF_SECONDS = 2.0


def _backend_url() -> str:
    try:
        return st.secrets["backend"]["url"]
    except (KeyError, FileNotFoundError):
        return DEFAULT_BACKEND_URL


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def health_check() -> Dict[str, Any]:
    response = requests.get(f"{_backend_url()}/api/v1/health", timeout=10)
    response.raise_for_status()
    return response.json()


def analyze_resume(
    resume_file,
    access_token: str,
    job_description: str = "",
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a single resume. Retries automatically on HTTP 429 (rate limit)
    since the LLM provider (Groq) enforces a tokens-per-minute cap that bulk
    uploads can hit even when each individual request is well within limits.

    `batch_id` is optional and passed through as a form field so the backend
    can (once it supports it) group resumes analyzed together into one
    session for the History page. Safe to omit for single-resume analysis.
    """
    files = {
        "resume": (resume_file.name, resume_file.getvalue(), resume_file.type),
    }
    data = {"job_description": job_description}
    if batch_id:
        data["batch_id"] = batch_id

    last_exc: Optional[requests.HTTPError] = None

    for attempt in range(MAX_RETRIES_ON_RATE_LIMIT + 1):
        response = requests.post(
            f"{_backend_url()}/api/v1/analyze-resume",
            files=files,
            data=data,
            headers=_auth_headers(access_token),
            timeout=180,
        )

        if response.status_code == 429:
            last_exc = requests.HTTPError(response=response)
            if attempt < MAX_RETRIES_ON_RATE_LIMIT:
                # Simple fixed backoff. If the backend/provider starts
                # returning a Retry-After header, prefer that instead:
                #   wait = float(response.headers.get("Retry-After", RETRY_BACKOFF_SECONDS))
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            break

        response.raise_for_status()
        return response.json()

    # Exhausted retries on repeated 429s — raise the last one so the caller's
    # existing requests.HTTPError handling (_show_backend_error) still works.
    raise last_exc


def get_history(access_token: str) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{_backend_url()}/api/v1/history",
        headers=_auth_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def delete_history_entry(analysis_id: str, access_token: str) -> None:
    response = requests.delete(
        f"{_backend_url()}/api/v1/history/{analysis_id}",
        headers=_auth_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()


def generate_pdf(analysis_data: Dict[str, Any], access_token: str) -> bytes:
    response = requests.post(
        f"{_backend_url()}/api/v1/generate-pdf",
        json=analysis_data,
        headers=_auth_headers(access_token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def get_history_pdf(analysis_id: str, access_token: str) -> bytes:
    response = requests.get(
        f"{_backend_url()}/api/v1/history/{analysis_id}/pdf",
        headers=_auth_headers(access_token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content