# Rewrite Implementation Kickoff Checklist

Status: Draft
Last updated: 2026-02-09

## 1. Goal

Translate planning artifacts into first implementation sprint execution without hidden blockers.

## 2. Must-complete before code migration starts

1. Confirm D-001..D-005 approvals in `decision_log.md`.
2. Lock switch transport baseline (D-002) and publish config schema.
3. Approve blocking architecture artifacts (G8-G15):
- `data_access_layer_design.md`
- `go_module_strategy.md`
- `fips_crypto_migration.md`
- `storage_backend_inventory.md`
- `registryd_design.md`
- `redis_usage_inventory.md`
- `deployment_architecture.md`
- `config_tool_evolution.md`
- `image_strategy.md`
- `tls_security_posture.md`
- `auth_backend_inventory.md`
- `notification_driver_inventory.md`
- `performance_budget.md`
4. Approve implementation-enablement guide:
- `ai_agent_guide.md`
5. Review `plans/rewrite/m0_readiness_checklist.md` and close all `blocked` rows.
6. Route-auth manual backlog remains at 0 rows (`route_auth_verification_checklist.csv`).
7. Assign owners for signoff batches using `owner_assignment_summary.md`.
8. Stand up parity test scaffolding from `test_implementation_plan.md`.
9. Start baseline metric capture and update `generated/performance_baseline_status.md`.
10. Confirm upload hasher-state dual-runtime strategy is approved in `registryd_design.md`.
11. Confirm expanded crypto inventory and AES key-derivation parity plan are approved in `fips_crypto_migration.md`.

## 3. Sprint 1 recommended execution

1. Implement control-plane primitives:
- route owner resolution
- worker owner resolution
- emergency fallback (`MIGRATION_FORCE_PYTHON`)
2. Initialize Go test harness and run first parity tests:
- `PT-ROUTE-*` for `A1` routes
- `WBT-*`/`WRT-*`/`WMT-*` for `P0/P1` workers
3. Initialize Go module + CI gates from `go_module_strategy.md`:
- root `go.mod`
- `go test ./...`
- `go vet ./...`
4. Execute first signoff batches:
- `signoff_batch_a1_routes.csv`
- `signoff_batch_wp0_workers.csv`
- `signoff_batch_wp1_workers.csv`
5. Move completed rows to `verified` with `owner_signoff` and evidence links.

## 4. Exit criteria for kickoff phase

- First route batch and first worker batches verified with owner signoff.
- Rollback drill run once for route and worker owner flips.
- No unresolved high-severity parity regressions in pilot scope.
