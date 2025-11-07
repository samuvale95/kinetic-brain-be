#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python - <<'PY'
from sqlalchemy import inspect, text
from app.database import engine

SCHEMAS = ["public"]
SKIP_TABLES = {"alembic_version"}

inspector = inspect(engine)

tables = []
for schema in SCHEMAS:
    for table in inspector.get_table_names(schema=schema):
        if table not in SKIP_TABLES:
            tables.append((schema, table))

with engine.begin() as conn:
    if not tables:
        print("No tables found to truncate.")
    else:
        fq_tables = ", ".join(f'"{schema}"."{table}"' for schema, table in tables)
        stmt = text(f"TRUNCATE TABLE {fq_tables} RESTART IDENTITY CASCADE")
        conn.execute(stmt)
        print(f"Truncated tables: {', '.join(table for _, table in tables)}")
PY

