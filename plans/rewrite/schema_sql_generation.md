# Schema SQL Generation for Go Parity

Status: Draft
Last updated: 2026-03-02

## 1. Purpose

Define the mechanism for generating a canonical PostgreSQL schema snapshot from Alembic HEAD and maintaining it in the repository, so the Go DAL (`sqlc`) always operates against an accurate schema definition.

Implementation architecture references:
- `plans/rewrite/data_access_layer_design.md` (§4, §5.2, §10)
- `plans/rewrite/db_migration_policy.md` (§10)

## 2. Problem

During mixed-runtime coexistence, both Python (Peewee/Alembic) and Go (sqlc) must agree on the database schema. Schema changes arrive via Alembic migrations authored against Peewee models. Go's sqlc uses a schema snapshot (`internal/dal/sql/schema/postgres/schema.sql`) as input for code generation. Without an automated check, the Go-side schema snapshot can silently diverge from Alembic HEAD, causing runtime query failures or data corruption.

## 3. Approach selection

### 3.1 `pg_dump --schema-only` after `alembic upgrade head` (selected)

Apply all Alembic migrations to an ephemeral PostgreSQL instance, then dump the resulting schema.

Rationale:
- Captures the exact schema PostgreSQL produces — all columns, types, constraints, indexes, sequences, extensions.
- Handles all migration patterns: custom `op.execute()` DDL, runtime introspection (`Inspector.from_engine()`), conditional logic (`if bind.engine.name == "postgresql"`).
- Deterministic: same PostgreSQL version + same migrations + empty database = same OID assignment = same `pg_dump` ordering.

### 3.2 SQLAlchemy `metadata.create_all()` DDL generation (rejected)

Use `data/model/sqlalchemybridge.py` to convert Peewee models → SQLAlchemy metadata → DDL.

Rejected because:
- 39 migration files use `op.execute()` for custom DDL (e.g., `ALTER SEQUENCE manifestblob_id_seq AS BIGINT` in `e8ed3fb547da`) not representable in Peewee models.
- The bridge does not handle custom field types (`EncryptedCharField`, `JSONField`, `CredentialField`) with full fidelity — they pass through as base types.
- Would produce a schema that diverges from what is actually in production.

### 3.3 Alembic offline mode `--sql` (rejected)

Generate SQL without running against a database.

Rejected because:
- Produces migration-ordered output (sequential ALTER/CREATE from 100+ migrations), not a clean final-state snapshot.
- Many migrations use runtime introspection (`Inspector.from_engine(bind)`) and conditional execution that cannot run offline.
- Would require post-processing equivalent to running a SQL engine anyway.

### 3.4 Atlas schema inspection (deferred)

Atlas (`atlasgo.io`) can inspect a database and produce normalized schema output.

Deferred because:
- Still requires a running database, so no savings over `pg_dump`.
- Adds a dependency for no additional benefit at this stage.
- sqlc needs plain SQL, not Atlas HCL.
- Atlas could be evaluated as Go migration tooling at M5 (see `db_migration_policy.md` §10.7), but that is a separate decision.

## 4. Generation script: `scripts/sync-sqlc-schema.sh`

Referenced by `db_migration_policy.md` §10.6.

### 4.1 Steps

1. Start ephemeral PostgreSQL 18 container (port 15432, PID-suffixed container name to avoid collisions).
2. Wait for PostgreSQL readiness via `pg_isready`.
3. Create `pg_trgm` extension (required for GIN fulltext indexes on `repository.name` and `repository.description`, matching `local-dev/init/pg_bootstrap.sql`).
4. Run `QUAY_OVERRIDE_CONFIG='{"DB_URI":"postgresql://..."}' TEST=true PYTHONPATH=. alembic upgrade head`.
5. Run `pg_dump` with normalization flags:
   - `--schema-only` — exclude data
   - `--no-owner` — strip ownership
   - `--no-privileges` — strip GRANT/REVOKE
   - `--no-comments` — strip COMMENT ON
   - `--no-tablespaces` — strip tablespace assignment
   - `--exclude-table=alembic_version` — exclude migration tracking table
