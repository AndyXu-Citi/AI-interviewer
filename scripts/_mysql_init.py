"""
MySQL bootstrap for the AI-interviewer app.

Creates the `ai_interviewer` database + `jobs` table (fields aligned with
agents/_db.py) and seeds it from data/seed/boss_jobs.json.

Usage:
    python scripts/_mysql_init.py
Config via env: DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
Defaults below match the app's .env.example.
"""
import json
import os
import sys

import mysql.connector

HOST = os.getenv("DB_HOST", "47.101.167.103")
PORT = int(os.getenv("DB_PORT", "3306"))
USER = os.getenv("DB_USER", "root")
PASSWORD = os.getenv("DB_PASSWORD", "")
DBNAME = os.getenv("DB_NAME", "ai_interviewer")
SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "seed", "boss_jobs.json")

CREATE_DB = (
    f"CREATE DATABASE IF NOT EXISTS `{DBNAME}` "
    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS `jobs` (
  `id` VARCHAR(64) NOT NULL,
  `encrypt_job_id` VARCHAR(64) DEFAULT NULL,
  `title` VARCHAR(255) NOT NULL,
  `company` VARCHAR(255) DEFAULT NULL,
  `salary` VARCHAR(64) DEFAULT NULL,
  `city` VARCHAR(64) DEFAULT NULL,
  `district` VARCHAR(64) DEFAULT NULL,
  `experience` VARCHAR(64) DEFAULT NULL,
  `education` VARCHAR(64) DEFAULT NULL,
  `skills` TEXT,
  `description` TEXT,
  `source` VARCHAR(32) DEFAULT 'boss_zhipin',
  `crawled_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_city` (`city`),
  KEY `idx_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def main() -> int:
    if not PASSWORD:
        print("DB_PASSWORD not set — aborting.")
        return 1

    conn = mysql.connector.connect(host=HOST, port=PORT, user=USER, password=PASSWORD,
                                   connection_timeout=8)
    cur = conn.cursor()
    cur.execute(CREATE_DB)
    conn.database = DBNAME
    cur.execute(CREATE_TABLE)
    conn.commit()
    print(f"[ok] database `{DBNAME}` ready, table `jobs` ready")

    # Seed
    with open(SEED, encoding="utf-8") as f:
        raw = json.load(f)
    jobs = raw if isinstance(raw, list) else raw.get("jobs", [])
    if not jobs:
        print("[warn] seed file empty, nothing to import")
    ins = (
        "INSERT INTO `jobs` (id, encrypt_job_id, title, company, salary, city, district, "
        "experience, education, skills, description, source, crawled_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW()) "
        "ON DUPLICATE KEY UPDATE "
        "title=VALUES(title), company=VALUES(company), salary=VALUES(salary), "
        "city=VALUES(city), district=VALUES(district), experience=VALUES(experience), "
        "education=VALUES(education), skills=VALUES(skills), description=VALUES(description)"
    )
    n = 0
    for j in jobs:
        skills = j.get("skills") or []
        cur.execute(ins, (
            j.get("id"), j.get("id"),
            j.get("title", ""), j.get("company"), j.get("salary"), j.get("city"),
            j.get("district"), j.get("experience"), j.get("education"),
            json.dumps(skills, ensure_ascii=False), j.get("description", ""),
            j.get("source", "boss_zhipin"),
        ))
        n += cur.rowcount if cur.rowcount != -1 else 1
    conn.commit()
    print(f"[ok] upserted {n} rows from {SEED}")

    cur.execute("SELECT COUNT(*) FROM jobs")
    print(f"[ok] total rows in jobs = {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
