# Rewrite Decision Approval Packet

Status: Active
Last updated: 2026-02-09

## 1. Purpose

Provide one-page record of approved outcomes from `open_decisions.md`.

## 2. Approved outcomes

## D-001: `ip-resolver-update-worker` disposition

- Outcome: approved retirement of stale reference (remove service-map entry).
- Evidence:
  - present in `conf/init/supervisord_conf_create.py`
  - no matching `[program:ip-resolver-update-worker]` in `conf/supervisord.conf.jnj`
  - no worker implementation module found
  - detailed package: `plans/rewrite/ip_resolver_update_worker_disposition.md`
- Rollback implication:
  - if later required, introduce as a new explicit capability with implementation + supervisor program.

## D-002: switch transport baseline

- Outcome: approved Option B from `switch_transport_design.md`.
- Option summary:
  - config-provider backed polling in all services/workers
  - `<30s` propagation target
  - parse/load failure defaults route/worker owner to `python`
- Rollback implication:
  - forced-global fallback remains available via emergency override.

## D-003: DB exception governance

- Outcome: approved explicit exception records + designated approvers before non-additive schema changes.
- Evidence:
  - policy defined in `db_migration_policy.md`
- Rollback implication:
  - no schema-contract changes proceed without approved fallback plan.

## D-004: operational CLI tooling disposition

- Outcome: scripts are not critical for migration and do not need Go ports by default.
- Evidence:
  - scripts inventoried in `generated/operational_tooling_inventory.md`
  - policy in `operational_tooling_plan.md`
  - dispositions in `generated/operational_tooling_disposition.csv`
- Rollback implication:
  - if a script is later found critical, open a targeted exception.

## D-005: repo mirror implementation path

- Outcome: approved migration to Go-native `containers/image`.
- Evidence:
  - user approval recorded on 2026-02-09
  - current Python source shells out via `util/repomirror/skopeomirror.py`
- Rollback implication:
  - temporary compatibility fallback may be retained during transition testing only.

## 3. Post-approval checklist

1. Mark each decision in `decision_log.md`.
2. Update decision status in `open_decisions.md`.
3. Apply resulting plan edits in impacted sub-plans.
