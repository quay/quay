# DB and Data Migration Policy

Status: Draft
Last updated: 2026-03-02

## 1. Purpose

Define non-breaking data evolution rules for mixed Python/Go runtime during migration.

Implementation architecture reference:
- `plans/rewrite/data_access_layer_design.md`

## 2. Hard policy

- No breaking DB schema change while any Python runtime still serves that contract.
- No queue payload schema break while Python and Go producers/consumers are mixed.
- No object-storage layout break without compatibility readers in both runtimes.

## 3. Schema evolution pattern

Use expand->migrate->contract only:

1. Expand
- Additive schema only (new nullable columns/tables/indexes).
- Old read/write paths continue to function unchanged.

2. Migrate
- Backfill data in idempotent jobs.
- Enable dual-write where required.
- Keep read path backward compatible.

3. Contract
- Remove legacy columns/paths only after:
  - all owners are `go`
  - rollback period ends
  - compatibility metrics show no legacy reads/writes

## 4. Queue payload compatibility

- Payloads are versioned with `schema_version` where shape may evolve.
- Consumers must accept previous version(s) during migration.
- Producers may emit old version until all active consumers support new version.
- No required-field removal in active mixed mode.

## 5. Locking and transactional behavior

Preserve semantics for:
- WorkQueue claim CAS (`id + state_id`) behavior.
- `retries_remaining` decrement semantics on claim.
- `complete` vs `incomplete` semantics.
- Lease extension (`extend_processing`) behavior.
- Build queue ordered claim behavior.

## 6. Storage and identifier invariants

- Repository/image/blob identifiers remain stable.
- Digest normalization and media type interpretation remain stable.
- Placement/replication records remain semantically equivalent.
- Marker-based GC invariants remain intact.

## 7. Exception process for unavoidable DB changes

If a non-additive change is unavoidable:

1. File a migration exception record in plan docs:
- reason
- affected endpoints/workers
- compatibility strategy
- rollback strategy

2. Provide compensating compatibility layer:
- Python compatibility adapter OR
- Go compatibility adapter

3. Require explicit approval gate before rollout.
4. Required approver set:
- db-architecture owner
- api-service owner for affected capabilities
- rollback/oncall representative

## 8. Required test gates for DB-affecting changes

- Forward and backward migration tests.
- Mixed-runtime integration tests.
- Queue replay tests with old/new payloads.
- Data consistency checks before and after rollback drill.

## 9. Alembic bridge dependency (Python retention requirement)

Current constraint:
- Alembic metadata generation currently relies on Python/Peewee model definitions via `data/model/sqlalchemybridge.py`.

Policy implication:
1. Do not remove Peewee model definitions before replacement migration tooling is production-ready.
2. During mixed-runtime milestones, schema evolution must remain compatible with this bridge.
3. Peewee removal is an M5+ action gated on replacement migration tool validation and operator signoff.

## 10. Schema drift detection CI gate

### 10.1 Problem

During mixed-runtime coexistence, both Python (Peewee/Alembic) and Go (sqlc) must agree on the database schema. Schema changes arrive via Alembic migrations authored against Peewee models. Go's sqlc uses a schema snapshot as input for code generation. Without an automated check, the Go-side schema snapshot can silently diverge from Alembic HEAD, causing runtime query failures or data corruption.

### 10.2 CI gate requirements

A CI job must run on every PR that modifies any of:
- `data/migrations/versions/` (Alembic migration files)
- `data/database.py` (Peewee model definitions)
- `internal/dal/sql/schema/` (sqlc schema snapshots)
- `internal/dal/sql/queries/` (sqlc query definitions)

### 10.3 Gate steps

1. **Generate schema snapshot from Alembic HEAD:**
   - Apply all Alembic migrations to a temporary PostgreSQL instance (use CI-provided ephemeral database).
   - Dump the resulting schema using `pg_dump --schema-only`.
   - Normalize the dump (strip comments, sort objects) for deterministic comparison.

2. **Compare against sqlc schema snapshot:**
   - Diff the generated schema against `internal/dal/sql/schema/postgres/schema.sql`.
   - If they differ, fail the CI gate with a clear message identifying the divergent objects (tables, columns, indexes, constraints).

3. **Regenerate sqlc code:**
   - Run `sqlc generate`.
   - Check for uncommitted changes to generated files in `internal/dal/repositories/postgres/sqlc/`.
   - If generated code changed, fail the CI gate with a message requiring the developer to commit the regenerated files.

4. **Compile and test:**
   - Run `go build ./internal/dal/...`
   - Run `go test ./internal/dal/...`
   - Run parity fixture tests against Python oracle.

### 10.4 Failure modes and resolution

| Failure | Cause | Resolution |
|---------|-------|------------|
| Schema snapshot diverged | Alembic migration added without updating sqlc schema | Run schema dump script, update `internal/dal/sql/schema/`, run `sqlc generate`, commit all changes |
| Generated code changed | sqlc query or schema updated without regenerating | Run `sqlc generate`, commit generated files |
| Go build failure | Schema change broke existing queries | Update affected `.sql` query files, regenerate, fix compilation errors |
| Parity test failure | Schema change altered query behavior | Update parity test fixtures and Python oracle expected values |

### 10.5 Ownership

- **db-architecture** owns the correctness of the schema drift check: what constitutes a valid diff, what divergences are acceptable (e.g., comment differences), and the normalization rules for deterministic comparison.
- **CI/platform** owns the infrastructure: running the job, providing ephemeral PostgreSQL instances, integrating into the merge pipeline.
- In practice, db-architecture writes the comparison script and CI/platform integrates it. The comparison script is a WS0 deliverable.

### 10.6 Tooling

