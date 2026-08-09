#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

import psycopg


def main():
    parser = argparse.ArgumentParser(description="Run a SQL file against DATABASE_URL.")
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    sql = args.sql_file.read_text(encoding="utf-8")
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"Executed {args.sql_file}")


if __name__ == "__main__":
    main()
