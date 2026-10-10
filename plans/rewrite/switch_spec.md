# Rewrite Switch Specification

Status: Draft
Last updated: 2026-02-08

## 1. Purpose

Define a concrete, implementable control plane for incremental Python->Go ownership cutover with fast rollback.

## 2. Design principles

- One capability has one active owner at a time.
- Ownership must be explicit and observable.
- Rollback must be a single change operation.
- Switches must be safe-by-default (`python` owner until promoted).
- Control semantics must support both startup-time and runtime updates.

## 3. Switch model

Use owner switches (enum), not paired booleans.

Allowed owner values:
- `python`
- `go`
- `off` (workers only; never valid for required API routes)

### 3.1 Route owner switches

Levels:
- Family default: `ROUTE_OWNER_FAMILY_<FAMILY>`
- Capability override: `ROUTE_OWNER_CAP_<CAPABILITY>`
- Route-method override (only where needed): `ROUTE_OWNER_ROUTE_<ROUTE_ID>`

Resolution order:
1. Route-method override
2. Capability override
3. Family default
4. Global default (`python`)

Examples:
- `ROUTE_OWNER_FAMILY_REGISTRY_V2=python`
- `ROUTE_OWNER_CAP_V2_PULL=go`
- `ROUTE_OWNER_ROUTE_ROUTE_0324=python`

### 3.2 Worker owner switches

Per process:
- `WORKER_OWNER_<PROGRAM_NAME>` where value in `{python,go,off}`

Examples:
- `WORKER_OWNER_NOTIFICATIONWORKER=go`
- `WORKER_OWNER_REPOMIRRORWORKER=python`

### 3.3 Cohort selectors (canary)

Independent routing selectors:
- `ROUTE_CANARY_ORGS`
- `ROUTE_CANARY_REPOS`
- `ROUTE_CANARY_USERS`
- `ROUTE_CANARY_PERCENT`

These selectors scope where `go` owner applies when owner policy is canary-gated.

## 4. Storage and distribution

Two-stage control delivery:

Stage A (bootstrap):
- Environment-backed values at process startup.
- Suitable for early bring-up and staging.

Stage B (required for production cutover):
- Runtime control source (dynamic config provider) with periodic refresh.
- Max propagation target: `< 30s`.
- Last-known-good cache and monotonic versioning required.
- Detailed option analysis and baseline recommendation: `plans/rewrite/switch_transport_design.md`.

## 5. Safety requirements

- Unknown owner values must fail closed to `python`.
- Switch parsing failures must not break request handling.
- Every owner decision emits a metric label (`owner=python|go`) and route/process id.
- A global kill switch exists for emergency failback:
  - `MIGRATION_FORCE_PYTHON=true` (routes + workers).

## 6. Integration points

- Route owner decisions used at edge/gateway dispatch and/or in-process router.
- Worker owner decisions integrate with supervisor/service startup policy.
- `QUAY_OVERRIDE_SERVICES` conflict resolution:
  - When both `QUAY_OVERRIDE_SERVICES` and an owner switch are set, the owner switch takes precedence.
  - If `QUAY_OVERRIDE_SERVICES` is used alongside owner switches, emit a deprecation warning in logs.
  - `QUAY_OVERRIDE_SERVICES` is deprecated for migration-scoped capabilities; it remains valid only for non-migration service control (e.g., disabling auxiliary processes).
  - Phase-out: remove `QUAY_OVERRIDE_SERVICES` support for migration-scoped capabilities after M5 (Python deactivation).

## 7. Rollback contract

Rollback operation for one capability/process must be:
1. Set owner back to `python`.
2. Confirm ownership metrics flip.
3. Confirm error/latency/backlog return to baseline.

No code deploy should be required for rollback.

## 8. Implementation checklist

- Define switch schema and validation.
- Implement owner decision library used by both Python and Go control paths.
- Add metrics and audit logs for owner decisions.
- Add staging tests for precedence resolution.
- Add canary selector validation tests.
- Add propagation delay testing (< 30s SLO from switch transport design).
- Add rollback drill exercises for route and worker owner flips.
- Add production runbook for emergency global failback.
