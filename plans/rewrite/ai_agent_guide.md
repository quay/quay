# AI Agent Implementation Guide (Go Rewrite)

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Provide concrete, bounded implementation tasks so an AI agent can execute rewrite work without making uncontrolled architectural decisions.

## 2. Agent operating rules

1. Never change API, auth, queue, or storage contracts unless the tracker row explicitly permits it.
2. Always implement behind owner switches (`python|go|off`) from `switch_spec.md`.
3. Treat Python behavior as oracle unless a reviewed decision says otherwise.
4. Include or update tests in the same change as implementation.
5. Keep task scope bounded to one capability family per PR.

## 3. Required task packet format

Every agent task must include:
- `scope_id`: tracker row(s) being implemented (for example `ROUTE-0311`, `PROC-014`).
- `input_contracts`: source files and contract IDs.
- `output_files`: exact file paths expected to change.
- `validation_commands`: exact commands to run.
- `rollback_path`: owner switch and rollback command.
- `out_of_scope`: explicit exclusions.

## 4. Task templates

### Template A: Route handler migration

- Scope: one route family subset (max 10 route rows).
- Inputs:
  - `plans/rewrite/generated/route_migration_tracker.csv`
  - `plans/rewrite/generated/route_auth_verification_checklist.csv`
  - Python endpoint source file(s)
- Outputs:
  - `internal/api/...` handler(s)
  - contract tests in `tests/rewrite/contracts/routes/...`
- Validation:
  1. route contract tests pass against Python oracle
  2. auth mode parity check passes
  3. rollback switch verified

### Template B: Worker migration

- Scope: one worker/process row.
- Inputs:
  - `plans/rewrite/generated/worker_migration_tracker.csv`
  - `plans/rewrite/queue_contracts.md`
  - Python worker source file
- Outputs:
  - `internal/workers/<name>/...`
  - `tests/rewrite/contracts/workers/<name>_contract_test.go`
- Validation:
  1. queue payload compatibility tests
  2. idempotency/retry behavior parity
  3. rollback to Python worker owner switch

### Template C: DAL repository implementation

- Scope: one repository interface + one read/write path.
- Inputs:
  - `plans/rewrite/data_access_layer_design.md`
  - SQL/query contracts and fixtures
- Outputs:
  - `internal/dal/repositories/...`
  - `internal/dal/sql/queries/...`
  - fixture tests
- Validation:
  1. SQLC generation succeeds
  2. read-replica fallback tests pass
  3. Python/Go fixture diff is clean

## 5. Bounded expectations per task

- Max files changed: `<= 12` (excluding generated files).
- Max net LOC: `<= 600`.
- Max capability rows per task:
  - routes: `<= 10`
  - workers: `1`
  - runtime components: `1`
- If scope exceeds limits, split work and create a follow-up packet.

## 6. Mandatory evidence in every PR

1. Tracker rows updated with status + evidence refs.
2. Test output snippet with commit SHA.
3. Explicit statement of preserved contracts.
4. Rollback verification note.

## 7. Example agent-ready task packet

```yaml
scope_id:
  - PROC-014
input_contracts:
  - plans/rewrite/generated/worker_migration_tracker.csv#PROC-014
  - plans/rewrite/queue_contracts.md#pull-metrics
output_files:
  - internal/workers/pullstatsflush/worker.go
  - tests/rewrite/contracts/workers/pullstatsflush_contract_test.go
validation_commands:
  - go test ./internal/workers/pullstatsflush/...
  - go test ./tests/rewrite/contracts/workers -run PullstatsFlush
rollback_path:
  switch: WORKER_OWNER_PULLSTATSREDISFLUSHWORKER
  rollback_value: python
out_of_scope:
  - redis key schema changes
  - metrics dashboard redesign
```

## 8. Exit criteria

- At least one task packet exists for each major workstream (`WS3`..`WS11`).
- Every packet is independently executable and testable.
- No packet requires undocumented architectural choices.
