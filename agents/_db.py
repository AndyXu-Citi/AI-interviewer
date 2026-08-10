"""
Data layer — private module (starts with _), not a route.

Talks to the Aliyun MySQL `final_results` table (ai_collector schema,
source_type='boss_zhipin', payload under structured_json._boss) with a JSON
seed fallback (data/seed/boss_jobs.json) so the app runs locally without a DB.
All job-retrieval, market reporting and resume matching live here. Similarity /
ranking uses LLM semantic rerank (also locked decision) with a keyword-overlap
fallback when the LLM is unavailable.
"""

from __future__ import annotations

import os
import json
import re
from typing import Any, Optional

from ._logger import create_logger

logger = create_logger("db")

# Seed is resolved from two locations, in priority order:
#   1. data/seed/boss_jobs.json    -> local dev (written by scripts/crawl_boss.py)
#   2. agents/_seed/boss_jobs.json  -> bundled with the function for EdgeOne Makers,
#      because Makers only packages the agents/ tree, not the repo-root data/ dir.
_SEED_PATHS = [
    os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed", "boss_jobs.json")
    ),
    os.path.join(os.path.dirname(__file__), "_seed", "boss_jobs.json"),
]

_CONN = None


def _load_seed() -> list[dict]:
    for _path in _SEED_PATHS:
        try:
            with open(_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("jobs", [])
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.error(f"[db] seed read failed ({_path}): {type(e).__name__}: {e}")
            continue
    logger.error("[db] seed not found in any location; returning empty")
    return []


def get_connection():
    """Return a MySQL connection, or None if not configured."""
    global _CONN
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    if not (host and user and password and database):
        return None
    try:
        import mysql.connector

        _CONN = mysql.connector.connect(
            host=host, port=int(os.getenv("DB_PORT", "3306")),
            user=user, password=password, database=database,
            charset="utf8mb4", use_unicode=True,
        )
        return _CONN
    except Exception as e:
        logger.error(f"[db] mysql connect failed: {type(e).__name__}: {e}")
        return None


def _row_to_job(r: dict) -> dict:
    skills = r.get("skills")
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except (json.JSONDecodeError, ValueError):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
    return {
        "id": r.get("id") or r.get("encrypt_job_id"),
        "title": r.get("title") or r.get("job_name"),
        "company": r.get("company") or r.get("brand_name"),
        "salary": r.get("salary") or r.get("salary_desc"),
        "city": r.get("city") or r.get("city_name"),
        "district": r.get("district") or r.get("area_district"),
        "experience": r.get("experience") or r.get("job_experience") or r.get("experience_name"),
        "education": r.get("education") or r.get("job_degree") or r.get("degree_name"),
        "skills": skills or [],
        "description": r.get("description") or r.get("post_description") or "",
        "source": r.get("source", "boss_zhipin"),
        "crawled_at": r.get("crawled_at"),
    }


def _final_row_to_job(row: dict) -> dict:
    """Convert a `final_results` row (ai_collector schema) into the job dict.

    Boss jobs store their payload under structured_json._boss (per the original
    ai_collector_project pipeline); the title lives at structured_json.title.
    """
    try:
        structured = json.loads(row.get("structured_json") or "{}")
    except (json.JSONDecodeError, ValueError):
        structured = {}
    boss = structured.get("_boss") or {}
    skills = boss.get("skills") or boss.get("skills_extracted") or []
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except (json.JSONDecodeError, ValueError):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
    return {
        "id": str(row.get("id") or ""),
        "title": structured.get("title") or boss.get("job_name") or "",
        "company": boss.get("brand_name") or boss.get("company_name") or "",
        "salary": boss.get("salary_desc") or "",
        "city": boss.get("city") or "",
        "district": boss.get("address") or "",
        "experience": boss.get("experience_name") or "",
        "education": boss.get("degree_name") or "",
        "skills": skills or [],
        "description": boss.get("post_description") or "",
        "source": "boss_zhipin",
        "crawled_at": row.get("processed_at"),
    }


def _fetch_all() -> list[dict]:
    """Return all boss_zhipin jobs from final_results (ai_collector schema).

    Falls back to the JSON seed when MySQL is not configured, unreachable,
    or the final_results table is empty.
    """
    conn = get_connection()
    if conn is None:
        return _load_seed()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, url, structured_json, processed_at FROM final_results "
            "WHERE source_type = 'boss_zhipin' ORDER BY id DESC"
        )
        rows = cur.fetchall()
        jobs = [_final_row_to_job(r) for r in rows if r.get("structured_json")]
        if not jobs:
            logger.warning("[db] final_results empty, falling back to seed")
            return _load_seed()
        return jobs
    except Exception as e:
        logger.error(f"[db] query failed, falling back to seed: {type(e).__name__}: {e}")
        return _load_seed()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_job(jd_id: str) -> Optional[dict]:
    """Fetch a single job by final_results.id (or seed id as fallback)."""
    if not jd_id:
        return None
    conn = get_connection()
    if conn is None:
        for j in _load_seed():
            if str(j.get("id")) == str(jd_id):
                return _row_to_job(j)
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, url, structured_json, processed_at FROM final_results "
            "WHERE id = %s AND source_type = 'boss_zhipin' LIMIT 1",
            (jd_id,),
        )
        row = cur.fetchone()
        if row and row.get("structured_json"):
            return _final_row_to_job(row)
        # Not found in MySQL — try the seed (e.g. seed ids when DB is partial)
        for j in _load_seed():
            if str(j.get("id")) == str(jd_id):
                return _row_to_job(j)
        return None
    except Exception as e:
        logger.error(f"[db] get_job failed: {type(e).__name__}: {e}")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def search_jobs(query: str = "", city: str = "", skill: str = "") -> list[dict]:
    """Keyword/ filter search over jobs. Returns list of job dicts (no scoring)."""
    jobs = _fetch_all()
    q = (query or "").lower()
    out = []
    for j in jobs:
        if city and city.lower() not in (j.get("city") or "").lower():
            continue
        if skill and skill.lower() not in [s.lower() for s in j.get("skills", [])]:
            continue
        if q:
            hay = " ".join([
                j.get("title", ""), j.get("company", ""),
                " ".join(j.get("skills", [])), j.get("description", ""),
            ]).lower()
            if q not in hay:
                continue
        out.append(j)
    return out


