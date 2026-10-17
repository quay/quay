# Queue Contracts and Semantics

Status: Expanded
Last updated: 2026-02-08

## 1. Purpose

Define queue behavior as a hard migration contract.

## 2. Authoritative source files

- `data/queue.py`
- `data/database.py` (`QueueItem`)
- `app.py` (queue instances)
- queue producer/consumer files referenced below

Generated inventories:
- `plans/rewrite/generated/queue_inventory.md`
- `plans/rewrite/generated/queue_payload_inventory.md`
- `plans/rewrite/generated/queue_worker_contract_tests.csv`
- `plans/rewrite/generated/route_worker_dependency_matrix.md`

Dependency sequencing companion:
- `plans/rewrite/queue_cutover_dependencies.md`

## 3. Core queue item contract

`QueueItem` contract fields:
- `queue_name`
- `body`
- `available_after`
- `available`
- `processing_expires`
- `retries_remaining`
- `state_id`

## 4. Behavior contract (must preserve)

From `WorkQueue` behavior:
- At-least-once delivery.
- Claim-by-update via `id + state_id` compare-and-swap.
- Claim decrements `retries_remaining`.
- `complete` removes item.
- `incomplete` supports retry restoration and deferred retry (`retry_after`).
- Lease extension via `extend_processing`.
- Claim mode:
  - default pseudo-random from first available set.
  - ordered mode via `ordering_required=True`.

Build manager requires ordered mode.

## 5. Queue instances (runtime)

| Queue var | Default queue name | `has_namespace` | Producer(s) | Consumer(s) | Payload keys (contract) |
|---|---|---|---|---|---|
| `chunk_cleanup_queue` | `chunk_cleanup` | `False` | `storage/swift.py` | `workers/chunkcleanupworker.py` | `location`, `path` (producer may include `uuid`) |
| `image_replication_queue` | `imagestoragereplication` | `False` | `util/registry/replication.py` | `workers/storagereplication.py` | `namespace_user_id`, `storage_id` |
| `proxy_cache_blob_queue` | `proxycacheblob` | `True` | `data/registry_model/registry_proxy_model.py` | `workers/proxycacheblobworker.py` | `digest`, `repo_id`, `username`, `namespace` |
| `dockerfile_build_queue` | `dockerfilebuild` | `True` | `endpoints/building.py` | `buildman/jobutil/buildjob.py`, `buildman/manager/ephemeral.py` | `build_uuid`, `pull_credentials` |
| `notification_queue` | `notification` | `True` | `notifications/__init__.py`, `endpoints/api/repositorynotification_models_pre_oci.py` | `workers/notificationworker/notificationworker.py` | `notification_uuid`, `event_data`, `performer_data` |
| `secscan_notification_queue` | `secscanv4` | `False` | `endpoints/secscan.py` | `workers/securityscanningnotificationworker.py` | `notification_id` (+ worker-maintained `current_page_index`) |
| `export_action_logs_queue` | `exportactionlogs` | `True` | `data/logs_model/shared.py` | `workers/exportactionlogsworker.py` | `export_id`, `repository_id`, `namespace_id`, `namespace_name`, `repository_name`, `start_time`, `end_time`, `callback_url`, `callback_email` |
| `repository_gc_queue` | `repositorygc` | `True` | `data/model/repository.py` | `workers/repositorygcworker.py` | `marker_id`, `original_name` |
| `namespace_gc_queue` | `namespacegc` | `False` | `data/model/user.py` | `workers/namespacegcworker.py` | `marker_id`, `original_username` |

## 6. Cross-cutting migration risks

1. `all_queues` in `app.py` is not a complete list of runtime queues. Specifically, `proxy_cache_blob_queue`, `secscan_notification_queue`, and `export_action_logs_queue` are instantiated at startup but absent from the `all_queues` list. This means namespace-deletion cleanup (which iterates `all_queues`) does not purge items from these three queues. Go must either preserve this selective cleanup behavior or deliberately change it with a compatibility analysis and approved decision. Contract tests must assert expected behavior during namespace deletion for all 9 queues.
2. Queue payload JSON shape is loosely typed in Python; Go must validate payloads while remaining backward compatible during mixed producer/consumer operation.
3. Build queue lifecycle embeds queue item bodies into orchestrator state and relies on specific requeue paths; this must be contract-tested.
4. Some producer payload keys in static inventory are intentionally incomplete (producer builds nested payloads or uses helper constructors); canonical payload fixtures must be source-verified during test authoring.
5. Optional payload fields (e.g., `chunk_cleanup_queue` producer may include `uuid`) must be tested for both presence and absence in contract tests, including mixed-producer scenarios (Python with optional field, Go without, and vice versa).

## 7. Go migration requirement

A different internal queue engine is allowed only if observable semantics remain equivalent:
- claim/fail/complete behavior
- retries and retry-restoration
- lease expiration and extension
- ordered-queue behavior for build manager
- operational metrics parity
