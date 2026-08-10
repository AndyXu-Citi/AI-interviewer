"""Profile handler — EdgeOne Makers Python cloud function.

POST /profile
  Body:    { "resume": str }
  Returns: candidate skill profile + market gap analysis.
"""

import json
import os
import sys
import time
import traceback

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from agents._db import get_report
from _logger import create_logger

logger = create_logger("profile")


def _read_body(rfile, headers) -> dict:
    length = int(headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    try:
        return json.loads(rfile.read(length).decode("utf-8")) or {}
    except (ValueError, UnicodeDecodeError):
        return {}


def _extract_skills(resume: str) -> list[str]:
    """Extract candidate skills from resume text (LLM, with keyword fallback)."""
    try:
        from agents._llm import get_llm_client

        client = get_llm_client()
        model = os.getenv("AI_GATEWAY_MODEL", "@makers/deepseek-v4-flash")
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": "从下面的简历中提取候选人掌握的技能关键词，用逗号分隔，只输出技能词，不要解释。\n\n"
                + resume[:2000],
            }],
            temperature=0.2, max_tokens=200,
        )
        text = resp.choices[0].message.content or ""
        return [s.strip() for s in text.split(",") if s.strip()]
    except Exception as e:
        logger.error(f"profile skill extraction failed: {type(e).__name__}: {e}")
        # Fallback: surface words that look like tech skills.
        import re
        return sorted(set(re.findall(r"\b([A-Za-z][A-Za-z0-9\+\#\.]{1,20})\b", resume)))


class handler(BaseHTTPRequestHandler):
    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        start = time.time()
        body = _read_body(self.rfile, self.headers)
        resume = str(body.get("resume") or "")
        logger.log(f"profile: resume_len={len(resume)}")
        if not resume:
            self._write_json(200, {"skills": [], "market_top": [], "gaps": []})
            return
        try:
            skills = _extract_skills(resume)
            report = get_report()
            market_top = [s for s, _ in report.get("top_skills", [])]
            skill_lc = {s.lower() for s in skills}
            gaps = [m for m in market_top if m.lower() not in skill_lc]
            elapsed = int((time.time() - start) * 1000)
            logger.log(f"profile: {len(skills)} skills, {len(gaps)} gaps in {elapsed}ms")
            self._write_json(200, {
                "skills": skills,
                "market_top": market_top,
                "gaps": gaps[:15],
            })
        except Exception as e:
            logger.error(f"profile failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            self._write_json(200, {"skills": [], "market_top": [], "gaps": []})
