# Worker Inventory (Source Parse)

## Supervisor Programs

| Program | Default autostart | Python module (if any) | Command snippet |
|---|---|---|---|
| `blobuploadcleanupworker` | `true` | `workers.blobuploadcleanupworker.blobuploadcleanupworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/blobuploadcleanupworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.blobuploadcleanupworker.blobuploadcleanupwo` |
| `buildlogsarchiver` | `true` | `workers.buildlogsarchiver.buildlogsarchiver` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/buildlogsarchiver.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.buildlogsarchiver.buildlogsarchiver:create_gunico` |
| `builder` | `true` | `buildman.builder` | `python -m buildman.builder` |
| `chunkcleanupworker` | `true` | `workers.chunkcleanupworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/chunkcleanupworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.chunkcleanupworker:create_gunicorn_worker()' {% ` |
| `expiredappspecifictokenworker` | `true` | `workers.expiredappspecifictokenworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/expiredappspecifictokenworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.expiredappspecifictokenworker:create_` |
| `exportactionlogsworker` | `true` | `workers.exportactionlogsworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/exportactionlogsworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.exportactionlogsworker:create_gunicorn_worke` |
| `gcworker` | `true` | `workers.gc.gcworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/gcworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.gc.gcworker:create_gunicorn_worker()' {% else -%}   python` |
| `globalpromstats` | `true` | `workers.globalpromstats.globalpromstats` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/globalpromstats.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.globalpromstats.globalpromstats:create_gunicorn_wor` |
| `logrotateworker` | `true` | `workers.logrotateworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/logrotateworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.logrotateworker:create_gunicorn_worker()' {% else -` |
| `repositorygcworker` | `true` | `workers.repositorygcworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/repositorygcworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.repositorygcworker:create_gunicorn_worker()' {% ` |
| `reconciliationworker` | `true` | `workers.reconciliationworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/reconciliationworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.reconciliationworker:create_gunicorn_worker()'` |
| `namespacegcworker` | `true` | `workers.namespacegcworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/namespacegcworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.namespacegcworker:create_gunicorn_worker()' {% el` |
| `notificationworker` | `true` | `workers.notificationworker.notificationworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/notificationworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.notificationworker.notificationworker:create_gun` |
| `queuecleanupworker` | `true` | `workers.queuecleanupworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/queuecleanupworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.queuecleanupworker:create_gunicorn_worker()' {% ` |
| `repositoryactioncounter` | `true` | `workers.repositoryactioncounter` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/repositoryactioncounter.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.repositoryactioncounter:create_gunicorn_wor` |
| `securityworker` | `true` | `workers.securityworker.securityworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/securityworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.securityworker.securityworker:create_gunicorn_worker` |
| `storagereplication` | `true` | `workers.storagereplication` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/storagereplication.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.storagereplication:create_gunicorn_worker()' {% ` |
| `teamsyncworker` | `true` | `workers.teamsyncworker.teamsyncworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/teamsyncworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.teamsyncworker.teamsyncworker:create_gunicorn_worker` |
| `dnsmasq` | `true` | `` | `/usr/sbin/dnsmasq --no-daemon --user=root --listen-address=127.0.0.1 --port=8053` |
| `gunicorn-registry` | `true` | `` | `nice -n 10 gunicorn -c %(ENV_QUAYCONF)s/gunicorn_registry.py registry:application` |
| `gunicorn-secscan` | `true` | `` | `{% if hotreload -%}   gunicorn --timeout=600 -c %(ENV_QUAYCONF)s/gunicorn_secscan.py secscan:application {% else -%}   gunicorn -c %(ENV_QUAYCONF)s/gunicorn_secscan.py secscan:appl` |
| `gunicorn-web` | `true` | `` | `{% if hotreload -%}   gunicorn --timeout=600 -c %(ENV_QUAYCONF)s/gunicorn_web.py web:application {% else -%}   gunicorn -c %(ENV_QUAYCONF)s/gunicorn_web.py web:application {% endif` |
| `memcache` | `true` | `` | `memcached -u memcached -m 64 -l 127.0.0.1 -p 18080` |
| `nginx` | `true` | `` | `nginx -c %(ENV_QUAYCONF)s/nginx/nginx.conf` |
| `pushgateway` | `true` | `` | `/usr/local/bin/pushgateway` |
| `servicekey` | `true` | `workers.servicekeyworker.servicekeyworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/servicekey.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.servicekeyworker.servicekeyworker:create_gunicorn_worker` |
| `manifestbackfillworker` | `true` | `workers.manifestbackfillworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/manifestbackfillworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.manifestbackfillworker:create_gunicorn_worke` |
| `manifestsubjectbackfillworker` | `true` | `workers.manifestsubjectbackfillworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/manifestsubjectbackfillworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.manifestsubjectbackfillworker:create_` |
| `securityscanningnotificationworker` | `true` | `workers.securityscanningnotificationworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/securityscanningnotificationworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.securityscanningnotificationwork` |
| `repomirrorworker` | `false` | `workers.repomirrorworker.repomirrorworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/repomirrorworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.repomirrorworker.repomirrorworker:create_gunicorn_` |
| `quotatotalworker` | `true` | `workers.quotatotalworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/quotatotalworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.quotatotalworker:create_gunicorn_worker()' {% else` |
| `quotaregistrysizeworker` | `true` | `workers.quotaregistrysizeworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/quotaregistrysizeworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.quotaregistrysizeworker:create_gunicorn_wor` |
| `autopruneworker` | `true` | `workers.autopruneworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/autopruneworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.autopruneworker:create_gunicorn_worker()' {% else -` |
| `proxycacheblobworker` | `true` | `workers.proxycacheblobworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/proxycacheblobworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.proxycacheblobworker:create_gunicorn_worker()'` |
| `pullstatsredisflushworker` | `true` | `workers.pullstatsredisflushworker` | `{% if hotreload -%}   gunicorn --timeout=600 -b 'unix:/tmp/pullstatsredisflushworker.sock' -c %(ENV_QUAYCONF)s/gunicorn_worker.py 'workers.pullstatsredisflushworker:create_gunicorn` |

