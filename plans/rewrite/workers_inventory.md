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
6. `reconciliationworker` acquires a Redis global lock before executing. During Python/Go coexistence, this lock provides a runtime safety net against concurrent reconciliation runs — both workers can be deployed simultaneously and the lock guarantees mutual exclusion. The Go implementation must use the exact same Redis key, TTL, renewal, and release pattern as Python. The `WORKER_OWNER_RECONCILIATIONWORKER` switch remains the intentional operational control for which runtime should run, but the Redis lock prevents duplicate external API calls (Stripe/marketplace) even if both workers are accidentally active. Verify the lock key and semantics from the Python source before Go implementation.

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

## 9. Reconciliation worker: event-driven migration proposal (D-006)

Decision: `plans/rewrite/open_decisions.md` D-006

### 9.1 Problem

The Python `reconciliationworker` polls every 5 minutes, iterating all active users and making external API calls (Stripe `Customer.retrieve` + marketplace `lookup_subscription` / `create_entitlement`) per user. This has several issues:

1. **Unnecessary load**: The vast majority of users' billing state has not changed. O(users) external API calls per cycle is disproportionate.
2. **No idempotency**: Neither marketplace `create_entitlement` (POST to `/subscription/v5/createPerm`) nor Stripe `Customer.create` pass idempotency keys. If a call succeeds but the response times out, the next cycle retries without deduplication.
3. **Unsafe mutation pattern**: Billing API endpoints follow a create-externally-then-save-to-DB pattern (`billing.Customer.create()` → `user.stripe_id = cus.id` → `user.save()`). If the DB save fails after the external call succeeds, the external resource is orphaned.
4. **Coexistence risk window**: During Python/Go coexistence, more frequent polling increases the chance of edge-case duplicate calls even with the Redis lock in place (lock TTL expiry, network partition).

### 9.2 Existing event sources

Quay already receives real-time billing change signals:

| Event source | Trigger | Current handler | Reconciliation action needed |
|---|---|---|---|
| Stripe webhook `checkout.session.completed` | User completes checkout | `endpoints/webhooks.py` — sends email | Reconcile entitlement for this user |
| Stripe webhook `customer.subscription.created` | New subscription | `endpoints/webhooks.py` — sends email | Reconcile entitlement for this user |
| Stripe webhook `customer.subscription.updated` | Plan change | `endpoints/webhooks.py` — sends email | Reconcile entitlement for this user |
| Stripe webhook `customer.subscription.deleted` | Cancellation | `endpoints/webhooks.py` — sends email | Remove/downgrade entitlement for this user |
| Billing API `POST /v1/user/plan` | User creates plan | `endpoints/api/billing.py` | Reconcile entitlement for this user |
| Billing API `PUT /v1/user/plan` | User changes plan | `endpoints/api/billing.py` | Reconcile entitlement for this user |
| Billing API `POST /v1/organization/<orgname>/marketplace` | SKU binding | `endpoints/api/billing.py` | Reconcile entitlement for this org |

### 9.3 Proposed Go architecture

Replace the full-table polling worker with two components:

**A. Event-driven per-user reconciliation**

When a Stripe webhook or billing API mutation occurs, enqueue a reconciliation job for the specific user/org affected. The reconciliation logic (lookup customer, check entitlements, create if missing) remains the same but runs only for the affected entity.

Implementation options:
- Use the existing queue infrastructure (new `entitlement_reconciliation` queue) with the standard `QueueWorker` pattern.
- Or handle inline in the webhook/API handler if the marketplace API calls are fast enough (sub-second with 20s timeout).

Benefits:
- Reconciliation happens within seconds of the billing event, not up to 5 minutes later.
- External API calls reduced from O(users) per cycle to O(events) per cycle.
- Idempotency is simpler — the event payload identifies the exact user, and the reconciliation logic can check-then-act for a single entity with a much narrower race window.

**B. Low-frequency consistency sweep**

Keep a full-table reconciliation sweep but reduce frequency to hourly or daily. This catches:
- Out-of-band subscription changes made directly in the Red Hat portal (no webhook from Quay's perspective).
- Missed or failed webhook deliveries.
- Drift from any other source.

This sweep is the safety net, not the primary reconciliation path.

**C. Idempotency improvements**

Regardless of whether event-driven migration is adopted:
- Add idempotency keys to Stripe `Customer.create` calls (Stripe supports `Idempotency-Key` header natively).
- Verify whether Red Hat marketplace `createPerm` endpoint supports idempotency keys or has server-side deduplication for duplicate customer+SKU pairs. Document the finding.
- Add request correlation IDs to marketplace API calls for traceability.

### 9.4 Compatibility and rollback

- During coexistence, the Python poller can remain active as the consistency sweep while Go handles event-driven reconciliation. The Redis lock prevents concurrent execution of the sweep.
- Rollback: disable Go event-driven handlers, re-enable Python 5-minute poller via `WORKER_OWNER_RECONCILIATIONWORKER=python`. No data migration required — both approaches read the same Stripe/marketplace state.
- The event-driven approach does not change the database schema or the external API contracts. It changes only when and how often the same reconciliation logic runs.

### 9.5 Scope decision required

This proposal goes beyond strict parity. The team must decide:
- **Option A**: Port the 5-minute poller as-is for parity, track event-driven migration as a separate follow-up.
- **Option B (recommended)**: Implement event-driven reconciliation as part of the Go worker migration (WS5/P3), since the webhook handlers are being migrated anyway (WS4) and the integration point is natural.

## 10. Config drift disposition (closed)

`ip-resolver-update-worker` disposition is approved:
- remove stale service-map references and mark retired (`retired-approved`).
- if reintroduced later, treat as a new capability with explicit implementation and parity plan.
