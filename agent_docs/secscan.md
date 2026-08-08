# Security Scanning (Clair Integration)

## Architecture Overview

Quay integrates with [Clair](https://github.com/quay/clair) for container image
vulnerability scanning. The scanning subsystem has three main components:

1. **`SecurityWorker`** (`workers/securityworker/securityworker.py`) — background
   worker that periodically indexes manifests by submitting them to Clair. Runs
   two operations on a configurable interval (`SECURITY_SCANNER_INDEXING_INTERVAL`,
   default 30s):
   - `_index_in_scanner()` — full-range indexing across all manifest IDs
   - `_index_recent_manifests_in_scanner()` — indexes only recent manifests

2. **Secscan model layer** (`data/secscan_model/`) — implements the indexing
   logic and vulnerability report loading:
   - `secscan_v4_model.py` — V1 indexer (`V4SecurityScanner`), uses
     `yield_random_entries()` for batch iteration
   - `secscan_v4_model_v2.py` — V2 indexer (`V4SecurityScannerV2`), uses
     PostgreSQL `FOR UPDATE SKIP LOCKED` for lock-free work distribution
   - `interface.py` — abstract interfaces (`SecurityScannerReadInterface`,
     `SecurityScannerIndexerInterface`)
   - `__init__.py` — `SecurityScannerModelProxy` that delegates to V1/V2

3. **Clair API client** (`util/secscan/v4/api.py`) — HTTP client for Clair's
   indexer, matcher, and notifier APIs. Handles JWT signing via PSK.

### Key Model: `ManifestSecurityStatus`

Defined in `data/database.py`, this model tracks the scan state for each
manifest:

| Field            | Type                      | Purpose |
|------------------|---------------------------|---------|
| `manifest`       | `ForeignKeyField(Manifest)` | One-to-one link to the manifest (unique) |
| `repository`     | `ForeignKeyField(Repository)` | Denormalized for efficient queries |
| `index_status`   | `ClientEnumField(IndexStatus)` | Current scan state (see below) |
| `error_json`     | `JSONField`               | Error details from the last scan attempt |
| `last_indexed`   | `DateTimeField`           | Timestamp of the last indexing attempt |
| `indexer_hash`   | `CharField(128)`          | Clair's indexer state hash at time of scan |
| `indexer_version`| `ClientEnumField(IndexerVersion)` | Always `V4` for Clair v4 |
| `metadata_json`  | `JSONField`               | Retry tracking metadata (see below) |

### `IndexStatus` Enum

```python
class IndexStatus(IntEnum):
    SCAN_RETRIES_EXHAUSTED = -4  # Retry budget spent for current indexer hash
    MANIFEST_LAYER_TOO_LARGE = -3  # Layer exceeds SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE
    MANIFEST_UNSUPPORTED = -2  # Manifest list, artifact, or no container layers
    FAILED = -1  # Scan failed, eligible for retry
    PENDING = 0  # Initial state (V2 indexer only)
    IN_PROGRESS = 1  # Claimed by a worker, scan in flight
    COMPLETED = 2  # Successfully scanned
```

### Workers and Notifications

- **`SecurityWorker`** — drives indexing. Can optionally acquire a global lock
  (`SECURITY_SCANNER_V4_LOCK`) to prevent concurrent full-range indexing.
- **`SecurityScanningNotificationWorker`**
  (`workers/securityscanningnotificationworker.py`) — processes vulnerability
  notifications from Clair's notifier API. When Clair detects a new
  vulnerability affecting previously-indexed manifests, this worker pages
  through notification results and emits Quay `vulnerability_found`
  notifications for affected repositories.

## Indexer Hash Lifecycle

The indexer hash represents Clair's internal configuration state — effectively
a version identifier for the set of updaters, matchers, and vulnerability
databases Clair is using. When Clair's configuration changes (e.g., after an
upgrade or a vulnerability database update), the hash changes.

### Flow

1. **Fetch state:** The indexer calls `SecurityScannerAPI.state()` which hits
   Clair's `/indexer/api/v1/index_state` endpoint. Returns
   `{"state": "<hash>"}`.