Provide a developer script (`scripts/sync-sqlc-schema.sh`) that automates steps 1-3 locally, so developers can resolve drift before pushing.

### 10.7 Go migration authority switchover gate (M5)

Go migration tooling becomes the primary authority at M5, replacing Alembic. The switchover requires all of the following:

1. The schema drift CI gate (§10.2) has been green for all migrations across at least 2 milestones (M3-M4).
2. Go migration tooling has been used to produce at least 5 production-equivalent migrations that pass the `pg_dump --schema-only` parity diff.
3. A rollback drill has been executed: apply a Go migration, roll back, verify Alembic can resume cleanly from the same state.
4. db-architecture owner signs off with evidence linking to CI runs, migration PRs, and rollback drill results.

At M5 switchover:
- Go migrations become the sole authority applied to production databases.
- Alembic migrations are frozen (no new migrations authored).
- `data/model/sqlalchemybridge.py` and Peewee model definitions become eligible for removal (tracked in `program_gates.md` under G8).

#### 10.7.1 Constraints for Go migration tool selection

Any Go migration tool must satisfy these project-specific requirements:

1. **DBA operator compatibility**: Must be invokable as a CLI command from within a container (e.g., `quay migrate <revision>`), matching the existing `dba_operator.py` pattern that wraps migrations in Kubernetes `DatabaseMigration` CRDs.
2. **Phase-gated migrations**: Must support upgrading to a specific revision, not just "head". The `active_migration.py` / `data/migrationutil.py` phase system gates migration rollout by revision.
3. **Rollback support**: Must support downgrade operations — a gating criterion for M5 switchover.
4. **FIPS/air-gap compatibility**: Must be embeddable as a Go library in the Quay binary. No external tool distribution required. Operators in air-gapped environments run migrations via the Quay container image.
5. **Multi-database support**: PostgreSQL (primary) + SQLite (mirror mode). MySQL is deprecated and not required.
6. **SQL-file migrations preferred**: Consistency with sqlc's SQL-first philosophy. Avoid Go-function migrations that tie execution to binary version.

#### 10.7.2 Candidate comparison

| | **golang-migrate** | **goose** | **atlas** |
|---|---|---|---|
| Migration format | SQL files (`.up.sql`/`.down.sql`) | SQL files or Go functions | SQL or HCL (declarative) |
| Version tracking | `schema_migrations` (version + dirty) | `goose_db_version` (version + is_applied) | `atlas_schema_revisions` |
| Specific revision | `migrate goto <version>` | `goose up-to <version>` | `atlas migrate apply --to <version>` |
| Rollback | `migrate down <steps>` | `goose down` / `goose down-to` | `atlas migrate down --to <version>` |
| PG + SQLite | Yes (separate drivers) | Yes | Yes |
| Embeddable | Yes (Go library) | Yes (Go library) | Yes (Go SDK) |
| SQL-only mode | SQL-only by design | Supports both SQL and Go | SQL migrations supported |
| Schema introspection | No | No | Yes (can diff live DB vs desired) |

#### 10.7.3 Recommendation

**golang-migrate** as primary candidate:
- SQL-only by design — no temptation to embed Go code in migrations.
- Simple version model — sequential integers, easy to reason about.
- `goto <version>` satisfies the phase-gated migration requirement.
- Embeddable as library for air-gapped/FIPS deployment.

**atlas** is worth evaluating at M5 for declarative schema diffing — it can compare a desired schema state (the `schema.sql` snapshot) against a live database and generate migrations automatically. This could eliminate hand-written migration files but is a significant workflow change requiring evaluation against real migrations before adoption.

**goose** is viable but offers no advantages over golang-migrate for this project.

#### 10.7.4 M5 transition mechanics

1. **Freeze Alembic**: No new migration files authored in `data/migrations/versions/`. The last Alembic revision becomes permanent HEAD.
2. **Baseline Go migration**: The `schema.sql` snapshot maintained throughout M1-M4 becomes `000001_baseline.up.sql` for golang-migrate. The `.down.sql` drops all tables in reverse dependency order.
3. **Version table handoff**: golang-migrate uses a `schema_migrations` table. `alembic_version` remains in the database but is no longer consulted. A one-time handoff script creates the Go version table and marks baseline as applied.
4. **Guard for existing databases**: The baseline migration checks for `alembic_version` — if found, skip DDL (database already has the schema), just mark baseline as applied.
5. **DBA operator adaptation**: Update `dba_operator.py` (or its Go replacement) to invoke `quay migrate --to <version>` instead of `alembic upgrade <revision>`.

#### 10.7.5 Shadow validation during M3-M4

Before M5, validate the Go migration tool without giving it production authority:

1. For each new Alembic migration, also write the equivalent golang-migrate `.up.sql`/`.down.sql` file.
2. CI applies both Alembic and golang-migrate to separate ephemeral PostgreSQL instances.
3. `pg_dump --schema-only` both, diff — must be byte-identical after normalization.
4. This proves parity without risk to production and satisfies the "5 production-equivalent migrations" requirement.

### 10.8 PR requirements during coexistence

Every PR that includes an Alembic migration (`data/migrations/versions/`) must also include the corresponding Go schema snapshot update — regenerated `internal/dal/sql/schema/postgres/schema.sql` and `internal/dal/sql/schema/sqlite/schema.sql` via `make generate-schema-sql generate-schema-sql-sqlite`. CI blocks the merge if the schema snapshots are stale relative to Alembic HEAD (see `schema_sql_generation.md` §7 and §7A for the CI gate).

Starting in M3, when shadow validation begins (§10.7.5), PRs with Alembic migrations must also include the corresponding golang-migrate `.up.sql`/`.down.sql` file. CI validates parity between the two migration implementations.
