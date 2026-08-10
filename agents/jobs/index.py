"""
Jobs handler — EdgeOne Makers (agents route)
============================================
File path agents/jobs/index.py is auto-mapped to **POST /jobs**.

Body:    { "query": str, "city": str, "skill": str }
Returns: { "total": int, "jobs": Job[] }
"""

from .._logger import create_logger
from .._db import search_jobs

logger = create_logger("jobs")


async def handler(context):
    body = context.request.body or {}
    query = str(body.get("query") or "")
    city = str(body.get("city") or "")
    skill = str(body.get("skill") or "")
    logger.log(f"jobs: query={query!r} city={city!r} skill={skill!r}")
    try:
        jobs = search_jobs(query=query, city=city, skill=skill)
        logger.log(f"jobs: {len(jobs)} results")
        return {"total": len(jobs), "jobs": jobs}
    except Exception as e:
        logger.error(f"jobs failed: {type(e).__name__}: {e}")
        return {"total": 0, "jobs": []}
