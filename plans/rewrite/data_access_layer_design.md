# Data Access Layer Migration Design (Peewee -> Go)

Status: Draft (blocking)
Last updated: 2026-02-12

## 1. Purpose

Define the implementation architecture for replacing Quay's Peewee-based data layer with a Go data access layer that preserves behavior in mixed Python/Go runtime.

Primary source anchors:
- `data/database.py`
- `data/readreplica.py`
- `data/encryption.py`
- `data/cache/impl.py`

## 2. Current-state invariants to preserve

1. Per-request DB lifecycle and cleanup semantics.
2. Retry behavior for transient operational DB errors.
3. Read-replica selection with fallback and explicit replica bypass (`disallow_replica_use`).
4. Field-level encryption/decryption compatibility for existing rows.
5. Metrics parity for connection pool and query errors.

## 3. Go architecture decision

Recommended stack:
- SQL driver/runtime: `pgx/v5` + `pgxpool`
- Query layer: `sqlc` generated query packages + thin repository wrappers
- Migration authority: Alembic remains source of truth until M5

Rationale:
- `pgx` provides strong PostgreSQL feature support and pool instrumentation.
- `sqlc` keeps SQL explicit and reviewable, avoiding ORM behavior drift.

## 4. Go module and package layout

Module strategy (planning baseline):
- Single module at repo root: `github.com/quay/quay`
- Minimum toolchain: Go `1.24+`

DAL package layout (implementation target):
- `internal/dal/dbcore/`
  - `pool.go` (pool bootstrap, health, lifecycle)
  - `retry.go` (safe retry classifier and wrapper)
  - `tx.go` (transaction helpers + context propagation)
  - `metrics.go` (Prometheus/OpenTelemetry hooks)
- `internal/dal/readreplica/`
  - `selector.go` (replica selection + quarantine)
  - `policy.go` (bypass rules, fallback controls)
- `internal/dal/crypto/`
  - `fields.go` (encrypt/decrypt adapters for DB fields)
  - `compat_fixtures_test.go`
- `internal/dal/repositories/`
  - `repository.go` (repository-facing interfaces)
  - `postgres/` (sqlc-backed implementations)
- `internal/dal/testkit/`
  - `fixtures/` (cross-runtime fixtures)
  - `oracle/` (Python-oracle comparison helpers)

## 5. Multi-database support

### 5.1 PostgreSQL (primary target)

PostgreSQL remains the primary and fully supported database. All sqlc query definitions target the PostgreSQL dialect. The Go DAL uses `pgx/v5` as the driver.

### 5.2 SQLite (mirror mode)

sqlc natively supports SQLite as a separate engine target. Mirror-mode deployments (single-node, local testing) use SQLite with a separate `sqlc.yaml` engine entry generating dialect-appropriate Go code.

**Driver choice:** Use `modernc.org/sqlite` (pure-Go, no CGO dependency). Rationale:
- Simplifies cross-compilation and reproducible builds.
- Avoids CGO dependency chain in FIPS-validated build environments.
- `mattn/go-sqlite3` is more mature but requires CGO, complicating FIPS certification and CI matrix.
- Mirror mode is a secondary deployment target; the pure-Go tradeoffs (minor performance gap) are acceptable.

**sqlc configuration:** Maintain separate engine entries in `sqlc.yaml`:
```yaml
sql:
  - engine: "postgresql"
    queries: "internal/dal/sql/queries/postgres/"
    schema: "internal/dal/sql/schema/postgres/"
    gen:
      go:
        package: "pgqueries"
        out: "internal/dal/repositories/postgres/sqlc"
  - engine: "sqlite"
    queries: "internal/dal/sql/queries/sqlite/"
    schema: "internal/dal/sql/schema/sqlite/"
    gen:
      go:
        package: "sqlitequeries"
        out: "internal/dal/repositories/sqlite/sqlc"
```

### 5.3 MySQL (deprecation)

MySQL is formally deprecated for Go DAL support. The current Python codebase has MySQL-specific code paths (MATCH/AGAINST full-text search, `fn.Rand()`, charset configuration in `data/database.py:74-80`), but these will not be ported to the Go DAL.

**Migration path for MySQL deployments:**
1. MySQL remains supported in the Python runtime through M4.
2. Operators on MySQL must migrate to PostgreSQL before adopting Go-served capabilities.
3. Migration tooling (pg_loader or equivalent) guidance will be provided in operator documentation by M3.
4. MySQL-specific Python code paths may be removed after M5 (Python retirement gate).

## 6. Dependencies and version pins

