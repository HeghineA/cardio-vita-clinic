#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

import psycopg


TABLES = [
    "users",
    "doctors",
    "patients",
    "appointments",
    "holters",
    "service_orders",
    "doctor_notes",
    "audit_log",
]


def insert_rows(conn, table, rows):
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    quoted_columns = ", ".join(columns)
    updates = ", ".join([f"{column} = EXCLUDED.{column}" for column in columns if column != "id"])
    conflict = "id" if "id" in columns else columns[0]
    sql = f"""
        INSERT INTO {table} ({quoted_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict}) DO UPDATE SET {updates}
    """
    with conn.cursor() as cur:
        cur.executemany(sql, [[row.get(column) for column in columns] for row in rows])
    return len(rows)


def reset_sequence(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_get_serial_sequence(%s, 'id')
            """,
            (table,),
        )
        row = cur.fetchone()
        sequence = row[0] if row else None
        if not sequence:
            return
        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        max_id = cur.fetchone()[0]
        cur.execute("SELECT setval(%s, %s, %s)", (sequence, max_id, max_id > 0))


def main():
    parser = argparse.ArgumentParser(description="Import Cardio Vita JSON export into Postgres/Supabase.")
    parser.add_argument("export_json", type=Path, help="Path to clinic_export_*.json")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="Postgres connection string")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    data = json.loads(args.export_json.read_text(encoding="utf-8"))
    with psycopg.connect(args.database_url) as conn:
        with conn.transaction():
            total = 0
            for table in TABLES:
                count = insert_rows(conn, table, data.get(table, []))
                total += count
                print(f"{table}: {count}")
            for table in TABLES:
                reset_sequence(conn, table)
        print(f"Imported rows: {total}")


if __name__ == "__main__":
    main()

