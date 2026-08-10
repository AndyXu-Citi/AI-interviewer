"""Jobs handler — EdgeOne Makers Python cloud function.

POST /jobs
  Body:    { "query": str, "city": str, "skill": str }
  Returns: { "total": int, "jobs": Job[] }
"""

import json
import os
import sys
import time
import traceback

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from agents._db import search_jobs
from _logger import create_logger

logger = create_logger("jobs")


def _read_body(rfile, headers) -> dict:
    length = int(headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    try:
        return json.loads(rfile.read(length).decode("utf-8")) or {}
    except (ValueError, UnicodeDecodeError):
        return {}


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
        query = str(body.get("query") or "")
        city = str(body.get("city") or "")
        skill = str(body.get("skill") or "")
        logger.log(f"jobs: query={query!r} city={city!r} skill={skill!r}")
        try:
            jobs = search_jobs(query=query, city=city, skill=skill)
            elapsed = int((time.time() - start) * 1000)
            logger.log(f"jobs: {len(jobs)} results in {elapsed}ms")
            self._write_json(200, {"total": len(jobs), "jobs": jobs})
        except Exception as e:
            logger.error(f"jobs failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            self._write_json(200, {"total": 0, "jobs": []})
