# Worker/Process Coverage Audit

Compare supervisor programs + service maps with `worker_migration_tracker.csv`.

- supervisor programs: 35
- service-map entries in `supervisord_conf_create.py`: 36
- tracker program rows: 36

## Supervisor programs missing from tracker

- none

## Tracker programs missing from supervisor template

- `ip-resolver-update-worker`

## Service-map entries without supervisor program

- `ip-resolver-update-worker` (known drift D-001)

## Supervisor programs not in service-map defaults

- none

## Result

- Tracker coverage is complete for supervisor programs; only known D-001 drift remains.
