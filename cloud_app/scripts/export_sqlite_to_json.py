#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("CLINIC_DB", APP_DIR / "data" / "clinic.sqlite"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", APP_DIR / "backups"))
TABLES = [
    "users",
    "sessions",
    "patients",
    "appointments",
    "holters",
    "service_orders",
    "doctors",
    "audit_log",
    "doctor_notes",
]


def table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return bool(row)


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = BACKUP_DIR / f"clinic_export_{stamp}.json"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        data = {}
        for table in TABLES:
            if not table_exists(conn, table):
                data[table] = []
                continue
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id" if table != "sessions" else "SELECT * FROM sessions").fetchall()
            data[table] = [dict(row) for row in rows]
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

