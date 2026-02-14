# Data Access Layer Migration Design (Peewee -> Go)

Status: Draft (blocking)
Last updated: 2026-02-09

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
- Minimum toolchain: Go `1.23.x`

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

## 5. Dependencies and version pins

Pin exact dependencies in `go.mod`:
- `github.com/jackc/pgx/v5` (DB driver + pool)
- `github.com/jackc/pgerrcode` (error classification)
- `github.com/sqlc-dev/sqlc` (codegen tool, pinned in tooling docs/CI)
- `github.com/prometheus/client_golang` (metrics)
- `go.opentelemetry.io/otel` (tracing, optional in first phase)

Version policy:
- Patch updates allowed automatically.
- Minor upgrades require explicit compatibility review and fixture rerun.
- Any dependency tied to crypto or SQL serialization requires security owner signoff.

## 6. Core interfaces and types (implementation stubs)

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

## 7. Connection lifecycle and retry policy

1. Default pooling: on in Go (no per-request connect/disconnect churn).
2. Request context carries `read_intent` and `replica_allowed` flags.
3. Pool metrics exported with the same dimensions as Python dashboards where possible.
4. Failure policy:
- Replica read failure retries once on primary.
- Write failures only retry for explicitly classified transient errors and idempotent operations.
- Retry ceiling defaults to 1 retry for reads, 0 for writes unless callsite opts in.
5. Explicitly release DB resources before long-running response streaming to avoid pool starvation (equivalent concern to Python `CloseForLongOperation` / `UseThenDisconnect` patterns).
6. Operator compatibility note: Python pooling is dual-controlled by env + config; Go default-on pooling is a behavior change and needs migration communication + opt-out control.

## 8. Read-replica behavior

- Maintain randomized healthy-replica selection.
- Keep a short-lived bad-host quarantine window.
- Support explicit request-local replica bypass to preserve `disallow_replica_use`.
- Emit reason-coded metrics for:
  - replica selected
  - replica bypassed by context
  - fallback-to-primary
  - no-replica-available

## 9. SQL generation workflow (`sqlc`)

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

## 10. Concrete implementation example

Reference operation: repository lookup by namespace/name.

Implementation requirement:
1. Execute as `IntentRead` with `ReplicaAllowed=true`.
2. On read-replica failure, retry once on primary.
3. Preserve "not found" mapping behavior to existing endpoint error contract.
4. Emit metric labels for selected node role (`replica|primary`) and result (`ok|fallback|error`).

## 11. Migration and rollout sequence

1. Read-only parity phase: Go reads for selected capabilities, Python remains writer.
2. Controlled dual-read phase with diffing metrics for high-risk entities.
3. Selective write enablement after deterministic write parity is proven.
4. Full owner switch only after rollback drill and contract evidence review.

## 12. Required tests and fixture format

Required tests:
- Repository-level parity tests (`python oracle` vs `go implementation`).
- Replica routing tests (normal, degraded, bypass).
- Transaction boundary tests for queue producer side effects.
- Encrypted field backward-compatibility tests.

Fixture format:
- `internal/dal/testkit/fixtures/<case>.json`:
  - `seed_sql`: schema/data setup SQL list
  - `python_expected`: serialized result payload
  - `go_expected`: serialized result payload
  - `notes`: behavior caveats

## 13. Credential hashing compatibility (bcrypt)

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

## 14. Queue optimistic concurrency (`state_id`)

Source anchor:
- `data/database.py` (`QueueItem.save`)

Requirements:
1. Every queue item mutation must regenerate `state_id` (UUID) before write.
2. Claim/update operations must preserve compare-and-swap behavior (`id + state_id` contract).
3. Do not allow ad-hoc writes that bypass state-id regeneration path.

Implementation guidance:
- Prefer a dedicated queue write helper (`SaveQueueItem`) or equivalent invariant enforcement strategy.

## 15. Delete semantics and cleanup hooks

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

## 16. Foreign-key access conventions (N+1 protection)

Source anchor:
- `data/database.py` (`BaseModel.__getattribute__` `_id` shortcut behavior)

Requirements:
1. Model/query shapes must support lightweight FK-ID access without forcing relation loads.
2. Repository methods should return FK identifiers by default unless relation expansion is explicitly required.

Implementation guidance:
- Keep ID fields first-class in Go models and SQL queries.

## 17. Text search compatibility

Source anchor:
- `data/text.py` (`prefix_search`, `match_like`)

Requirements:
1. Preserve wildcard escaping semantics (`!` escape char, escaped `%`/`_`/`[` handling).
2. Preserve ILIKE/LIKE behavior parity by database backend.
3. Keep sanitized query handling consistent with Python behavior.

## 18. Exit criteria (gate G8)

- DAL architecture approved by db-architecture + security owners.
- Go module + DAL package scaffold compiles in CI (`go test ./...`, `go vet ./...`).
- At least one high-risk repository area validated end-to-end (read/write/retry/rollback).
- Connection pool and replica fallback dashboards available.
- Encryption compatibility tests green in both FIPS-on and FIPS-off test environments.
- Queue CAS and `state_id` regeneration behavior validated under contention tests.
- Delete semantics and cleanup callback parity validated for representative entities.
- Bcrypt credential verification parity tests green.
