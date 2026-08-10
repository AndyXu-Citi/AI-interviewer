"""Migrate the local ai_collector data (boss_zhipin) to the Aliyun ai_interviewer DB.

Copies urls_history / task_queue / raw_contents / final_results from the LOCAL
ai_collector MySQL (read from ai_collector_project/.env) into the Aliyun
ai_interviewer DB (DB_* env vars). INSERT IGNORE so it is idempotent.
Order respects foreign keys: urls_history -> task_queue -> raw_contents/final_results.
"""
import json
import os
import sys

import mysql.connector


def read_env(path):
    d = {}
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return d


def connect(cfg, database=None):
    return mysql.connector.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                                   password=cfg["password"], database=database,
                                   connection_timeout=10)


def main() -> int:
    # Local (source)
    local_env = read_env(os.path.join(os.path.dirname(__file__), "..", "..",
                                      "ai_collector_project", ".env"))
    src = {
        "host": local_env.get("DB_HOST", "127.0.0.1"),
        "port": int(local_env.get("DB_PORT", "3306")),
        "user": local_env.get("DB_USER", "root"),
        "password": local_env.get("DB_PASSWORD", ""),
        "database": local_env.get("DB_NAME", "ai_collector"),
    }
    # Aliyun (target)
    dst = {
        "host": os.getenv("DB_HOST", "47.101.167.103"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "ai_interviewer"),
    }
    if not dst["password"]:
        print("DB_PASSWORD (target) not set")
        return 1

    print(f"source: {src['user']}@{src['host']}:{src['port']}/{src['database']}")
    print(f"target: {dst['user']}@{dst['host']}:{dst['port']}/{dst['database']}")

    src_conn = connect(src, src["database"])
    dst_conn = connect(dst, dst["database"])
    sc = src_conn.cursor(dictionary=True)
    dc = dst_conn.cursor()

    def copy_table(table, columns, extra_where="", limit=None):
        where = f" WHERE {extra_where}" if extra_where else ""
        lim = f" LIMIT {int(limit)}" if limit else ""
        sc.execute(f"SELECT {columns} FROM {table}{where}{lim}")
        rows = sc.fetchall()
        if not rows:
            print(f"[{table}] 0 rows")
            return 0
        cols = columns.split(",")
        marks = ",".join(["%s"] * len(cols))
        sql = (f"INSERT IGNORE INTO {table} ({', '.join(cols)}) "
               f"VALUES ({marks})")
        n = 0
        for r in rows:
            vals = tuple(r[c.strip()] for c in cols)
            dc.execute(sql, vals)
            n += dc.rowcount if dc.rowcount != -1 else 1
        dst_conn.commit()
        print(f"[{table}] copied {n}/{len(rows)}")
        return len(rows)

    # Foreign-key order matters
    copy_table("urls_history", "url, first_seen_at, last_seen_at")
    copy_table("task_queue", "id, url, status, source_type, retry_count, "
                              "error_message, last_attempt_at, created_at")
    copy_table("raw_contents", "url, markdown_text, collected_at")
    copy_table("final_results", "id, url, source_type, structured_json, processed_at",
               extra_where="source_type='boss_zhipin'")

    # Verify
    for t in ["urls_history", "task_queue", "raw_contents", "final_results"]:
        dc.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"[verify] {t}: {dc.fetchone()[0]}")
    dc.execute("SELECT COUNT(*) FROM final_results WHERE source_type='boss_zhipin'")
    print(f"[verify] final_results boss_zhipin: {dc.fetchone()[0]}")

    sc.close()
    dc.close()
    src_conn.close()
    dst_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
