# Switch Transport Design

Status: Draft
Last updated: 2026-02-08

## 1. Goal

Provide production-safe distribution of route/worker owner switches with fast rollback and no deploy requirement.

## 2. Constraints from current codebase

- Config overrides are loaded through `config_provider` during startup (`_init.py`, `app.py`).
- Providers exist for filesystem and Kubernetes secret backed config (`util/config/provider/*`).
- Current model is startup-oriented; runtime propagation is not built in.

## 3. Options

### Option A: Environment-only switches

- Mechanism: owner switches via env vars, process restart required.
- Pros: minimal implementation.
- Cons: rollback speed tied to restart/deploy; weak canary ergonomics.

### Option B: Config-provider backed runtime polling (recommended)

- Mechanism:
  - Store switches in override config (`config.yaml`) under a migration section.
  - Add lightweight runtime polling (or file watch) in Python and Go components.
  - Apply monotonic versioned switch snapshots with fail-closed default to `python`.
- Pros:
  - Reuses existing config distribution model (file + k8s secret).
  - Works for disconnected/mirror-registry environments.
  - Supports rollback without redeploy.
- Cons:
  - Requires runtime reload code and consistency safeguards.

### Option C: New dedicated dynamic store (DB/Redis/service)

- Mechanism: separate control-plane store + client library.
- Pros: low-latency updates and central governance.
- Cons: new operational dependency and larger implementation scope.

## 4. Recommended baseline

Choose Option B for migration implementation, with these requirements:

- Poll interval target: 5-15s.
- Max propagation SLO: <30s.
- Snapshot includes `version`, `updated_at`, and full owner map.
- Parse/validation failure falls back to last-known-good snapshot; hard fail closes to `python`.
- Owner decision metrics include snapshot version.

## 5. Rollback operation

1. Update switch snapshot to owner=`python` for impacted capabilities/processes.
2. Wait for propagation (<30s target).
3. Confirm owner-decision metrics and error/latency/backlog recovery.

## 6. Implementation tasks

- Extend config schema with migration switch namespace.
- Implement Python and Go switch snapshot loaders with shared validation rules.
- Add switch snapshot version metric and decision logs.
- Add staging chaos tests for malformed/partial switch snapshots.
