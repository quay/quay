# `ip-resolver-update-worker` Disposition

Status: Proposed
Last updated: 2026-02-08

## 1. Evidence

- Present in service maps only:
  - `conf/init/supervisord_conf_create.py` (`registry_services`, `config_services`)
- Missing from actual supervisor template program blocks:
  - no `[program:ip-resolver-update-worker]` in `conf/supervisord.conf.jnj`
- No worker implementation/module found in repository:
  - no `workers/*` or other executable module for this service name

## 2. Recommended decision

Adopt **retire stale entry**:
- Remove `ip-resolver-update-worker` keys from service maps in `conf/init/supervisord_conf_create.py`.
- Mark process as retired in migration artifacts.

Rationale:
- Current entry is non-functional (cannot be started by supervisor template).
- Keeping stale entry increases migration/control-plane ambiguity without delivering behavior.

## 3. Migration artifact updates after approval

- `worker_migration_tracker.csv`
  - `PROC-008` -> `migration_status=retired-approved`
  - `rollout_phase=P0` remains informational
  - notes updated with approval reference
- `worker_verification_checklist.csv`
  - `PROC-008` -> `verification_status=retired-approved`

## 4. Implementation change set (after approval)

1. Edit `conf/init/supervisord_conf_create.py`:
- Remove entries:
  - `"ip-resolver-update-worker": {"autostart": "true"}`
  - `"ip-resolver-update-worker": {"autostart": "false"}`

2. Validation:
- Generate supervisord config and confirm no missing-service references remain.
- Confirm `QUAY_SERVICES` / `QUAY_OVERRIDE_SERVICES` behavior unchanged for all existing programs.

## 5. Rollback

If this decision is reversed:
- Restore service-map entries and add a real `[program:ip-resolver-update-worker]` template block plus implementation module, then reclassify as active migration scope.
