#!/usr/bin/env python
"""
Local Boss Zhipin crawler (LOCAL ONLY — never deployed to EdgeOne).

EdgeOne's serverless / Agents runtime has no browser, so this script lives on
your machine. It scrapes Boss Zhipin job cards via Playwright + CDP (to dodge
WebDriver detection), normalizes them to the ai_collector pipeline schema and
writes them into MySQL `final_results` (source_type='boss_zhipin', payload under
structured_json._boss) — exactly the schema ai_collector_project uses. It also
mirrors the data to data/seed/boss_jobs.json so the cloud app has a JSON
fallback. The cloud app reads the DB / JSON; it never triggers crawling.

Usage:
    python scripts/crawl_boss.py --keyword "AI应用开发工程师" --city "上海" --pages 5

Env / args:
    --keyword   search keyword
    --city      city name (maps to Boss city code internally)
    --pages     max pages to crawl
    --cdp       optional CDP websocket url (e.g. from a logged-in Chrome)
    COOKIES_TXT optional path to a cookies.txt exported from your logged-in session
    DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME  MySQL target (optional; skips DB write if unset)

Requires: pip install playwright  (and `playwright install chromium`)
NOTE: scraping Boss Zhipin may violate its ToS. Use only on data you are
authorized to access, and rate-limit aggressively.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed", "boss_jobs.json")
)

# Boss city name -> code (partial; extend as needed).
CITY_CODES = {
    "北京": "101010100", "上海": "101020100", "广州": "101280100", "深圳": "101280600",
    "杭州": "101210100", "成都": "101270100", "南京": "101190100", "武汉": "101200100",
    "西安": "101110100", "苏州": "101190400", "厦门": "101230200", "长沙": "101250100",
}


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return list(v)


def _normalize(card: dict) -> dict:
    """Normalize a Boss jobList item to the ai_collector final_results schema.

    Payload mirrors ai_collector_project/src/mcp_server/ai_collector_mcp.py:
    title lives at structured_json.title, the rest under structured_json._boss.
    """
    skills = _as_list(card.get("skills"))
    labels = _as_list(card.get("detailLabels"))
    return {
        "id": card.get("encryptJobId") or card.get("securityId") or card.get("lid") or "",
        "title": card.get("jobName") or card.get("title") or "",
        "structured_json": {
            "title": card.get("jobName") or card.get("title") or "",
            "summary": card.get("summary") or "",
            "_boss": {
                "brand_name": card.get("brandName") or card.get("company") or "",
                "salary_desc": card.get("salaryDesc") or card.get("salary") or "",
                "city": card.get("cityName") or card.get("city") or "",
                "address": card.get("areaDistrict") or card.get("district") or "",
                "experience_name": (card.get("jobExperience") or card.get("experienceName")
                                    or card.get("experience") or ""),
                "degree_name": (card.get("jobDegree") or card.get("degreeName")
                                or card.get("education") or ""),
                "skills": skills,
                "detail_labels": labels,
                "post_description": card.get("postDescription") or card.get("description") or "",
                "encrypt_job_id": card.get("encryptJobId") or "",
                "security_id": card.get("securityId") or "",
                "lid": card.get("lid") or "",
                "boss_name": card.get("bossName") or "",
                "boss_title": card.get("bossTitle") or "",
            },
        },
        "source": "boss_zhipin",
        "crawled_at": int(time.time() * 1000),
    }


def _flat_seed(norm: dict) -> dict:
    """Flatten a normalized job back to the simple seed JSON shape (JSON fallback)."""
    b = norm["structured_json"]["_boss"]
    return {
        "id": norm["id"],
        "title": norm["title"],
        "company": b["brand_name"],
        "salary": b["salary_desc"],
        "city": b["city"],
        "district": b["address"],
        "experience": b["experience_name"],
        "education": b["degree_name"],
        "skills": b["skills"],
        "description": b["post_description"],
        "source": norm["source"],
    }


def _save_to_mysql(jobs: list[dict]) -> int:
    """Persist jobs into MySQL final_results (ai_collector schema). Returns rows written."""
    if not (os.getenv("DB_HOST") and os.getenv("DB_PASSWORD")):
        print("[db] DB_* not configured — skipping MySQL write")
        return 0
    import mysql.connector

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "ai_interviewer"), connection_timeout=10,
    )
    cur = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    written = 0
    for j in jobs:
        url = f"https://www.zhipin.com/job_detail/{j['id']}.html"
        cur.execute(
            "INSERT IGNORE INTO urls_history (url, first_seen_at, last_seen_at) "
            "VALUES (%s, %s, %s)", (url, now, now),
        )
        cur.execute(
            "INSERT IGNORE INTO task_queue (url, status, source_type, created_at) "
            "VALUES (%s, 'COMPLETED', 'boss_zhipin', %s)", (url, now),
        )
        cur.execute(
            "INSERT INTO final_results (url, source_type, structured_json, processed_at) "
            "VALUES (%s, 'boss_zhipin', %s, %s)",
            (url, json.dumps(j["structured_json"], ensure_ascii=False), now),
        )
        written += cur.rowcount if cur.rowcount != -1 else 1
    conn.commit()
    cur.close()
    conn.close()
    return written


def _strip_webdriver(page) -> None:
    """Best-effort stealth: nuke navigator.webdriver before any script runs."""
    try:
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
    except Exception:
        pass


def crawl(keyword: str, city: str, pages: int, cdp: str | None) -> list[dict]:
    from playwright.sync_api import sync_playwright

    city_code = CITY_CODES.get(city, "")
    collected: dict[str, dict] = {}

    with sync_playwright() as p:
        if cdp:
            browser = p.chromium.connect_over_cdp(cdp)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
        else:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
        page = context.new_page()
        _strip_webdriver(page)

        # Intercept the job-list API responses.
        def on_response(response):
            try:
                if "zpgeek/search/joblist" in response.url or "zpData" in response.url:
                    data = response.json()
                    zp = (data or {}).get("zpData", {})
                    for item in zp.get("jobList", []) or []:
                        norm = _normalize(item)
                        if norm.get("id"):
                            collected[norm["id"]] = norm
                    card = zp.get("jobCard")
                    if card:
                        norm = _normalize(card)
                        if norm.get("id"):
                            collected[norm["id"]] = norm
            except Exception:
                pass

        page.on("response", on_response)

        q = os.path.join(
            "https://www.zhipin.com/web/geek/job",
            f"?query={keyword}&city={city_code}" if city_code else f"?query={keyword}",
        )
        page.goto(q, wait_until="networkidle", timeout=30000)
        for _ in range(max(1, pages)):
            page.mouse.wheel(0, 4000)
            time.sleep(2.5)
            # Click "next page" if present.
            try:
                page.get_by_text("下一页", exact=True).click(timeout=1500)
                time.sleep(2.5)
            except Exception:
                break
        context.close()
        browser.close()

    return list(collected.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="Local Boss Zhipin crawler")
    ap.add_argument("--keyword", default="AI应用开发工程师")
    ap.add_argument("--city", default="上海")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--cdp", default=os.getenv("BOSS_CDP"))
    args = ap.parse_args()

    print(f"[crawl] keyword={args.keyword!r} city={args.city!r} pages={args.pages}")
    jobs = crawl(args.keyword, args.city, args.pages, args.cdp)
    print(f"[crawl] collected {len(jobs)} jobs")

    # 1) MySQL final_results (ai_collector schema)
    written = _save_to_mysql(jobs)
    print(f"[db] wrote {written} rows to final_results")

    # 2) JSON seed fallback (flat shape, same as before)
    os.makedirs(os.path.dirname(SEED_PATH), exist_ok=True)
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump([_flat_seed(j) for j in jobs], f, ensure_ascii=False, indent=2)
    print(f"[crawl] wrote {SEED_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
