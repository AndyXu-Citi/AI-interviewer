#!/usr/bin/env python
"""
Local Boss Zhipin crawler (LOCAL ONLY — never deployed to EdgeOne).

EdgeOne's serverless / Agents runtime has no browser, so this script lives on
your machine. It scrapes Boss Zhipin job cards via Playwright + CDP (to dodge
WebDriver detection), normalizes them to the `jobs` schema, and writes
`data/seed/boss_jobs.json`. The cloud app reads that file (or the MySQL `jobs`
table) — it never triggers crawling itself.

Usage:
    python scripts/crawl_boss.py --keyword "AI应用开发工程师" --city "上海" --pages 5

Env / args:
    --keyword   search keyword
    --city      city name (maps to Boss city code internally)
    --pages     max pages to crawl
    --cdp       optional CDP websocket url (e.g. from a logged-in Chrome)
    COOKIES_TXT optional path to a cookies.txt exported from your logged-in session

Requires: pip install playwright  (and `playwright install chromium`)
NOTE: scraping Boss Zhipin may violate its ToS. Use only on data you are
authorized to access, and rate-limit aggressively.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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


def _normalize(card: dict) -> dict:
    """Normalize a Boss job card / jobList item to the `jobs` schema."""
    sec = card.get("securityId") or card.get("encryptJobId") or card.get("lid") or ""
    skills = card.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    return {
        "id": card.get("encryptJobId") or sec,
        "title": card.get("jobName") or card.get("title"),
        "company": card.get("brandName") or card.get("company"),
        "salary": card.get("salaryDesc") or card.get("salary"),
        "city": card.get("cityName") or card.get("city"),
        "district": card.get("areaDistrict") or card.get("district"),
        "experience": card.get("jobExperience") or card.get("experienceName") or card.get("experience"),
        "education": card.get("jobDegree") or card.get("degreeName") or card.get("education"),
        "skills": skills,
        "description": card.get("postDescription") or card.get("description") or "",
        "source": "boss_zhipin",
        "crawled_at": int(time.time() * 1000),
    }


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

    os.makedirs(os.path.dirname(SEED_PATH), exist_ok=True)
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"[crawl] wrote {SEED_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