def get_report() -> dict:
    """Market report: skill frequency, city/salary/education/experience distribution."""
    jobs = _fetch_all()
    skill_freq: dict[str, int] = {}
    city_freq: dict[str, int] = {}
    edu_freq: dict[str, int] = {}
    exp_freq: dict[str, int] = {}
    salary_nums: list[int] = []
    for j in jobs:
        for s in j.get("skills", []):
            skill_freq[s] = skill_freq.get(s, 0) + 1
        c = j.get("city")
        if c:
            city_freq[c] = city_freq.get(c, 0) + 1
        e = j.get("education")
        if e:
            edu_freq[e] = edu_freq.get(e, 0) + 1
        x = j.get("experience")
        if x:
            exp_freq[x] = exp_freq.get(x, 0) + 1
        sal = j.get("salary") or ""
        nums = [int(n) for n in re.findall(r"(\d+)\s*K", sal, re.IGNORECASE) if int(n) < 200]
        if nums:
            salary_nums.append(max(nums))

    return {
        "total": len(jobs),
        "top_skills": sorted(skill_freq.items(), key=lambda x: -x[1])[:20],
        "cities": sorted(city_freq.items(), key=lambda x: -x[1])[:15],
        "education": sorted(edu_freq.items(), key=lambda x: -x[1]),
        "experience": sorted(exp_freq.items(), key=lambda x: -x[1]),
        "salary_avg_k": round(sum(salary_nums) / len(salary_nums), 1) if salary_nums else None,
    }


def _keyword_score(resume: str, job: dict) -> float:
    """Fallback relevance: fraction of job skills mentioned in the resume."""
    rv = (resume or "").lower()
    skills = [s.lower() for s in job.get("skills", [])]
    if not skills:
        return 0.0
    hit = sum(1 for s in skills if s in rv)
    return round(hit / len(skills), 3)


def _llm_rerank(resume: str, jobs: list[dict], top_k: int = 8) -> list[dict]:
    """LLM semantic rerank. Scores each candidate job 0-100 for fit to the resume."""
    client = None
    model = os.getenv("AI_GATEWAY_MODEL", "@makers/deepseek-v4-flash")
    try:
        from ._llm import get_llm_client

        client = get_llm_client()
    except Exception as e:
        logger.log(f"[db] LLM client unavailable, keyword fallback: {type(e).__name__}: {e}")

    scored = []
    for j in jobs[:top_k]:
        if client is None:
            scored.append({**j, "score": int(_keyword_score(resume, j) * 100),
                           "reason": "关键词兜底（LLM 未配置）"})
            continue
        prompt = (
            "你是招聘匹配评委。给定候选人简历摘要和目标岗位，只输出一个 0-100 的匹配分"
            "（整数）和一句理由，格式：分数|理由。\n\n"
            f"【简历摘要】\n{resume[:1500]}\n\n"
            f"【岗位】{j.get('title')} @ {j.get('company')}\n"
            f"技能：{', '.join(j.get('skills', []))}\n"
            f"要求：{j.get('description', '')[:600]}"
        )
        try:
            resp = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=120,
            )
            text = resp.choices[0].message.content.strip()
            score = 0
            reason = text
            if "|" in text:
                head, reason = text.split("|", 1)
                try:
                    score = int("".join(c for c in head if c.isdigit()) or 0)
                except ValueError:
                    score = 0
            scored.append({**j, "score": score, "reason": reason.strip()})
        except Exception as e:
            logger.error(f"[db] rerank failed for {j.get('id')}: {type(e).__name__}: {e}")
            scored.append({**j, "score": int(_keyword_score(resume, j) * 100), "reason": "关键词兜底"})
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored


def match_resume(resume: str, jd_id: Optional[str] = None) -> dict:
    """Match a resume against one JD (jd_id) or rank across all jobs."""
    if jd_id:
        job = get_job(jd_id)
        if not job:
            return {"error": f"job {jd_id!r} not found"}
        ranked = _llm_rerank(resume, [job], top_k=1)
        return {"mode": "single", "job": ranked[0] if ranked else {**job, "score": 0}}
    jobs = _fetch_all()
    # Prefilter by keyword overlap to keep LLM calls cheap.
    prefiltered = [j for j in jobs if _keyword_score(resume, j) > 0] or jobs[:20]
    ranked = _llm_rerank(resume, prefiltered, top_k=10)
    return {"mode": "rank", "ranked": ranked}


def match_rank(resume: str) -> list[dict]:
    """Rank all jobs for a resume (used by 简历匹配 -> 全部岗位)."""
    return match_resume(resume).get("ranked", [])
