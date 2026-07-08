#!/usr/bin/env python3
"""Dump a SQLite database schema in deterministic (sorted) order.

Replaces ``sqlite3 <db> .schema`` whose output order depends on
``sqlite_master`` insertion order and varies between Alembic runs.

This script emits:
  1. CREATE TABLE statements sorted alphabetically by table name.
  2. Immediately after each table, its CREATE INDEX / CREATE UNIQUE INDEX
     statements sorted alphabetically by index name.

The result is a DDL file that only diffs on actual schema changes,
eliminating the ~40-line reordering noise observed across regenerations.

Usage:
    python tools/deterministic_schema_dump.py <db_path> [output_path]

If *output_path* is omitted the DDL is written to stdout.
"""
import sqlite3
import sys
from collections import defaultdict


def dump_deterministic(db_path):
    """Return the schema DDL as a deterministic string."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ---- Collect all objects from sqlite_master ----
    rows = cursor.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL ORDER BY type, name"
    ).fetchall()

    # Separate tables from indexes (and any other types like views/triggers).
    tables = {}  # name -> sql
    # Map table_name -> list of (index_name, sql)
    indexes_by_table = defaultdict(list)
    # Standalone indexes not tied to a table (shouldn't happen, but be safe)
    other_objects = []

    for obj_type, name, tbl_name, sql in rows:
        if obj_type == "table":
            if name == "sqlite_sequence":
                continue
            tables[name] = sql
        elif obj_type == "index":
            indexes_by_table[tbl_name].append((name, sql))
        else:
            other_objects.append((obj_type, name, sql))

    # ---- Emit DDL in sorted order ----
    parts = []

    # Tables sorted by name, each followed by its indexes sorted by name.
    for table_name in sorted(tables):
        parts.append(tables[table_name] + ";")
        for _idx_name, idx_sql in sorted(indexes_by_table.get(table_name, []), key=lambda x: x[0]):
            parts.append(idx_sql + ";")

    # Any other object types (views, triggers) sorted by type then name.
    for _obj_type, _name, sql in sorted(other_objects, key=lambda x: (x[0], x[1])):
        parts.append(sql + ";")

    conn.close()
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <db_path> [output_path]", file=sys.stderr)
        sys.exit(1)

    db_path = sys.argv[1]
    output = dump_deterministic(db_path)

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w") as f:
            f.write(output)
    else:
        sys.stdout.write(output)
