# Rewrite Program Gates Dashboard

Status: Active
Last updated: 2026-02-09

## 1. Purpose

Provide milestone-level readiness view across all rewrite planning artifacts.

## 2. Gate status

| Gate | Description | Status | Evidence |
|---|---|---|---|
| G0 | Inventory and contract mapping complete | complete | route/worker/queue/runtime inventories generated; coverage audits (`http_surface_coverage_audit.md`, `worker_process_coverage_audit.md`) |
| G1 | Ownership switch/control-plane design complete | complete | `switch_spec.md`, `switch_transport_design.md`, `cutover_matrix.md`; D-002 approved |
| G2 | Critical decision set approved | complete | D-001..D-005 approved; D-005 finalized as Go-native `containers/image` migration |
| G3 | Route/worker verification checklists source-anchored | ready | worker checklist `35 verified-source-anchored + 1 retired-approved`; route checklist `413 verified-source-anchored`, `0` manual backlog |
| G4 | Test implementation rollout defined | ready | `test_implementation_plan.md`, `ai_agent_guide.md` |
| G5 | Runtime support component execution waves defined | ready | `runtime_component_execution_plan.md`, runtime mapping wave fields |
| G6 | Rollout/rollback playbooks complete | ready | `rollout_playbooks.md`, route/worker sequence artifacts |
| G7 | Operational tooling migration disposition complete | mostly-ready | D-004 baseline complete; transition-period script validation still required |
| G8 | Data access layer architecture approved | blocked | `data_access_layer_design.md` + `go_module_strategy.md` drafted; approval and scaffold init pending |
| G9 | FIPS/crypto migration plan approved | blocked | `fips_crypto_migration.md` drafted; compatibility test corpus pending |
| G10 | Storage backend migration plan approved | blocked | `storage_backend_inventory.md` + `generated/storage_driver_migration_tracker.csv` drafted |
| G11 | Registryd architecture approved (`/v1` + `/v2`) | blocked | `registryd_design.md` drafted |
| G12 | Redis migration inventory approved | blocked | `redis_usage_inventory.md` drafted |
| G13 | Deployment/image/config/TLS plans approved | blocked | `deployment_architecture.md`, `config_tool_evolution.md`, `image_strategy.md`, `tls_security_posture.md` drafted |
| G14 | Auth backend + notification parity plans approved | blocked | `auth_backend_inventory.md`, `notification_driver_inventory.md` drafted |
| G15 | Performance budgets baselined and accepted | blocked | `performance_budget.md` drafted; baseline capture pending |

## 3. Remaining gate-to-green actions

1. Promote source-anchored rows to `verified` with owner signoff + test evidence.
2. Approve G8-G15 architecture artifacts with named owners.
3. Capture and publish baseline performance measurements for all `PB-*` budgets.
4. Initialize root Go module and CI checks from `go_module_strategy.md`.

## 4. Update policy

- Update this dashboard whenever a gate status changes.
- Keep status values strict: `pending`, `mostly-ready`, `ready`, `ready-for-approval`, `blocked`, `complete`.