Pin exact dependencies in `go.mod`:
- `github.com/jackc/pgx/v5` (DB driver + pool)
- `github.com/jackc/pgerrcode` (error classification)
- `github.com/sqlc-dev/sqlc` (codegen tool, pinned in tooling docs/CI)
- `github.com/prometheus/client_golang` (metrics)
- `go.opentelemetry.io/otel` (tracing, optional in first phase)
- `modernc.org/sqlite` (SQLite driver for mirror mode, pure-Go, no CGO)

Crypto dependencies:
- `golang.org/x/crypto/bcrypt` (credential hashing)
- AES-CCM library: requires candidate selection and FIPS validation. Evaluate `github.com/pion/dtls/v2/pkg/crypto/ccm` or a standalone CCM implementation wrapping `crypto/aes`. The selected library must:
  - Pass FIPS validation or be wrappable with a FIPS-validated AES primitive.
  - Reproduce the exact nonce+ciphertext byte layout used by Python's `cryptography` library.
  - Be vetted by security owner before any implementation begins.

Key derivation compatibility:
- Python's `convert_secret_key` (`util/security/secret.py`) uses `itertools.cycle` to pad/truncate arbitrary key material to 32 bytes. This is not a standard KDF. The Go implementation must reproduce this byte-for-byte, including the three input parsing modes (integer string, UUID hex, raw bytes). Golden test vectors covering all three modes are a prerequisite for any Go crypto implementation (see section 14).

Version policy:
- Patch updates allowed automatically.
- Minor upgrades require explicit compatibility review and fixture rerun.
- Any dependency tied to crypto or SQL serialization requires security owner signoff.

## 7. Core interfaces and types (implementation stubs)

```go
package dbcore

import "context"

type QueryIntent int

const (
    IntentRead QueryIntent = iota
    IntentWrite
)

type QueryOptions struct {
    Intent         QueryIntent
    ReplicaAllowed bool
    Idempotent     bool
}

type Runner interface {
    Exec(ctx context.Context, sql string, args ...any) (int64, error)
    Query(ctx context.Context, sql string, args ...any) (Rows, error)
    QueryRow(ctx context.Context, sql string, args ...any) Row
}

type DB interface {
    Run(ctx context.Context, opts QueryOptions, fn func(ctx context.Context, r Runner) error) error
    WithTx(ctx context.Context, fn func(ctx context.Context, tx Runner) error) error
}
```

```go
package repositories

import "context"

type RepositoryStore interface {
    GetByNamespaceAndName(ctx context.Context, namespace, name string) (*Repository, error)
    Create(ctx context.Context, cmd CreateRepositoryCommand) (*Repository, error)
    UpdateVisibility(ctx context.Context, id int64, visibility string) error
}
```

## 8. Connection lifecycle and retry policy

1. Default pooling: on in Go (no per-request connect/disconnect churn).
2. Request context carries `read_intent` and `replica_allowed` flags.
3. Pool metrics exported with the same dimensions as Python dashboards where possible.
4. Failure policy:
- Replica read failure retries once on primary.
- Write failures only retry for explicitly classified transient errors and idempotent operations.
- Retry ceiling defaults to 1 retry for reads, 0 for writes unless callsite opts in.
5. Explicitly release DB resources before long-running response streaming to avoid pool starvation (equivalent concern to Python `CloseForLongOperation` / `UseThenDisconnect` patterns).
6. Operator compatibility note: Python pooling is dual-controlled by env + config; Go default-on pooling is a behavior change and needs migration communication + opt-out control.

## 9. Read-replica behavior

- Maintain randomized healthy-replica selection.
- Keep a short-lived bad-host quarantine window.
- Support explicit request-local replica bypass to preserve `disallow_replica_use`.
- `ReplicaAllowed` defaults to `false` in `QueryOptions`. Every callsite that opts in must document the staleness tolerance and confirm no write-dependent read follows. A linter or code review checklist should enforce documentation for every `ReplicaAllowed=true` callsite.
- Emit reason-coded metrics for:
  - replica selected
  - replica bypassed by context
  - fallback-to-primary
  - no-replica-available

## 10. SQL generation workflow (`sqlc`)

Directory contract:
- SQL definitions: `internal/dal/sql/queries/*.sql`
- Schema snapshot inputs: generated from Alembic state during CI job
- Generated package: `internal/dal/repositories/postgres/sqlc`

Required commands:
1. `sqlc generate`
2. `go test ./internal/dal/...`
3. contract fixture diff check against Python oracle

Change control:
- Every SQL change must include:
  - SQL diff
  - generated code diff
  - parity test updates

## 11. Query surface inventory

### 11.1 Purpose

Before implementation begins, produce a complete inventory of the Python data access surface to size the work, identify dynamic query patterns incompatible with static sqlc, and track porting progress.

### 11.2 Inventory methodology

Enumerate all public functions in `data/model/` that execute database queries. For each function, record:

