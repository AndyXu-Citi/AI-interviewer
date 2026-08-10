"""
Report handler — EdgeOne Makers (agents route)
==============================================
File path agents/report/index.py is auto-mapped to **POST /report**.

Body:    {} (optional)
Returns: market report (skill frequency, city/salary/education/experience distribution)
"""

from .._logger import create_logger
from .._db import get_report

logger = create_logger("report")


async def handler(context):
    try:
        report = get_report()
        logger.log(f"report: total={report.get('total')}")
        return report
    except Exception as e:
        logger.error(f"report failed: {type(e).__name__}: {e}")
        return {"total": 0, "top_skills": [], "cities": [],
                "education": [], "experience": [], "salary_avg_k": None}
