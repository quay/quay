# DB and Data Migration Policy

Status: Draft
Last updated: 2026-02-09

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
