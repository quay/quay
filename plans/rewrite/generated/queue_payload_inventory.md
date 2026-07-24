# Queue Payload Inventory

| Queue var | Producer keys | Consumer keys | Producer files | Consumer files |
|---|---|---|---|---|
| `chunk_cleanup_queue` | `` | `location, path` | `storage/swift.py` | `workers/chunkcleanupworker.py` |
| `image_replication_queue` | `` | `namespace_user_id, storage_id` | `util/registry/replication.py` | `workers/storagereplication.py` |
| `proxy_cache_blob_queue` | `digest, namespace, repo_id, username` | `digest, namespace, repo_id, username` | `data/registry_model/registry_proxy_model.py` | `workers/proxycacheblobworker.py` |
| `dockerfile_build_queue` | `` | `created_at, execution_id, executor_name, job_queue_item, last_heartbeat, max_expiration` | `endpoints/building.py` | `buildman/manager/ephemeral.py; buildman/jobutil/buildjob.py` |
| `notification_queue` | `` | `event_data, notification_uuid` | `endpoints/api/repositorynotification_models_pre_oci.py; notifications/__init__.py` | `workers/notificationworker/notificationworker.py` |
| `secscan_notification_queue` | `notification_id` | `current_page_index, notification_id` | `endpoints/secscan.py` | `workers/securityscanningnotificationworker.py` |
| `export_action_logs_queue` | `callback_email, callback_url, end_time, export_id, namespace_id, namespace_name, repository_id, repository_name, start_time` | `callback_email, callback_url, end_time, export_id, namespace_id, namespace_name, repository_id, repository_name, start_time` | `data/logs_model/shared.py` | `workers/exportactionlogsworker.py` |
| `repository_gc_queue` | `marker_id, original_name` | `marker_id` | `data/model/repository.py` | `workers/repositorygcworker.py` |
| `namespace_gc_queue` | `marker_id, original_username` | `marker_id` | `data/model/user.py` | `workers/namespacegcworker.py` |