6. Post-process via `sed`: strip `SET` statements, `SELECT pg_catalog.setval` lines, `--` comment lines, collapse consecutive blank lines.
7. Write output with header comment to target path (default: `internal/dal/sql/schema/postgres/schema.sql`).
8. Cleanup container on exit via `trap`.

### 4.2 Design decisions

- **Port 15432**: avoids conflict with local-dev PostgreSQL (5432) and test runners.
- **Container engine detection**: `podman || docker`, consistent with project conventions.
- **`QUAY_OVERRIDE_CONFIG` + `TEST=true`**: matches the pattern established in `data/migrations/migration.sh` and `Makefile:test_postgres`. The `data/migrations/env.py` reads `DB_URI` from `app.config`, which respects `QUAY_OVERRIDE_CONFIG`.
- **PostgreSQL 18**: matches the version used in `docker-compose.yaml` for local development.
- **`pg_trgm` before migrations**: migration `e2894a3a3c19` creates GIN indexes with `gin_trgm_ops` that require the extension to exist.

### 4.3 Determinism

`pg_dump` output ordering is deterministic within a PostgreSQL major version — objects are sorted by OID, which is deterministic for a database created from scratch via migrations on an empty instance. Pinning the PostgreSQL version in the script and CI ensures consistency.

The `sed` post-processing strips timestamp-containing comments and session-variable `SET` statements that could vary between environments.

## 4A. SQLite schema generation script: `scripts/sync-sqlc-schema-sqlite.sh`

### 4A.1 Feasibility

All 117 Alembic migrations run on SQLite without modification:

- `data/migrations/env.py:108` uses `render_as_batch=True`, enabling SQLite-compatible ALTER TABLE via copy-and-rename.
- PostgreSQL-specific DDL is dialect-guarded (`e8ed3fb547da` guards `ALTER SEQUENCE` with `if bind.engine.name == "postgresql"`; `34c8ef052ec9` guards `COMMIT` with `if dialect.name != "sqlite"`).
- PostgreSQL-specific index options (`postgresql_concurrently=True`, `postgresql_using="gin"`, `postgresql_ops={"...": "gin_trgm_ops"}`) are silently ignored by SQLAlchemy on SQLite.
- The existing test infrastructure already runs Alembic against SQLite via `test/fixtures.py`.

### 4A.2 Steps

1. Create temporary SQLite database file via `mktemp`.
2. Run `DB_URI=sqlite:///$TMPDB TEST=true PYTHONPATH=. alembic upgrade head`.
3. Dump schema: `sqlite3 $TMPDB .schema`.
4. Post-process: strip `CREATE TABLE alembic_version`, normalize whitespace, collapse blank lines.
5. Write output with header comment to target path (default: `internal/dal/sql/schema/sqlite/schema.sql`).
6. Cleanup temp file on exit via `trap`.

### 4A.3 Design decisions

- **No container needed**: SQLite is file-based. Script executes in sub-second, significantly faster than the PostgreSQL path (~15-30s).
- **Same Alembic environment**: Uses the same `env.py`, `TEST=true`, and `PYTHONPATH=.` as the PostgreSQL script, differing only in `DB_URI`.
- **Determinism**: SQLite `.schema` output is deterministic for a given migration sequence on a freshly-created database.

### 4A.4 Known dialect differences in the generated schema

| Feature | PostgreSQL `schema.sql` | SQLite `schema.sql` | Impact on sqlc |
|---------|------------------------|---------------------|----------------|
| Auto-increment PK | `SERIAL`/`BIGSERIAL` + sequences | `INTEGER PRIMARY KEY` (implicit rowid) | sqlc handles both per engine config |
| GIN/trigram indexes | `CREATE INDEX ... USING gin (...gin_trgm_ops)` | Absent (regular B-tree or omitted) | sqlc ignores indexes for codegen |
| Boolean | `BOOLEAN` (native) | `INTEGER` (0/1) | sqlc SQLite engine maps to Go `bool` via override |
| `VARCHAR(n)` | Length enforced | Type affinity only | Both map to Go `string` |
| `BIGINT`/`BIGSERIAL` | Explicit 8-byte integer | `INTEGER` (always 8-byte internally) | Both map to Go `int64` |
| Foreign keys | Enforced by default | Require `PRAGMA foreign_keys = ON` at connection | Schema-level FK syntax is the same |
| Concurrent index creation | `postgresql_concurrently=True` | N/A | Absent from SQLite dump |

