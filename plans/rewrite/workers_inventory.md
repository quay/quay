# Workers and Process Inventory

Status: Expanded
Last updated: 2026-02-09

## 1. Purpose

Track all background processes and migration status.

## 2. Authoritative definitions

- `conf/init/supervisord_conf_create.py`
- `conf/supervisord.conf.jnj`
- `workers/*`
- `buildman/*`

## 3. Exhaustive source-of-truth artifact

- `plans/rewrite/generated/worker_inventory.md`
- `plans/rewrite/generated/worker_migration_tracker.csv`
- `plans/rewrite/generated/worker_migration_tracker_summary.md`
- `plans/rewrite/generated/worker_process_contract_tests.csv`
- `plans/rewrite/generated/worker_process_contract_tests_summary.md`
- `plans/rewrite/generated/worker_semantics_verification.md`
- `plans/rewrite/generated/worker_phase_sequence.md`
- `plans/rewrite/generated/worker_verification_checklist.csv`
- `plans/rewrite/generated/worker_verification_checklist_summary.md`
- `plans/rewrite/generated/worker_verification_progress.md`
- `plans/rewrite/generated/worker_process_coverage_audit.md`
- `plans/rewrite/generated/worker_module_coverage_audit.md`

This file includes:
- all supervisor programs
- default `autostart` values
- Python module entrypoints
- worker classes and queue refs
- feature-gated startup guards

Worker migration tracker includes per-process:
- trigger type
- queue/input contract
- idempotency rule
- retry policy
- side effects
- rollout phase
- rollback steps
- explicit enable/disable control placeholders
- contract test mapping in:
  - `plans/rewrite/generated/queue_worker_contract_tests.csv`
  - notification behavior mapping in `plans/rewrite/notification_driver_inventory.md`

Control-model note:
- Canonical switch model is owner-based (`WORKER_OWNER_<PROGRAM>=python|go|off`) per `plans/rewrite/switch_spec.md`.
- Existing placeholder columns in generated tracker remain as transition aids and should be normalized to owner-switch form during implementation.
- Verification workflow: `worker_verification_checklist.csv` is source-anchored (`verified-source-anchored`) per row, then promoted with `owner_signoff` during implementation.
- Current checklist status: `verified-source-anchored=35`, `retired-approved=1`.
- Checklist includes `suggested_owner` and `review_wave` for execution sequencing.

## 4. Baseline summary

- Supervisor programs: `36`
- Default autostart disabled in registry profile: `repomirrorworker` (explicitly `false`)
- Queue-worker processes (QueueWorker subclass):
  - `chunkcleanupworker`
  - `storagereplication`
  - `repositorygcworker`
  - `namespacegcworker`
  - `notificationworker`
  - `securityscanningnotificationworker`
  - `proxycacheblobworker`
  - `exportactionlogsworker`
- Build manager process: `builder` (`python -m buildman.builder`)

## 5. High-risk semantics to preserve

1. Build manager uses ordered queue claims (`ordering_required=True`) and custom retry/timeout handling.
2. Namespace/repository GC workers require global lock behavior (`LARGE_GARBAGE_COLLECTION`) and long reservations.
3. Queue workers depend on `QueueWorker` watchdog + `extend_processing` semantics.
4. Worker startup is guarded by feature flags and runtime conditions (account recovery mode, readonly/disable pushes, storage engine checks).
5. Supervisor service-level toggles (`QUAY_SERVICES`, `QUAY_OVERRIDE_SERVICES`) and feature toggles both influence runtime behavior and must be represented in Go cutover controls.

## 6. Migration policy per process

For each program in `worker_inventory.md`, record:
- Trigger mode (`queue`, `scheduler`, `event-loop`, or `service-support`)
- Inputs (queue payloads/config/db scans)
- Side effects (db mutations/storage operations/outbound callbacks)
- Idempotency strategy
- Retry strategy
- Locking/concurrency invariants
- Existing Python disable switch
- Planned Go enable switch
- Canary scope and rollback path

## 7. Gaps found vs earlier draft

1. Earlier draft under-specified process count and startup controls.
2. `repomirrorworker` default autostart behavior was missing from migration sequencing.
3. Worker-level feature guard expressions are numerous and must be copied as behavior, not simplified.
4. Build manager semantics must be treated as first-class migration scope, not an implementation detail.
5. Config drift was resolved by decision D-001: `ip-resolver-update-worker` is treated as retired and removed from active migration execution scope.

Cross-plan dependencies:
- Redis semantics: `plans/rewrite/redis_usage_inventory.md`
- Storage and mirror dependencies: `plans/rewrite/storage_backend_inventory.md`
- Deployment/runtime execution model: `plans/rewrite/deployment_architecture.md`

## 8. Config drift disposition (closed)

`ip-resolver-update-worker` disposition is approved:
- remove stale service-map references and mark retired (`retired-approved`).
- if reintroduced later, treat as a new capability with explicit implementation and parity plan.
