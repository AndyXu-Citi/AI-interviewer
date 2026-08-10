"""
Match handler — EdgeOne Makers (agents route)
=============================================
File path agents/match/index.py is auto-mapped to **POST /match**.

Body:    { "resume": str, "jdId": str }
Returns: single-JD match breakdown (score + reason) for the given JD.
"""

from .._logger import create_logger
from .._db import match_resume

logger = create_logger("match")


async def handler(context):
    body = context.request.body or {}
    resume = str(body.get("resume") or "")
    jd_id = str(body.get("jdId") or body.get("jd_id") or "")
    logger.log(f"match: jdId={jd_id!r} resume_len={len(resume)}")
    if not jd_id:
        return {"error": "jdId is required for single match"}
    try:
        return match_resume(resume, jd_id)
    except Exception as e:
        logger.error(f"match failed: {type(e).__name__}: {e}")
        return {"error": str(e)}