## 5. Makefile targets

Added after the existing Go targets section (Makefile line ~380):

```makefile
##################
# Schema targets #
##################

SCHEMA_SQL := internal/dal/sql/schema/postgres/schema.sql
SCHEMA_SQL_SQLITE := internal/dal/sql/schema/sqlite/schema.sql

.PHONY: generate-schema-sql generate-schema-sql-sqlite check-schema-sql check-schema-sql-sqlite

generate-schema-sql:
	./scripts/sync-sqlc-schema.sh $(SCHEMA_SQL)

generate-schema-sql-sqlite:
	./scripts/sync-sqlc-schema-sqlite.sh $(SCHEMA_SQL_SQLITE)

check-schema-sql:
	@echo "==> Checking schema.sql is up to date..."
	@TMPFILE=$$(mktemp) && \
	./scripts/sync-sqlc-schema.sh "$$TMPFILE" && \
	diff -u $(SCHEMA_SQL) "$$TMPFILE" || \
	(echo ""; echo "ERROR: $(SCHEMA_SQL) is out of date."; \
	 echo "Run 'make generate-schema-sql' and commit the result."; \
	 rm -f "$$TMPFILE"; exit 1); \
	rm -f "$$TMPFILE"; \
	echo "==> Schema is up to date."

check-schema-sql-sqlite:
	@echo "==> Checking SQLite schema.sql is up to date..."
	@TMPFILE=$$(mktemp) && \
	./scripts/sync-sqlc-schema-sqlite.sh "$$TMPFILE" && \
	diff -u $(SCHEMA_SQL_SQLITE) "$$TMPFILE" || \
	(echo ""; echo "ERROR: $(SCHEMA_SQL_SQLITE) is out of date."; \
	 echo "Run 'make generate-schema-sql-sqlite' and commit the result."; \
	 rm -f "$$TMPFILE"; exit 1); \
	rm -f "$$TMPFILE"; \
	echo "==> SQLite schema is up to date."
```

## 6. sqlc configuration: `sqlc.yaml`

At repository root, matching `data_access_layer_design.md` §5.2:

```yaml
version: "2"
sql:
  - engine: "postgresql"
    queries: "internal/dal/sql/queries/postgres/"
    schema: "internal/dal/sql/schema/postgres/"
    gen:
      go:
        package: "pgqueries"
        out: "internal/dal/repositories/postgres/sqlc"
        sql_package: "pgx/v5"
        emit_json_tags: true
        emit_empty_slices: true
```

The SQLite engine entry should be committed from day one alongside the PostgreSQL entry, even before mirror-mode query definitions are authored. This ensures the CI parity check (§7A) has both schema files to compare.

```yaml
  - engine: "sqlite"
    queries: "internal/dal/sql/queries/sqlite/"
    schema: "internal/dal/sql/schema/sqlite/"
    gen:
      go:
        package: "sqlitequeries"
        out: "internal/dal/repositories/sqlite/sqlc"
```

## 7. CI gate: `.github/workflows/schema-drift.yml`

Implements `db_migration_policy.md` §10.2-10.5.

### 7.1 Trigger paths

On pull requests touching any of:
- `data/database.py` (Peewee model definitions)
- `data/fields.py` (custom field types)
- `data/migrations/versions/**` (Alembic migration files)
- `internal/dal/sql/schema/**` (sqlc schema snapshots)
- `internal/dal/sql/queries/**` (sqlc query definitions)
- `sqlc.yaml` (sqlc configuration)

### 7.2 Job steps

1. GitHub Actions `services:` PostgreSQL 18 container with health check.
2. Checkout, set up Python 3.12, install dependencies.
3. Create `pg_trgm` extension.
4. `alembic upgrade head` with `QUAY_OVERRIDE_CONFIG`.
5. `pg_dump` with same flags and `sed` normalization as the local script.
6. Diff generated output against committed `internal/dal/sql/schema/postgres/schema.sql`.
7. Fail with clear error message if divergent, identifying the changed objects.

### 7.3 Failure resolution