| Field | Description |
|-------|-------------|
| Module | Python module path (e.g., `data.model.oci.tag`) |
| Function | Function name |
| Query type | `read` / `write` / `read-write` |
| Complexity | `static` / `conditional` / `dynamic` |
| Go strategy | `sqlc` / `Go builder` / `raw pgx` |
| Priority | `P0` (registry critical path) / `P1` (API) / `P2` (background/admin) |
| Status | `not started` / `in progress` / `parity tested` / `done` |

### 11.3 Query strategy classification

- **Static sqlc** (~60-70% estimated): Fixed SQL shape, parameterized only by bind values. Direct sqlc query file.
- **Conditional Go builder** (~20-25% estimated): SQL shape varies based on input flags (e.g., optional filters, permission-based JOINs). Implemented as Go functions that assemble SQL strings from pre-validated fragments, then execute via `pgx` directly.
- **Raw pgx** (~5-10% estimated): Highly dynamic patterns like `filter_to_repos_for_user` (multi-union queries built from permission sets) and `reduce_as_tree` (balanced UNION ALL trees). Implemented as Go functions with explicit SQL string construction.

### 11.4 Known dynamic query patterns requiring Go builder or raw pgx

| Pattern | Location | Description |
|---------|----------|-------------|
| `filter_to_repos_for_user` | `data/model/_basequery.py` | Builds multi-UNION queries based on user permissions, team memberships, and org visibility |
| `reduce_as_tree` | `data/model/_basequery.py` | Constructs balanced binary UNION ALL trees for query optimization |
| Conditional tag filtering | `data/model/oci/tag.py` | Dynamic WHERE clauses based on filter parameters |
| Permission-based JOINs | `data/model/permission.py` | JOIN structure varies by permission check type |

### 11.5 Tracking and exit criteria

- Inventory spreadsheet (or structured YAML/JSON) must be completed before WS8 implementation starts.
- Coverage tracked as a percentage of total functions ported and parity-tested.
- WS8 exit requires 100% coverage of P0 functions, 90%+ of P1 functions.

## 12. Concrete implementation example

Reference operation: repository lookup by namespace/name.

Implementation requirement:
1. Execute as `IntentRead` with `ReplicaAllowed=true`.
2. On read-replica failure, retry once on primary.
3. Preserve "not found" mapping behavior to existing endpoint error contract.
4. Emit metric labels for selected node role (`replica|primary`) and result (`ok|fallback|error`).

## 13. Migration and rollout sequence

1. Read-only parity phase: Go reads for selected capabilities, Python remains writer.
2. Controlled dual-read phase with diffing metrics for high-risk entities.
3. Selective write enablement after deterministic write parity is proven.
4. Full owner switch only after rollback drill and contract evidence review.

## 14. Required tests and fixture format

Required tests:
- Repository-level parity tests (`python oracle` vs `go implementation`).
- Replica routing tests (normal, degraded, bypass).
- Transaction boundary tests for queue producer side effects.
- Encrypted field backward-compatibility tests.
- Encrypted field golden test corpus: produce encrypted values from Python for all 12 encrypted field instances across the schema, covering each `convert_secret_key` parsing mode (integer string, UUID hex, raw bytes). Go must decrypt every value and re-encrypt to produce byte-identical ciphertext (given the same nonce).
- `convert_secret_key` test vectors: explicit input/output pairs for each of the three parsing modes, including edge cases (empty string, max-length input, non-ASCII bytes). These vectors are a gate for any Go crypto implementation.
- Delete cascade ordering tests: for User (28+ dependent models) and Repository (19+ dependent models), verify that Go delete workflows produce the same deletion order and skip-set behavior as Python's `delete_instance_filtered`. Include verification that post-delete cleanup callbacks fire in the correct order.

Fixture format:
- `internal/dal/testkit/fixtures/<case>.json`:
  - `seed_sql`: schema/data setup SQL list
  - `python_expected`: serialized result payload
  - `go_expected`: serialized result payload
  - `notes`: behavior caveats

## 15. Credential hashing compatibility (bcrypt)

Source anchor:
- `data/fields.py` (`Credential`, `CredentialField`)

Requirements:
1. Treat credential hashes as bcrypt contracts, not encrypted-field contracts.
2. Use Go bcrypt implementation compatible with existing hash payloads (`golang.org/x/crypto/bcrypt`).
3. Preserve existing hash verification semantics for robot/app tokens.
4. Parse and respect cost factor encoded in stored hash values.

Tests:
- Verify Python-generated hash in Go.
- Verify Go-generated hash in Python during mixed mode.
- Cost-factor compatibility test corpus.

## 16. Queue optimistic concurrency (`state_id`)

Source anchor:
- `data/database.py` (`QueueItem.save`)

