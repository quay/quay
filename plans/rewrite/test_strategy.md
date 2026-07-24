# Rewrite Test Strategy

Status: Draft
Last updated: 2026-02-09

## 1. Goal

Prove behavior parity for every migrated endpoint, worker, and runtime support component.

Implementation details and harness rollout:
- `plans/rewrite/test_implementation_plan.md`
- `plans/rewrite/signoff_workflow.md`
- `plans/rewrite/performance_budget.md`

## 2. Test planes

1. Route contract tests
- input/output parity (status, headers, body schema)
- auth parity (anonymous/session/oauth/jwt)
- error model parity
- feature-gated route presence/absence parity

2. Queue and worker contract tests
- payload schema compatibility in mixed Python/Go mode
- retry, lease extension, incomplete/complete semantics
- ordered build queue semantics
- idempotency under duplicate delivery

3. Performance and reliability
- enforce budget IDs in `performance_budget.md` (`PB-REG-*`, `PB-API-*`, `PB-WORKER-*`, `PB-DB-*`)
- worker throughput and queue lag parity
- resource usage and failure behavior during canaries

4. Rollback validation
- route-owner and worker-owner rollback drills
- replay and reconciliation checks after rollback

## 3. Artifact inputs

- `plans/rewrite/generated/route_inventory.md`
- `plans/rewrite/generated/non_blueprint_route_inventory.md`
- `plans/rewrite/generated/route_migration_tracker.csv`
- `plans/rewrite/generated/feature_gate_inventory.md`
- `plans/rewrite/generated/queue_inventory.md`
- `plans/rewrite/generated/queue_payload_inventory.md`
- `plans/rewrite/generated/worker_inventory.md`
- `plans/rewrite/generated/worker_migration_tracker.csv`
- `plans/rewrite/generated/runtime_component_mapping.csv`

## 4. Required mapping outputs

1. `route_contract_tests.csv`
- route id
- source file
- auth mode
- feature gates
- golden fixture id
- parity test id
- performance budget id

2. `queue_worker_contract_tests.csv`
- queue name
- producer fixture id
- consumer behavior test id
- retry/idempotency test id
- mixed-mode compatibility test id

3. `worker_process_contract_tests.csv`
- process id
- behavior test id
- rollout wave
- rollback drill id

## 5. Release gate

No capability flips to `go` owner unless:
- route/worker parity tests pass
- queue compatibility tests pass
- auth-mode matrix coverage passes (`auth_mode_matrix.md`)
- route-auth checklist rows for flipped capability are `verified` with owner signoff
- performance budgets pass
- rollback drill passes