| Failure | Cause | Resolution |
|---------|-------|------------|
| Schema snapshot diverged | Alembic migration added without updating sqlc schema | Run `make generate-schema-sql`, commit updated `schema.sql` |
| Generated code changed | sqlc query or schema updated without regenerating | Run `sqlc generate`, commit generated files |
| Go build failure | Schema change broke existing queries | Update affected `.sql` query files, regenerate |

## 7A. PG/SQLite logical schema parity check

### 7A.1 Purpose

The PostgreSQL and SQLite schema files diverge in DDL syntax (see §4A.4), but must agree on logical structure: same tables, same columns, same types (modulo dialect mapping), same constraints (modulo unsupported features like GIN indexes).

### 7A.2 Implementation

A Python script (`scripts/check-schema-parity.py`, ~100 LOC) that:

1. Parses `CREATE TABLE` statements from both `internal/dal/sql/schema/postgres/schema.sql` and `internal/dal/sql/schema/sqlite/schema.sql`.
2. Extracts table names, column names, column ordering, and nullable flags.
3. Compares and fails with a clear diff if table/column structure diverges.
4. Allows known exceptions via an allowlist: GIN indexes, sequences, PG-specific DEFAULT expressions, type syntax differences (e.g., `SERIAL` vs `INTEGER PRIMARY KEY`).

### 7A.3 CI integration

Add to `.github/workflows/schema-drift.yml` as a step after both schema snapshots are validated:

```yaml
- name: Check PG/SQLite logical parity
  run: python3 scripts/check-schema-parity.py
```

Triggered on PRs touching `internal/dal/sql/schema/**`.

## 8. Directory structure

```
scripts/
  sync-sqlc-schema.sh                         # PostgreSQL schema generation script
  sync-sqlc-schema-sqlite.sh                  # SQLite schema generation script
  check-schema-parity.py                      # PG/SQLite logical parity check
internal/
  dal/
    sql/
      schema/
        postgres/
          schema.sql                           # pg_dump output (committed, generated)
        sqlite/
          schema.sql                           # sqlite3 .schema output (committed, generated)
      queries/
        postgres/
          .gitkeep                             # Placeholder for sqlc query files
        sqlite/
          .gitkeep                             # Placeholder for sqlc query files
    repositories/
      postgres/
        sqlc/
          .gitkeep                             # Placeholder for sqlc generated code
      sqlite/
        sqlc/
          .gitkeep                             # Placeholder for sqlc generated code
sqlc.yaml                                      # sqlc configuration (both PG and SQLite engines)
.github/workflows/schema-drift.yml             # CI gate
Makefile                                       # Edit: add schema generation and check targets
```

## 9. Developer workflow

1. Edit `data/database.py` (Peewee models) and/or create Alembic migration in `data/migrations/versions/`.
2. Run `make generate-schema-sql` (~15-30 seconds, spins up ephemeral PostgreSQL).
3. Run `make generate-schema-sql-sqlite` (sub-second, no container needed).
4. Review diffs in `internal/dal/sql/schema/postgres/schema.sql` and `internal/dal/sql/schema/sqlite/schema.sql`.
5. Commit updated schema files alongside the migration file.
6. (Future, when sqlc queries exist) Run `sqlc generate`, commit generated Go code.
7. Push. CI verifies schema parity (PG snapshot, SQLite snapshot, PG/SQLite logical parity).

If steps 2-3 are skipped, CI fails with a diff and message identifying which schema file is out of date.

## 10. Verification criteria

1. `make generate-schema-sql` produces a valid, complete PostgreSQL schema.
2. `make generate-schema-sql-sqlite` produces a valid, complete SQLite schema.
3. Running both generation scripts twice produces byte-identical output (determinism).
4. Adding a trivial Alembic migration (e.g., new nullable column) causes both `make check-schema-sql` and `make check-schema-sql-sqlite` to fail.
5. After regeneration, both check targets pass.
6. PG/SQLite logical parity check (`scripts/check-schema-parity.py`) passes — both schemas have the same tables and columns.
7. `sqlc generate` against both schemas produces valid Go code (verifies `sqlc.yaml` configuration).

## 11. Ownership

- **db-architecture** owns the correctness of the generation script and normalization rules.
- **CI/platform** owns the workflow integration and ephemeral PostgreSQL provisioning.
- The generation script is a WS0 deliverable per `db_migration_policy.md` §10.5.