Requirements:
1. Every queue item mutation must regenerate `state_id` (UUID) before write.
2. Claim/update operations must preserve compare-and-swap behavior (`id + state_id` contract).
3. Do not allow ad-hoc writes that bypass state-id regeneration path.

Implementation guidance:
- Prefer a dedicated queue write helper (`SaveQueueItem`) or equivalent invariant enforcement strategy.

## 17. Delete semantics and cleanup hooks

Source anchors:
- `data/database.py` (`delete_instance_filtered`, `User.delete_instance`, `Repository.delete_instance`)
- `data/model/repository.py` (`config.repo_cleanup_callbacks`)

Requirements:
1. Preserve topological cascade delete behavior and ordering.
2. Preserve non-transactional long-running delete behavior where intentionally used.
3. Preserve entity-specific delete guards/logic (robot vs non-robot user, repository deletion state checks).
4. Preserve post-delete cleanup callbacks and side effects.

Implementation guidance:
- Use explicit delete workflows per entity type; avoid generic ORM cascade assumptions.
- Before implementing Go delete workflows, extract a delete dependency specification from Python's `delete_instance_filtered` for each entity with custom delete logic. This specification must document: FK dependency graph, skip sets, deletion ordering, and post-delete callbacks. The specification is the source of truth for Go implementation and must be updated when schema evolves.

## 18. Foreign-key access conventions (N+1 protection)

Source anchor:
- `data/database.py` (`BaseModel.__getattribute__` `_id` shortcut behavior)

Requirements:
1. Model/query shapes must support lightweight FK-ID access without forcing relation loads.
2. Repository methods should return FK identifiers by default unless relation expansion is explicitly required.

Implementation guidance:
- Keep ID fields first-class in Go models and SQL queries.

## 19. Enum table caching

### 19.1 Source anchors

- `data/database.py` (`EnumField` class, FK-based lookup tables)
- Enum tables: `RepositoryKind`, `TeamRole`, `Visibility`, `Role`, `MediaType`, `TagKind`, `LoginService`, `BuildTriggerService`, `AccessTokenKind`, `DisableReason`, `ApprType`, `NotificationKind`, `ExternalNotificationEvent`, `ExternalNotificationMethod`, `RepositoryNotificationEvent`, `RepositoryState`

### 19.2 Current behavior (Python)

Python's `EnumField` resolves FK-based enum values through `@lru_cache`-decorated id/name lookups. These are used extensively throughout the query layer for translating between human-readable enum names and FK integer IDs.

### 19.3 Go requirements

1. Load all static lookup tables into memory at DAL initialization (application startup).
2. Cache with process-lifetime TTL (these tables are effectively immutable after schema migration).
3. Provide bidirectional lookup: name-to-ID and ID-to-name.
4. Expose via DAL context or repository constructors so query implementations can resolve enum FKs without additional round-trips.

### 19.4 Implementation guidance

```go
package enums

// EnumCache provides bidirectional lookup for FK-based enum tables.
type EnumCache struct {
    byName map[string]int64
    byID   map[int64]string
}

// Registry holds all enum caches, loaded once at startup.
type Registry struct {
    RepositoryKind *EnumCache
    TeamRole       *EnumCache
    Visibility     *EnumCache
    MediaType      *EnumCache
    TagKind        *EnumCache
    // ... remaining enum tables
}

// LoadAll queries all enum tables once and populates the registry.
func LoadAll(ctx context.Context, db Runner) (*Registry, error) { ... }
```

5. If an enum value is encountered at runtime that is not in the cache (e.g., added by a migration while the process is running), log a warning and fall back to a single direct query. Do not crash.

## 20. Text search compatibility

Source anchor:
- `data/text.py` (`prefix_search`, `match_like`)

Requirements:
1. Preserve wildcard escaping semantics (`!` escape char, escaped `%`/`_`/`[` handling).
2. Preserve ILIKE/LIKE behavior parity by database backend.
3. Keep sanitized query handling consistent with Python behavior.

## 21. Exit criteria (gate G8)

- DAL architecture approved by db-architecture + security owners.
- Go module + DAL package scaffold compiles in CI (`go test ./...`, `go vet ./...`).
- At least one high-risk repository area validated end-to-end (read/write/retry/rollback).
- Connection pool and replica fallback dashboards available.
- Encryption compatibility tests green in both FIPS-on and FIPS-off test environments.
- Queue CAS and `state_id` regeneration behavior validated under contention tests.
- Delete semantics and cleanup callback parity validated for representative entities.
- Bcrypt credential verification parity tests green.
- Query surface inventory complete with strategy classification for all P0 and P1 functions.
- Enum table caching validated with startup load and runtime fallback behavior.
- AES-CCM library selected, FIPS-vetted, and approved by security owner.
