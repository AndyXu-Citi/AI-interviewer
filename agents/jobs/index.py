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


def _fix(obj):
    """修复数据库里已存储的 latin1 mojibake：encode('latin1') 还原原始字节，
    再 decode('utf-8') 恢复中文。对正常中文字符串安全（UnicodeEncodeError 时原样返回）。
    """
    if isinstance(obj, str):
        try:
            return obj.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return obj
    if isinstance(obj, list):
        return [_fix(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _fix(v) for k, v in obj.items()}
    return obj


async def handler(context):
    body = context.request.body or {}
    query = str(body.get("query") or "")
    city = str(body.get("city") or "")
    skill = str(body.get("skill") or "")
    logger.log(f"jobs: query={query!r} city={city!r} skill={skill!r}")
    try:
        jobs = search_jobs(query=query, city=city, skill=skill)
        jobs = _fix(jobs)
        logger.log(f"jobs: {len(jobs)} results")
        return {"total": len(jobs), "jobs": jobs}
    except Exception as e:
        logger.error(f"jobs failed: {type(e).__name__}: {e}")
        return {"total": 0, "jobs": []}
