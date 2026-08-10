"""Create the 5 ai_collector-style tables on the Aliyun `ai_interviewer` DB.

DDL is copied verbatim from ai_collector_project/src/db_manager.py so the two
databases stay schema-compatible.
"""
import os
import sys

import mysql.connector

HOST = os.getenv("DB_HOST", "47.101.167.103")
PORT = int(os.getenv("DB_PORT", "3306"))
USER = os.getenv("DB_USER", "root")
PASSWORD = os.getenv("DB_PASSWORD", "")
DBNAME = os.getenv("DB_NAME", "ai_interviewer")

DDL_DATABASE = f"""
CREATE DATABASE IF NOT EXISTS `{DBNAME}`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
"""

DDL_TABLES = """
CREATE TABLE IF NOT EXISTS urls_history (
    url             VARCHAR(255) PRIMARY KEY,
    first_seen_at   DATETIME,
    last_seen_at    DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS task_queue (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    url             VARCHAR(255) UNIQUE,
    status          VARCHAR(20) DEFAULT 'PENDING',
    source_type     VARCHAR(50) DEFAULT 'bilibili',
    retry_count     INT DEFAULT 0,
    error_message   TEXT,
    last_attempt_at DATETIME,
    created_at      DATETIME,
    INDEX idx_tq_status (status),
    INDEX idx_tq_source (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS raw_contents (
    url             VARCHAR(255) PRIMARY KEY,
    markdown_text   LONGTEXT,
    collected_at    DATETIME,
    FOREIGN KEY (url) REFERENCES task_queue(url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS final_results (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    url             VARCHAR(255),
    source_type     VARCHAR(50) DEFAULT 'bilibili',
    structured_json LONGTEXT,
    processed_at    DATETIME,
    INDEX idx_fr_source (source_type),
    INDEX idx_fr_url (url),
    FOREIGN KEY (url) REFERENCES task_queue(url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_runs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    run_at          DATETIME NOT NULL,
    query           TEXT NOT NULL,
    result_count    INT NOT NULL,
    elapsed_seconds FLOAT DEFAULT 0,
    reflect_rounds  INT DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'unreviewed',
    root_cause      TEXT,
    fix_commit      VARCHAR(40) DEFAULT '',
    fix_notes       TEXT,
    trace_json      LONGTEXT,
    final_report    LONGTEXT,
    INDEX idx_ar_status (status),
    INDEX idx_ar_run_at (run_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def main() -> int:
    if not PASSWORD:
        print("DB_PASSWORD not set")
        return 1
    conn = mysql.connector.connect(host=HOST, port=PORT, user=USER, password=PASSWORD,
                                   connection_timeout=8)
    cur = conn.cursor()
    cur.execute(DDL_DATABASE)
    conn.database = DBNAME
    for stmt in DDL_TABLES.split(";"):
        s = stmt.strip()
        if s and s.upper().startswith("CREATE"):
            cur.execute(s + ";")
    conn.commit()
    cur.execute("SHOW TABLES")
    print("tables:", [r[0] for r in cur.fetchall()])
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