2. **Index manifest:** `_secscan_api.index(manifest, layers)` submits the
   manifest to Clair's `/indexer/api/v1/index_report` endpoint. On success,
   Clair returns an `IndexReport` and an `ETag` header containing the indexer
   hash at the time of indexing.

3. **Store result:** The indexer writes the ETag value to
   `ManifestSecurityStatus.indexer_hash`. This records which Clair
   configuration was used to produce the scan result.

4. **Trigger reindexing:** On subsequent cycles, the `needs_reindexing_query`
   (V1) or the hash-mismatch clause in `_find_and_claim_batch` (V2) identifies
   manifests where `indexer_hash != current_hash`. These are re-scanned so
   results stay current with Clair's latest vulnerability data.

### Why Hash Scoping Matters for Retry Budgets

The retry budget (`metadata_json.retry_count`) must be scoped to the indexer
hash. If a manifest fails 5 times under hash `abc123` because of a Clair bug,
and Clair is then upgraded (changing the hash to `def456`), the manifest should
be retried under the new hash — the bug that caused the failures may be fixed.

The `metadata_json` field tracks this:

```json
{
  "retry_count": 3,
  "last_failed_hash": "abc123"
}
```

When the current indexer hash differs from `last_failed_hash`, the retry count
resets to 1. This ensures manifests are not permanently blacklisted across Clair
upgrades.

When `retry_count >= SECURITY_SCANNER_MAX_SCAN_RETRIES` (default 5) and the
hash matches, the manifest transitions to `SCAN_RETRIES_EXHAUSTED`. This is a
**terminal status** — the manifest stops cycling through FAILED → requeue →
skip. If Clair is later upgraded (new hash), the manifest becomes eligible for
reindexing via the hash-mismatch query path.

## Failure Taxonomy

Three distinct exception types in `util/secscan/v4/api.py` represent different
failure modes. Handling them differently is critical for correct retry behavior.

### `APIRequestFailure`

**Cause:** Connection error, timeout, or DNS failure when trying to reach Clair.
The request never reached Clair or Clair never responded.

**Examples:** Network partition, Clair pod restarting, load balancer timeout.

**Behavior:** Transient. The manifest is marked `FAILED` with
`indexer_hash="api_failure"`. **Does NOT increment `retry_count`** in the V2
indexer because the failure says nothing about whether Clair can process this
manifest — it's purely an infrastructure issue. In the V1 indexer, the manifest
is also marked `FAILED` without retry metadata.

**Review concern:** If a PR starts counting `APIRequestFailure` toward the retry
budget, manifests will be permanently skipped due to transient network issues.

### `Non200ResponseException`

**Cause:** Clair received the request and returned a non-2xx HTTP status. The
`response` attribute carries the full HTTP response including `status_code`.

**Examples:** Clair returning 500 for a corrupt layer, 422 for an unprocessable
manifest, 503 during maintenance.

**Behavior:** May be permanent for a specific manifest (e.g., Clair cannot
parse a corrupt layer and will always return 500 for it). **Counts toward
`retry_count`** and is scoped to `last_failed_hash`. After exhausting retries,
the manifest moves to `SCAN_RETRIES_EXHAUSTED`.

**Review concern:** This is the exception that motivates retry limiting. A Clair
500 on a specific manifest is likely to recur on retry (same manifest, same
Clair version). Without retry limits, the worker wastes cycles re-submitting
manifests that Clair cannot process.

### `InvalidContentSent` / `LayerTooLargeException`

**Cause:** The manifest content is malformed (`InvalidContentSent`, maps to
HTTP 400) or a layer exceeds the configured size limit
(`LayerTooLargeException`).

**Behavior:** Permanent. The manifest is marked `MANIFEST_UNSUPPORTED` or
`MANIFEST_LAYER_TOO_LARGE` respectively. These are terminal statuses — no
retries are attempted.

### `IndexReportState.Index_Error`

**Cause:** Clair returned a successful HTTP response, but the `IndexReport`
`state` field is `"IndexError"` rather than `"IndexFinished"`. This means
Clair could not fully index the manifest contents (e.g., unsupported package
manager, corrupt filesystem layer).

**Behavior:** The manifest is marked `FAILED` with retry metadata. Counts
toward the retry budget because the error is manifest-specific and likely to
recur under the same indexer hash.

## Batch Claiming

