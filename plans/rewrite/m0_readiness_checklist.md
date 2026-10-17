# M0 Readiness Checklist

Status: Blocked
Last updated: 2026-02-09

## 1. Purpose

Track exact readiness against M0 exit criteria from `plans/rewrite/quay_rewrite.md`.

## 2. Exit criteria status

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| `api_surface_inventory.md` complete and reviewed | pass | `plans/rewrite/api_surface_inventory.md` | Expanded inventory and route tracker coverage present. |
| `workers_inventory.md` complete and reviewed | pass | `plans/rewrite/workers_inventory.md` | Expanded worker/process inventory present. |
| `queue_contracts.md` complete and reviewed | pass | `plans/rewrite/queue_contracts.md` | Queue inventory/contracts documented. |
| `data_access_layer_design.md` approved | blocked | `plans/rewrite/data_access_layer_design.md` | Draft exists; approval/signoff not recorded. |
| `go_module_strategy.md` approved and Go scaffold/CI checks green | blocked | `plans/rewrite/go_module_strategy.md` | Strategy doc exists; root `go.mod` and CI checks not initialized yet. |
| `fips_crypto_migration.md` approved | blocked | `plans/rewrite/fips_crypto_migration.md` | Draft exists; compatibility signoff pending. |
| `storage_backend_inventory.md` approved with tracker coverage | blocked | `plans/rewrite/storage_backend_inventory.md`, `plans/rewrite/generated/storage_driver_migration_tracker.csv` | Draft + tracker exist; approval pending. |
| `registryd_design.md` approved | blocked | `plans/rewrite/registryd_design.md` | Draft exists; approval pending. |
| `redis_usage_inventory.md` approved | blocked | `plans/rewrite/redis_usage_inventory.md` | Draft exists; approval pending. |
| `performance_budget.md` baselines captured | blocked | `plans/rewrite/performance_budget.md` | Budget doc exists; baseline capture not yet attached. |
| deployment/config/image/TLS plans approved | blocked | `plans/rewrite/deployment_architecture.md`, `plans/rewrite/config_tool_evolution.md`, `plans/rewrite/image_strategy.md`, `plans/rewrite/tls_security_posture.md` | Drafts exist; approvals pending. |
| auth backend + notification plans approved | blocked | `plans/rewrite/auth_backend_inventory.md`, `plans/rewrite/notification_driver_inventory.md` | Drafts exist; approvals pending. |
| `ai_agent_guide.md` approved and task packets created | blocked | `plans/rewrite/ai_agent_guide.md` | Guide exists; task packets still need owner review and creation across WS3-WS11. |
| Contract fixture set established for all route families and queues | blocked | `plans/rewrite/test_implementation_plan.md`, `plans/rewrite/generated/route_contract_tests.csv`, `plans/rewrite/generated/queue_worker_contract_tests.csv` | Mapping exists; runnable fixture implementation not complete. |
| `route_auth_verification.md` shows zero unresolved auth rows | pass | `plans/rewrite/generated/route_auth_verification.md` | Unresolved auth rows = 0. |
| route-auth manual backlog `<= 50` rows | pass | `plans/rewrite/generated/route_auth_verification_checklist_summary.md` | Backlog is 0; all 413 rows are `verified-source-anchored`. |
| `route_parser_gaps.md` rows explicitly fixture-tracked | pass | `plans/rewrite/generated/route_parser_gaps.md` | Parser-gap inventory exists and remains tracked. |

## 3. Additional blockers affecting M0 confidence

| Item | Status | Evidence |
|---|---|---|
| Route/web count reconciliation (`web=66` vs `web=65`) | pass | `plans/rewrite/generated/route_family_counts.md`, `plans/rewrite/generated/rewrite_snapshot.md` |
| Owner signoff promotion (`verified-source-anchored` -> `verified`) | blocked | `plans/rewrite/signoff_workflow.md`, `plans/rewrite/signoff_schedule.md` |

## 4. Go/No-Go

- M0 go/no-go: **NO-GO**
- Blocking count: 11 core criteria + 1 additional blocker

## 5. Minimum actions to reach M0 go

1. Approve all draft architecture/security/deployment docs (G8-G15).
2. Capture baseline metrics for all `PB-*` budgets and link evidence.
3. Complete owner-signoff promotion for route/worker/runtime checklist rows.
