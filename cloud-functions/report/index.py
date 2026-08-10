"""Report handler — EdgeOne Makers Python cloud function.

POST /report
  Body:    {} (optional)
  Returns: market report (skill frequency, city/salary/education/experience distribution)
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

logger = create_logger("report")


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
        _read_body(self.rfile, self.headers)
        try:
            report = get_report()
            elapsed = int((time.time() - start) * 1000)
            logger.log(f"report: total={report.get('total')} in {elapsed}ms")
            self._write_json(200, report)
        except Exception as e:
            logger.error(f"report failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            self._write_json(200, {"total": 0, "top_skills": [], "cities": [],
                                    "education": [], "experience": [], "salary_avg_k": None})
