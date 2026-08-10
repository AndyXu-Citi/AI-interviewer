"""Match handler — EdgeOne Makers Python cloud function.

POST /match
  Body:    { "resume": str, "jdId": str }
  Returns: single-JD match breakdown (score + reason) for the given JD.
"""

import json
import os
import sys
import time
import traceback

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from agents._db import match_resume
from _logger import create_logger

logger = create_logger("match")


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
        resume = str(body.get("resume") or "")
        jd_id = str(body.get("jdId") or "")
        logger.log(f"match: jdId={jd_id!r} resume_len={len(resume)}")
        if not jd_id:
            self._write_json(200, {"error": "jdId is required for single match"})
            return
        try:
            result = match_resume(resume, jd_id)
            elapsed = int((time.time() - start) * 1000)
            logger.log(f"match done in {elapsed}ms")
            self._write_json(200, result)
        except Exception as e:
            logger.error(f"match failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            self._write_json(200, {"error": str(e)})
