# Worker Semantics Verification

This report captures source anchors for retry/idempotency semantics used in migration planning.

## Shared queue-worker semantics
- Queue polling/claim/processing lifecycle: `workers/queueworker.py`
- Retry handling via `incomplete(...)` and completion via `complete(...)`: `workers/queueworker.py`
- Lease extension path `extend_processing(...)`: `workers/queueworker.py`

## Build queue ordered semantics
- Ordered queue claim (`ordering_required=True`): `buildman/manager/ephemeral.py`
- Requeue paths (`restore_retry=True|False`, `retry_after=...`): `buildman/manager/ephemeral.py`

## High-risk process anchors
- `PROC-021` `chunkcleanupworker`: `workers/chunkcleanupworker.py`
- `PROC-022` `exportactionlogsworker`: `workers/exportactionlogsworker.py`
- `PROC-023` `notificationworker`: `workers/notificationworker/notificationworker.py`
- `PROC-024` `proxycacheblobworker`: `workers/proxycacheblobworker.py`
- `PROC-025` `securityscanningnotificationworker`: `workers/securityscanningnotificationworker.py`
- `PROC-026` `storagereplication`: `workers/storagereplication.py`
- `PROC-033` `gcworker`: `workers/gc/gcworker.py`
- `PROC-034` `namespacegcworker`: `workers/namespacegcworker.py`
- `PROC-035` `repositorygcworker`: `workers/repositorygcworker.py`
- `PROC-036` `builder`: `buildman/builder.py`

## Note
- Full row-by-row owner verification is pending and tracked in `temp.md` follow-ups.
