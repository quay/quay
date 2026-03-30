#!/usr/bin/env python3
"""Generate a deterministic structural fingerprint of a SQLite database.

Uses PRAGMAs (table_info, foreign_key_list, index_list, index_info)
to produce output that is identical regardless of DDL text ordering.
Sorts FKs and indexes within each table. Includes row counts.

Usage: python tools/schema_fingerprint.py <db_path>
"""
import re
import sqlite3
import sys


def fingerprint(db_path):
    db = sqlite3.connect(db_path)
    tables = db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name != 'sqlite_sequence' "
        "ORDER BY name"
    ).fetchall()

    for (table,) in tables:
        print(f"TABLE {table}")

        # Columns (deterministic order from table_info)
        for row in db.execute(f"PRAGMA table_info('{table}')"):
            cid, name, col_type, notnull, default, pk = row
            # Strip timestamp defaults (change every alembic run)
            if default and re.match(r"^'\d{4}-\d{2}-\d{2}", str(default)):
                default = "'<timestamp>'"
            print(f"  COL {cid} {name} {col_type} notnull={notnull} default={default} pk={pk}")

        # Foreign keys (sorted for determinism)
        fks = db.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
        for fk in sorted(fks, key=lambda r: (r[2], r[3])):
            _, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            print(f"  FK {from_col} -> {ref_table}({to_col})")

        # Indexes (sorted by name for determinism)
        indexes = db.execute(f"PRAGMA index_list('{table}')").fetchall()
        for idx in sorted(indexes, key=lambda r: r[1]):
            _, idx_name, unique, origin, partial = idx
            cols = db.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
            col_names = ",".join(r[2] for r in sorted(cols, key=lambda r: r[0]))
            print(f"  IDX {idx_name} unique={unique} cols={col_names}")

        # Row count
        count = db.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
        print(f"  ROWS {count}")

    db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <db_path>", file=sys.stderr)
        sys.exit(1)
    fingerprint(sys.argv[1])
