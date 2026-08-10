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


def _fix_utf8(obj):
    """修复 MySQL 默认 latin1 连接导致的 mojibake。

    MySQL 在没声明 charset 时会把 utf8mb4 字段里的 UTF-8 字节按 latin1
    交给 Python，于是中文变成 'Agentå¼€å...'。latin1 是单字节编码，
    任何字节序列都合法，所以 encode('latin1') 可以还原原始字节，再用
    utf-8 解码即可恢复中文。如果字符串本身已是正确中文（Unicode 码点
    >255 无法 encode 为 latin1），直接返回原值，不会破坏 seed 数据。
    """
    if isinstance(obj, str):
        try:
            return obj.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return obj
    if isinstance(obj, list):
        return [_fix_utf8(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _fix_utf8(v) for k, v in obj.items()}
    return obj


async def handler(context):
    body = context.request.body or {}
    query = str(body.get("query") or "")
    city = str(body.get("city") or "")
    skill = str(body.get("skill") or "")
    logger.log(f"jobs: query={query!r} city={city!r} skill={skill!r}")
    try:
        jobs = search_jobs(query=query, city=city, skill=skill)
        jobs = _fix_utf8(jobs)
        logger.log(f"jobs: {len(jobs)} results")
        return {"total": len(jobs), "jobs": jobs}
    except Exception as e:
        logger.error(f"jobs failed: {type(e).__name__}: {e}")
        return {"total": 0, "jobs": []}
