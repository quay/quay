# Queue Inventory

| Queue var | Config key | Default queue name | `has_namespace` | Producer files (`.put`/`.batch_insert`) | Consumer files |
|---|---|---|---|---|---|
| `chunk_cleanup_queue` | `CHUNK_CLEANUP_QUEUE_NAME` | `chunk_cleanup` | `False` | `storage/swift.py` | `workers/chunkcleanupworker.py` |
| `image_replication_queue` | `REPLICATION_QUEUE_NAME` | `imagestoragereplication` | `False` | `util/registry/replication.py` | `workers/storagereplication.py` |
| `proxy_cache_blob_queue` | `PROXY_CACHE_BLOB_QUEUE_NAME` | `proxycacheblob` | `True` | `data/registry_model/registry_proxy_model.py` | `workers/proxycacheblobworker.py` |
| `dockerfile_build_queue` | `DOCKERFILE_BUILD_QUEUE_NAME` | `dockerfilebuild` | `True` | `endpoints/building.py; test/test_api_usage.py` | `buildman/builder.py` |
| `notification_queue` | `NOTIFICATION_QUEUE_NAME` | `notification` | `True` | `endpoints/api/repositorynotification_models_pre_oci.py; endpoints/secscan.py; notifications/__init__.py; test/test_api_usage.py` | `workers/notificationworker/notificationworker.py; workers/securityscanningnotificationworker.py` |
| `secscan_notification_queue` | `SECSCAN_V4_NOTIFICATION_QUEUE_NAME` | `secscanv4` | `False` | `endpoints/secscan.py` | `workers/securityscanningnotificationworker.py` |
| `export_action_logs_queue` | `EXPORT_ACTION_LOGS_QUEUE_NAME` | `exportactionlogs` | `True` | `data/logs_model/shared.py` | `workers/exportactionlogsworker.py` |
| `repository_gc_queue` | `REPOSITORY_GC_QUEUE_NAME` | `repositorygc` | `True` | `data/model/repository.py` | `workers/repositorygcworker.py` |
| `namespace_gc_queue` | `NAMESPACE_GC_QUEUE_NAME` | `namespacegc` | `False` | `data/model/user.py` | `workers/namespacegcworker.py` |
