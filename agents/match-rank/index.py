"""
Match-rank handler — EdgeOne Makers (agents route)
==================================================
File path agents/match-rank/index.py is auto-mapped to **POST /match-rank**.

Body:    { "resume": str }
Returns: resume ranked against ALL jobs (LLM semantic rerank).
"""

from .._logger import create_logger
from .._db import match_resume

logger = create_logger("match-rank")


async def handler(context):
    body = context.request.body or {}
    resume = str(body.get("resume") or "")
    logger.log(f"match-rank: resume_len={len(resume)}")
    if not resume:
        return {"mode": "rank", "ranked": []}
    try:
        return match_resume(resume)
    except Exception as e:
        logger.error(f"match-rank failed: {type(e).__name__}: {e}")
        return {"mode": "rank", "ranked": []}