## Worker Modules

| File | Classes | Base types | Queue refs | Gunicorn feature flag | Guards |
|---|---|---|---|---|---|
| `workers/__init__.py` | `` | `` | `` | `` | `` |
| `workers/autopruneworker.py` | `AutoPruneWorker` | `Worker` | `` | `features.AUTO_PRUNE` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.AUTO_PRUNE` |
| `workers/blobuploadcleanupworker/__init__.py` | `` | `` | `` | `` | `` |
| `workers/blobuploadcleanupworker/blobuploadcleanupworker.py` | `BlobUploadCleanupWorker` | `Worker` | `` | `True` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/blobuploadcleanupworker/models_interface.py` | `` | `` | `` | `` | `` |
| `workers/blobuploadcleanupworker/models_pre_oci.py` | `` | `` | `` | `` | `` |
| `workers/buildlogsarchiver/__init__.py` | `` | `` | `` | `` | `` |
| `workers/buildlogsarchiver/buildlogsarchiver.py` | `ArchiveBuildLogsWorker` | `Worker` | `` | `True` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/buildlogsarchiver/models_interface.py` | `` | `` | `` | `` | `` |
| `workers/buildlogsarchiver/models_pre_oci.py` | `` | `` | `` | `` | `` |
| `workers/chunkcleanupworker.py` | `ChunkCleanupWorker` | `QueueWorker` | `chunk_cleanup_queue` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/expiredappspecifictokenworker.py` | `ExpiredAppSpecificTokenWorker` | `Worker` | `` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.APP_SPECIFIC_TOKENS` |
| `workers/exportactionlogsworker.py` | `ExportActionLogsWorker` | `QueueWorker` | `export_action_logs_queue` | `features.LOG_EXPORT` | `not features.LOG_EXPORT` |
| `workers/gc/__init__.py` | `` | `` | `` | `` | `` |
| `workers/gc/gcworker.py` | `GarbageCollectionWorker` | `Worker` | `` | `features.GARBAGE_COLLECTION` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); app.config.get("DISABLE_PUSHES", False); features.IMAGE_EXPIRY_TRIGGER; not features.GARBAGE_COLLECTION` |
| `workers/globalpromstats/__init__.py` | `` | `` | `` | `` | `` |
| `workers/globalpromstats/globalpromstats.py` | `GlobalPrometheusStatsWorker` | `Worker` | `` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/gunicorn_worker.py` | `` | `` | `` | `` | `` |
| `workers/logrotateworker.py` | `LogRotateWorker` | `Worker` | `` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.ACTION_LOG_ROTATION or None in [SAVE_PATH, SAVE_LOCATION]` |
| `workers/manifestbackfillworker.py` | `ManifestBackfillWorker` | `Worker` | `` | `features.MANIFEST_SIZE_BACKFILL` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.MANIFEST_SIZE_BACKFILL` |
| `workers/manifestsubjectbackfillworker.py` | `ManifestSubjectBackfillWorker` | `Worker` | `` | `features.MANIFEST_SUBJECT_BACKFILL` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.MANIFEST_SUBJECT_BACKFILL` |
| `workers/namespacegcworker.py` | `NamespaceGCWorker` | `QueueWorker` | `namespace_gc_queue` | `features.NAMESPACE_GARBAGE_COLLECTION` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); app.config.get("DISABLE_PUSHES", False); not features.NAMESPACE_GARBAGE_COLLECTION` |
| `workers/notificationworker/__init__.py` | `` | `` | `` | `` | `` |
| `workers/notificationworker/models_interface.py` | `` | `` | `` | `` | `` |
| `workers/notificationworker/models_pre_oci.py` | `` | `` | `` | `` | `` |
| `workers/notificationworker/notificationworker.py` | `NotificationWorker` | `QueueWorker` | `notification_queue` | `True` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/proxycacheblobworker.py` | `ProxyCacheBlobWorker` | `QueueWorker` | `proxy_cache_blob_queue` | `features.PROXY_CACHE` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.PROXY_CACHE or not features.PROXY_CACHE_BLOB_DOWNLOAD` |
| `workers/pullstatsredisflushworker.py` | `RedisFlushWorker` | `Worker` | `` | `features.IMAGE_PULL_STATS` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.IMAGE_PULL_STATS` |
| `workers/queuecleanupworker.py` | `QueueCleanupWorker` | `Worker` | `` | `True` | `app.config.get("ACCOUNT_RECOVERY_MODE", False)` |
| `workers/queueworker.py` | `QueueWorker` | `Worker` | `` | `` | `` |
| `workers/quotaregistrysizeworker.py` | `QuotaRegistrySizeWorker` | `Worker` | `` | `features.QUOTA_MANAGEMENT` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not any( [ any( [ features.SUPER_USERS, len(app.config.get("SUPER_USERS", [])) == 0, ] ), app.config.get("LDAP_SUPERUSER_FILTER", False), ] ); not features.QUOTA_MANAGEMENT` |
| `workers/quotatotalworker.py` | `QuotaTotalWorker` | `Worker` | `` | `features.QUOTA_MANAGEMENT` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.QUOTA_MANAGEMENT` |
| `workers/reconciliationworker.py` | `ReconciliationWorker` | `Worker` | `` | `features.ENTITLEMENT_RECONCILIATION` | `not features.ENTITLEMENT_RECONCILIATION` |
| `workers/repomirrorworker/__init__.py` | `` | `` | `` | `` | `not features.ORG_MIRROR; not features.REPO_MIRROR` |
| `workers/repomirrorworker/manifest_utils.py` | `` | `` | `` | `` | `` |
| `workers/repomirrorworker/models_interface.py` | `` | `` | `` | `` | `` |
| `workers/repomirrorworker/org_mirror_model.py` | `` | `` | `` | `` | `` |
| `workers/repomirrorworker/repo_mirror_model.py` | `` | `` | `` | `` | `` |
| `workers/repomirrorworker/repomirrorworker.py` | `RepoMirrorWorker` | `Worker` | `` | `features.REPO_MIRROR` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.REPO_MIRROR` |
| `workers/repositoryactioncounter.py` | `RepositoryActionCountWorker` | `Worker` | `` | `features.REPOSITORY_ACTION_COUNTER` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); features.CLEAR_EXPIRED_RAC_ENTRIES; not features.REPOSITORY_ACTION_COUNTER` |
| `workers/repositorygcworker.py` | `RepositoryGCWorker` | `QueueWorker` | `repository_gc_queue` | `features.REPOSITORY_GARBAGE_COLLECTION` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); app.config.get("DISABLE_PUSHES", False); not features.REPOSITORY_GARBAGE_COLLECTION` |
| `workers/securityscanningnotificationworker.py` | `SecurityScanningNotificationWorker` | `QueueWorker` | `secscan_notification_queue` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.SECURITY_NOTIFICATIONS; not features.SECURITY_SCANNER` |
| `workers/securityworker/__init__.py` | `` | `` | `` | `` | `` |
| `workers/securityworker/securityworker.py` | `SecurityWorker` | `Worker` | `` | `features.SECURITY_SCANNER` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.SECURITY_SCANNER` |
| `workers/servicekeyworker/__init__.py` | `` | `` | `` | `` | `` |
| `workers/servicekeyworker/models_interface.py` | `` | `` | `` | `` | `` |
| `workers/servicekeyworker/models_pre_oci.py` | `` | `` | `` | `` | `` |
| `workers/servicekeyworker/servicekeyworker.py` | `ServiceKeyWorker` | `Worker` | `` | `True` | `` |
| `workers/storagereplication.py` | `StorageReplicationWorker` | `QueueWorker` | `image_replication_queue` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); features.STORAGE_REPLICATION; not features.STORAGE_REPLICATION or has_local_storage` |
| `workers/teamsyncworker/__init__.py` | `` | `` | `` | `` | `` |
| `workers/teamsyncworker/teamsyncworker.py` | `TeamSynchronizationWorker` | `Worker` | `` | `feature_flag` | `app.config.get("ACCOUNT_RECOVERY_MODE", False); not features.TEAM_SYNCING or not authentication.federated_service` |
| `workers/worker.py` | `` | `` | `` | `` | `` |