The two indexer versions use different strategies to find and claim manifests
for scanning.

### V1 Indexer: `yield_random_entries()` + Per-Manifest Claims

The V1 indexer (`V4SecurityScanner`) uses `yield_random_entries()` from
`util/migrate/allocator.py` to iterate over random blocks of manifest IDs.
For each candidate, it:

1. Runs a `batch_preemption_check()` to bulk-filter manifests that were
   recently indexed by another worker or have exhausted their retry budget.
2. Performs an atomic UPDATE to set `index_status = IN_PROGRESS` (only if
   not already `IN_PROGRESS` or stale past `STALE_IN_PROGRESS_HOURS`).
3. Falls back to INSERT (via `ManifestSecurityStatus.create()`) if the
   manifest has no `ManifestSecurityStatus` row yet.

The V1 approach runs four chained queries covering different candidate
categories: not-indexed, failed (eligible for retry), stale in-progress,
and needs-reindexing (hash mismatch).

### V2 Indexer: `FOR UPDATE SKIP LOCKED`

The V2 indexer (`V4SecurityScannerV2`, enabled via
`FEATURE_SECURITY_SCANNER_V2`) uses PostgreSQL row-level locking for
contention-free work distribution:

1. **`_claim_unindexed_manifests(batch_size)`** — finds manifests with no
   `ManifestSecurityStatus` row (LEFT OUTER JOIN where MSS is NULL). Claims
   them by inserting a new row with `IN_PROGRESS` status. Ordered by
   `Manifest.id DESC` to prioritize recently pushed images.

2. **`_find_and_claim_batch(remaining, ...)`** — queries
   `ManifestSecurityStatus` rows matching any of:
   - `PENDING` status
   - `FAILED` status with `last_indexed < reindex_threshold`
   - `IN_PROGRESS` status with `last_indexed < stale_threshold`
   - Hash mismatch (excluding `MANIFEST_UNSUPPORTED` and
     `MANIFEST_LAYER_TOO_LARGE`)

   Uses `FOR UPDATE SKIP LOCKED` to atomically claim rows without blocking
   other workers. Filters out retry-exhausted manifests **after** the
   SELECT (Python-side), then bulk-updates eligible rows to `IN_PROGRESS`.

### Starvation Risk: LIMIT Before vs After Filtering

**This is a common source of bugs in secscan PRs.**

When the `_find_and_claim_batch` query uses `LIMIT batch_size` in the SQL
query (before Python-side filtering), the batch can be filled entirely with
retry-exhausted manifests that are then filtered out. If many exhausted
manifests sort before eligible ones in the `last_indexed ASC` ordering, the
worker claims zero usable manifests per cycle — batch starvation.

The V2 indexer mitigates this by:
- Transitioning exhausted manifests to `SCAN_RETRIES_EXHAUSTED` status,
  which removes them from the query's WHERE clause on subsequent cycles
- Using `batch_size` as the SQL LIMIT (accepting that some rows may be
  filtered), but marking exhausted rows as terminal so they don't recur

The V1 indexer's `batch_preemption_check()` similarly marks exhausted
manifests as `SCAN_RETRIES_EXHAUSTED` to prevent repeated evaluation.

**Review concern:** Any change to batch claiming logic should verify that
exhausted or ineligible manifests are permanently removed from the candidate
pool (via a terminal status), not just skipped in Python. Skipping without
a status transition causes starvation.

## Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `FEATURE_SECURITY_SCANNER` | bool | `False` | Enable/disable security scanning |
| `FEATURE_SECURITY_NOTIFICATIONS` | bool | `False` | Enable vulnerability notifications |
| `FEATURE_SECURITY_SCANNER_V2` | bool | `False` | Enable V2 lock-free indexer |
| `SECURITY_SCANNER_V4_ENDPOINT` | string | — | Clair v4 API endpoint URL |
| `SECURITY_SCANNER_V4_PSK` | string | — | Base64-encoded PSK for JWT signing |
| `SECURITY_SCANNER_V4_BATCH_SIZE` | int | `0` | Manifests per indexing cycle (V1) |
| `SECURITY_SCANNER_V2_BATCH_SIZE` | int | `50` | Manifests per indexing cycle (V2) |
| `SECURITY_SCANNER_V4_REINDEX_THRESHOLD` | int | `86400` | Seconds before a failed manifest is retried |
| `SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE` | string | — | Max layer size (e.g., `"8G"`) |
| `SECURITY_SCANNER_INDEXING_INTERVAL` | int | `30` | Seconds between indexing cycles |
| `SECURITY_SCANNER_V2_INDEXING_INTERVAL` | int | `30` | Seconds between V2 indexing cycles |
| `SECURITY_SCANNER_MAX_SCAN_RETRIES` | int | `5` | Max retries per indexer hash before exhaustion |
| `SECURITY_SCANNER_V4_LOCK` | bool | `False` | Use global lock for V1 full-range indexing |
| `FEATURE_SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX` | bool | `False` | Send notifications for new scan results |
| `NOTIFICATION_MIN_SEVERITY_ON_NEW_INDEX` | string | `"High"` | Minimum severity for new-index notifications |

## Key Source Files

| File | Purpose |
|------|---------|
| `data/database.py` | `ManifestSecurityStatus`, `IndexStatus`, `IndexerVersion` definitions |
| `data/secscan_model/__init__.py` | `SecurityScannerModelProxy` — delegates to V1/V2 |
| `data/secscan_model/secscan_v4_model.py` | V1 indexer: `V4SecurityScanner`, batch iteration, `features_for()` |
| `data/secscan_model/secscan_v4_model_v2.py` | V2 indexer: `V4SecurityScannerV2`, `FOR UPDATE SKIP LOCKED` |
| `data/secscan_model/interface.py` | Abstract interfaces for read and indexer |
| `data/secscan_model/datatypes.py` | `SecurityInformation`, `Vulnerability`, `ScanLookupStatus` |
| `util/secscan/v4/api.py` | `ClairSecurityScannerAPI`, exception types, JWT signing |
| `util/secscan/blob.py` | `BlobURLRetriever` — generates signed blob download URLs for Clair |
| `util/secscan/validator.py` | `V4SecurityConfigValidator` |
| `workers/securityworker/securityworker.py` | `SecurityWorker` — schedules indexing operations |
| `workers/securityscanningnotificationworker.py` | Processes Clair vulnerability notifications |

## Common Review Pitfalls

Use this checklist when reviewing PRs that touch `data/secscan_model/` or
`util/secscan/`:

### Failure Type Handling

- [ ] Does the PR distinguish between `APIRequestFailure` (transient/infra)
  and `Non200ResponseException` (Clair processed the request)?
- [ ] Are transient failures (`APIRequestFailure`) excluded from the retry
  count? Counting them penalizes manifests for infrastructure issues.
- [ ] Is `InvalidContentSent` handled as a terminal status
  (`MANIFEST_UNSUPPORTED`) rather than a retriable failure?

### Hash Scoping

- [ ] Is the retry count scoped to `last_failed_hash`? When the indexer hash
  changes, `retry_count` should reset to allow fresh attempts.
- [ ] Does `SCAN_RETRIES_EXHAUSTED` status allow re-evaluation when the
  indexer hash changes? The hash-mismatch reindexing query should pick
  these up (verify the WHERE clause doesn't exclude them).

### Batch Window Impact

- [ ] If a SQL `LIMIT` is applied before Python-side filtering, can the batch
  fill with ineligible manifests (starvation)?
- [ ] Are ineligible manifests transitioned to a terminal status so they stop
  appearing in candidate queries?
- [ ] Is the `should_skip` / preemption check performed **before** expensive
  operations (manifest parsing, layer-placement queries)?

### Config Schema Registration

- [ ] If a new config key is added, is it registered in
  `util/config/schema.py` with type, description, and example?
- [ ] Does the code provide a sensible default if the config key is missing?

### Terminal vs Retriable Status

- [ ] Does every failure path set a clear terminal or retriable status?
- [ ] Manifests in terminal statuses (`MANIFEST_UNSUPPORTED`,
  `MANIFEST_LAYER_TOO_LARGE`, `SCAN_RETRIES_EXHAUSTED`) should not cycle
  back into the candidate pool unless the indexer hash changes.
- [ ] Manifests in `FAILED` should be retried (subject to retry budget), not
  left indefinitely cycling through FAILED → requeue → skip.
