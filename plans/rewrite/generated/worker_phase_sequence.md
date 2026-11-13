# Worker Phase Sequence

Process rollout sequence from `worker_migration_tracker.csv`.

## P0

- `PROC-001` `dnsmasq` (service-support, planned)
- `PROC-002` `gunicorn-registry` (service-support, planned)
- `PROC-003` `gunicorn-secscan` (service-support, planned)
- `PROC-004` `gunicorn-web` (service-support, planned)
- `PROC-005` `memcache` (service-support, planned)
- `PROC-006` `nginx` (service-support, planned)
- `PROC-007` `pushgateway` (service-support, planned)
- `PROC-008` `ip-resolver-update-worker` (unknown, retired-approved)

## P1

- `PROC-009` `buildlogsarchiver` (background-worker, planned)
- `PROC-010` `expiredappspecifictokenworker` (background-worker, planned)
- `PROC-011` `globalpromstats` (background-worker, planned)
- `PROC-012` `manifestbackfillworker` (background-worker, planned)
- `PROC-013` `manifestsubjectbackfillworker` (background-worker, planned)
- `PROC-014` `pullstatsredisflushworker` (background-worker, planned)
- `PROC-015` `queuecleanupworker` (background-worker, planned)
- `PROC-016` `quotaregistrysizeworker` (background-worker, planned)
- `PROC-017` `quotatotalworker` (background-worker, planned)
- `PROC-018` `repositoryactioncounter` (background-worker, planned)
- `PROC-019` `servicekey` (background-worker, planned)

## P2

- `PROC-020` `blobuploadcleanupworker` (background-worker, planned)
- `PROC-021` `chunkcleanupworker` (background-worker, planned)
- `PROC-022` `exportactionlogsworker` (background-worker, planned)
- `PROC-023` `notificationworker` (background-worker, planned)
- `PROC-024` `proxycacheblobworker` (background-worker, planned)
- `PROC-025` `securityscanningnotificationworker` (background-worker, planned)
- `PROC-026` `storagereplication` (background-worker, planned)

## P3

- `PROC-027` `autopruneworker` (background-worker, planned)
- `PROC-028` `logrotateworker` (background-worker, planned)
- `PROC-029` `reconciliationworker` (background-worker, planned)
- `PROC-030` `repomirrorworker` (background-worker, planned)
- `PROC-031` `securityworker` (background-worker, planned)
- `PROC-032` `teamsyncworker` (background-worker, planned)

## P4

- `PROC-033` `gcworker` (background-worker, planned)
- `PROC-034` `namespacegcworker` (background-worker, planned)
- `PROC-035` `repositorygcworker` (background-worker, planned)

## P5

- `PROC-036` `builder` (build-manager, planned)
