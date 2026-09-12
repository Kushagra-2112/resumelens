import logging
import httpx
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict

logger = logging.getLogger('ats_resume_scorer')

from backend.core.config import SUPABASE_URL, SUPABASE_KEY

_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def _get_headers():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def _json_default(o):
    if hasattr(o, 'model_dump'):
        return o.model_dump()
    # Handle numpy scalars (float64, int64, etc.) so numbers stay numbers,
    # not strings, once serialized into the JSON column.
    if hasattr(o, 'item'):
        return o.item()
    return str(o)


async def save_analysis(user_id: str, filename: str, analysis_result: Dict) -> Optional[str]:
    headers = _get_headers()
    if not headers:
        return None

    serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get("missing_keywords", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_result": serializable_result,
    }

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=doc)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                inserted_id = str(data[0].get("id"))
                logger.info(f"Saved analysis for user {user_id}: {inserted_id}")
                return inserted_id
            logger.warning(f"Insert succeeded but returned no rows for user {user_id}")
            return None
    except httpx.HTTPStatusError as exc:
        logger.error(f"Failed to save analysis to Supabase: {exc} — response body: {exc.response.text}")
        return None
    except Exception as exc:
        logger.error(f"Failed to save analysis to Supabase: {exc}")
        return None


async def get_user_history(user_id: str) -> List[Dict]:
    headers = _get_headers()
    if not headers:
        return []

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                url,
                headers=headers,
                params={
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc"
                }
            )
            response.raise_for_status()
            docs = response.json()

            results = []
            for doc in docs:
                analysis_result = doc.get("analysis_result", {}) or {}
                results.append({
                    "id": str(doc.get("id")),
                    "filename": doc.get("filename", "resume"),
                    "resume_name": doc.get("filename", "resume"),
                    # Pull the actual job title from the stored analysis if
                    # present, instead of a hardcoded placeholder.
                    "job_title": analysis_result.get("job_title", "Unknown role"),
                    "ats_score": doc.get("ats_score", 0),
                    "keyword_match": doc.get("keyword_match", 0),
                    "missing_keywords": doc.get("missing_keywords", []),
                    "date": doc.get("created_at", ""),
                    "created_at": doc.get("created_at", ""),
                    "analysis_result": analysis_result,
                })
            return results
    except httpx.HTTPStatusError as exc:
        logger.error(f"Failed to fetch history from Supabase: {exc} — response body: {exc.response.text}")
        return []
    except Exception as exc:
        logger.error(f"Failed to fetch history from Supabase: {exc}")
        return []


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    headers = _get_headers()
    if not headers:
        return False

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.delete(
                url,
                headers=headers,
                params={
                    "id": f"eq.{analysis_id}",
                    "user_id": f"eq.{user_id}"
                }
            )
            response.raise_for_status()
            # Prefer: return=representation means a successful delete returns
            # the deleted row(s). If the list is empty, nothing actually
            # matched — e.g. wrong id, or it belongs to a different user.
            deleted_rows = response.json()
            if not deleted_rows:
                logger.warning(
                    f"Delete matched 0 rows for analysis_id={analysis_id}, user_id={user_id}"
                )
                return False
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(f"Failed to delete analysis {analysis_id}: {exc} — response body: {exc.response.text}")
        return False
    except Exception as exc:
        logger.error(f"Failed to delete analysis {analysis_id}: {exc}")
        return False