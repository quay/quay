# Open Decisions Register

Status: Resolved (all listed decisions approved)
Last updated: 2026-02-09

## 1. Purpose

Track planning decisions that block or materially change implementation sequencing.

## 2. Decision table

| ID | Decision | Status | Suggested owner | Target approval date | Current evidence | Recommended default | Impact if delayed |
|---|---|---|---|---|---|---|---|
| D-001 | `ip-resolver-update-worker` disposition | approved | runtime-platform | 2026-02-13 | Present in `conf/init/supervisord_conf_create.py`; no supervisor program block; no worker implementation found in repo (`ip_resolver_update_worker_disposition.md`) | Remove stale service-map entry and treat as retired unless concrete worker implementation is introduced | Worker tracker remains blocked and ownership controls stay ambiguous |
| D-002 | Production switch transport | approved | control-plane | 2026-02-13 | Switch model defined in `switch_spec.md`; transport options in `switch_transport_design.md` | Adopt Option B: config-provider backed runtime polling with `<30s` propagation and fallback-to-python on parse failure | Rollback may require deploy/restart; canary safety reduced |
| D-003 | DB exception governance | approved | db-architecture | 2026-02-20 | Policy exists in `db_migration_policy.md`; approvers/process now documented in backlog/gates | Require explicit migration exception record + designated approvers before non-additive changes | Risk of untracked breaking schema changes during mixed runtime |
| D-004 | Operational CLI tooling disposition | approved | release-management | 2026-02-20 | `operational_tooling_plan.md` + tooling inventory identify scripts requiring disposition | Treat tooling scripts as `retire-approved` by default unless transition-period exception is approved | Python dependency may linger and block retirement gate |
| D-005 | Repo mirror implementation path (`skopeo` subprocess vs Go `containers/image`) | approved | registry-platform | 2026-02-09 | User approved Go-native migration on 2026-02-09; source anchor: `util/repomirror/skopeomirror.py` | Migrate to Go-native `containers/image`; keep temporary compatibility fallback only during transition testing | Mirror/image workstreams proceed with finalized dependency direction |

## 3. Resolution rules

- Every decision must include: owner, due date, chosen option, and rollback implication.
- Resolved decisions are copied into relevant sub-plans.
- Approval outcomes are recorded in `plans/rewrite/decision_log.md`.
- Consolidated recommendations are maintained in `plans/rewrite/decision_approval_packet.md`.
