import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from peewee import IntegrityError, fn

import features
from data.cache import cache_key
from data.database import (
    IndexerVersion,
    IndexStatus,
    Manifest,
    ManifestSecurityStatus,
    db_for_update,
    db_transaction,
    get_epoch_timestamp_ms,
)
from data.registry_model import registry_model
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.secscan_model.datatypes import (
    Layer,
    PaginatedNotificationResult,
    PaginatedNotificationStatus,
    ScanLookupStatus,
    SecurityInformation,
    SecurityInformationLookupResult,
    UpdatedVulnerability,
    Vulnerability,
)
from data.secscan_model.interface import (
    InvalidConfigurationException,
    SecurityScannerInterface,
)
from data.secscan_model.secscan_v4_model import (
    IndexReportState,
    _has_container_layers,
    features_for,
    maybe_urlencoded,
)
from image.docker.schema1 import DOCKER_SCHEMA1_CONTENT_TYPES
from util.metrics.prometheus import (
    secscan_index_errors,
    secscan_manifests_claimed,
    secscan_manifests_skipped,
    secscan_result_duration,
)
from util.secscan import PRIORITY_LEVELS
from util.secscan.blob import BlobURLRetriever
from util.secscan.v4.api import (
    APIRequestFailure,
    ClairSecurityScannerAPI,
    InvalidContentSent,
    LayerTooLargeException,
)
from util.secscan.validator import V4SecurityConfigValidator

logger = logging.getLogger(__name__)

DEFAULT_SECURITY_SCANNER_V4_REINDEX_THRESHOLD = 86400  # 1 day
DEFAULT_IN_PROGRESS_TIMEOUT = 1800  # 30 minutes
DEFAULT_CONCURRENCY = 4
TAG_LIMIT = 100
SKIP_LOCKED = True  # Toggleable for MySQL 5.7 tests


class V4SecurityScanner2(SecurityScannerInterface):
    """
    Parallel-safe implementation of the security scanner interface for Clair V4.
    Uses SELECT FOR UPDATE SKIP LOCKED for distributed coordination and concurrent Clair API calls.
    """

    def __init__(self, app, instance_keys, storage):
        self.app = app
        self.storage = storage

        if app.config.get("SECURITY_SCANNER_V4_ENDPOINT", None) is None:
            raise InvalidConfigurationException(
                "Missing SECURITY_SCANNER_V4_ENDPOINT configuration"
            )

        validator = V4SecurityConfigValidator(
            app.config.get("FEATURE_SECURITY_SCANNER", False),
            app.config.get("SECURITY_SCANNER_V4_ENDPOINT", None),
        )

        if not validator.valid():
            msg = "Failed to validate security scanner V4 configuration"
            logger.warning(msg)
            raise InvalidConfigurationException(msg)

        self._secscan_api = ClairSecurityScannerAPI(
            endpoint=app.config.get("SECURITY_SCANNER_V4_ENDPOINT"),
            client=app.config.get("HTTPCLIENT"),
            blob_url_retriever=BlobURLRetriever(storage, instance_keys, app),
            jwt_psk=app.config.get("SECURITY_SCANNER_V4_PSK", None),
            max_layer_size=app.config.get("SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE", None),
        )

    def _not_indexed_query(self):
        """Manifests with no ManifestSecurityStatus row (never scanned)."""
        return (
            Manifest.select()
            .where(
                ~fn.EXISTS(
                    ManifestSecurityStatus.select().where(
                        ManifestSecurityStatus.manifest == Manifest.id
                    )
                )
            )
            .order_by(Manifest.id)
        )

    def _stale_in_progress_query(self, stale_threshold):
        """Manifests stuck in IN_PROGRESS (crash recovery)."""
        return (
            Manifest.select()
            .join(ManifestSecurityStatus)
            .where(
                ManifestSecurityStatus.index_status == IndexStatus.IN_PROGRESS,
                ManifestSecurityStatus.last_indexed < stale_threshold,
            )
            .order_by(Manifest.id)
        )

    def _failed_query(self, reindex_threshold):
        """Failed manifests past retry threshold."""
        return (
            Manifest.select()
            .join(ManifestSecurityStatus)
            .where(
                ManifestSecurityStatus.index_status == IndexStatus.FAILED,
                ManifestSecurityStatus.last_indexed < reindex_threshold,
            )
            .order_by(Manifest.id)
        )

    def _needs_reindex_query(self, indexer_hash, reindex_threshold):
        """Manifests with outdated indexer hash (Clair DB updated)."""
        return (
            Manifest.select()
            .join(ManifestSecurityStatus)
            .where(
                ManifestSecurityStatus.index_status != IndexStatus.MANIFEST_UNSUPPORTED,
                ManifestSecurityStatus.index_status != IndexStatus.MANIFEST_LAYER_TOO_LARGE,
                ManifestSecurityStatus.index_status != IndexStatus.IN_PROGRESS,
                ManifestSecurityStatus.indexer_hash != indexer_hash,
                ManifestSecurityStatus.last_indexed < reindex_threshold,
            )
            .order_by(Manifest.id)
        )

    def _mark_batch_in_progress(self, candidates):
        """Mark claimed manifests as IN_PROGRESS via upsert."""
        now = datetime.utcnow()
        candidate_ids = [c.id for c in candidates]

        # Update existing ManifestSecurityStatus rows
        ManifestSecurityStatus.update(
            index_status=IndexStatus.IN_PROGRESS,
            last_indexed=now,
        ).where(ManifestSecurityStatus.manifest.in_(candidate_ids)).execute()

        # Find which candidates don't have a status row yet
        existing_ids = set(
            row.manifest_id
            for row in ManifestSecurityStatus.select(ManifestSecurityStatus.manifest).where(
                ManifestSecurityStatus.manifest.in_(candidate_ids)
            )
        )

        # Create rows for new manifests
        new_candidates = [c for c in candidates if c.id not in existing_ids]
        if new_candidates:
            ManifestSecurityStatus.insert_many(
                [
                    {
                        "manifest": c.id,
                        "repository": c.repository_id,
                        "index_status": IndexStatus.IN_PROGRESS,
                        "indexer_hash": "",
                        "indexer_version": IndexerVersion.V4,
                        "metadata_json": {},
                        "error_json": {},
                    }
                    for c in new_candidates
                ]
            ).execute()

    def _claim_manifests(self, query_fn, batch_size):
        """
        Atomically claim a batch of manifests using SELECT FOR UPDATE SKIP LOCKED.
        Returns list of claimed Manifest rows.
        """
        with db_transaction():
            query = query_fn().limit(batch_size)
            candidates = list(db_for_update(query, skip_locked=SKIP_LOCKED))
            if not candidates:
                return []
            self._mark_batch_in_progress(candidates)
            logger.info(
                "Claimed %d manifest(s) for indexing (IDs: %d to %d)",
                len(candidates),
                candidates[0].id,
                candidates[-1].id,
            )
            return candidates

    def _upsert_status(self, manifest_id, repo_id, index_status, indexer_hash, error_json):
        """Upsert ManifestSecurityStatus (update-first, create-on-miss)."""
        now = datetime.utcnow()

        rows_updated = (
            ManifestSecurityStatus.update(
                index_status=index_status,
                indexer_hash=indexer_hash,
                indexer_version=IndexerVersion.V4,
                metadata_json={},
                error_json=error_json,
                last_indexed=now,
            )
            .where(ManifestSecurityStatus.manifest == manifest_id)
            .execute()
        )

        if rows_updated == 0:
            # No existing row, create one
            try:
                ManifestSecurityStatus.create(
                    manifest=manifest_id,
                    repository=repo_id,
                    index_status=index_status,
                    indexer_hash=indexer_hash,
                    indexer_version=IndexerVersion.V4,
                    metadata_json={},
                    error_json=error_json,
                )
            except IntegrityError:
                # Race condition: another pod created it
                ManifestSecurityStatus.update(
                    index_status=index_status,
                    indexer_hash=indexer_hash,
                    indexer_version=IndexerVersion.V4,
                    metadata_json={},
                    error_json=error_json,
                    last_indexed=now,
                ).where(ManifestSecurityStatus.manifest == manifest_id).execute()

    def _call_clair_index(self, manifest, layers):
        """Thread-safe wrapper around Clair index API call."""
        return self._secscan_api.index(manifest, layers)

    def _handle_notification(self, manifest):
        """Handle SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX notifications."""
        if not features.SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX:
            return

        try:
            vulnerability_report = self._secscan_api.vulnerability_report(manifest.digest)
        except APIRequestFailure:
            return

        if vulnerability_report is None:
            return

        found_vulnerabilities = vulnerability_report.get("vulnerabilities")
        if found_vulnerabilities is None:
            return

        level = self.app.config.get("NOTIFICATION_MIN_SEVERITY_ON_NEW_INDEX") or "High"
        lowest_severity = PRIORITY_LEVELS[level]

        import notifications

        logger.debug("Attempting to create notifications for manifest %s", manifest)

        for key in list(found_vulnerabilities.keys()):
            vuln = found_vulnerabilities[key]
            found_severity = PRIORITY_LEVELS.get(
                vuln["normalized_severity"], PRIORITY_LEVELS["Unknown"]
            )

            if found_severity["score"] >= lowest_severity["score"]:
                tag_names = list(registry_model.tag_names_for_manifest(manifest, TAG_LIMIT))
                event_data = {
                    "tags": tag_names if tag_names else [manifest.digest],
                    "vulnerable_index_report_created": "true",
                    "vulnerability": {
                        "id": vuln["id"],
                        "description": vuln["description"],
                        "link": vuln["links"],
                        "priority": vuln["severity"],
                        "has_fix": bool(vuln["fixed_in_version"]),
                    },
                }

                logger.debug("Created notification with event_data: %s", event_data)
                notifications.spawn_notification(
                    manifest.repository, "vulnerability_found", event_data
                )

    def _index_batch_concurrent(self, claimed_manifests, reindex_threshold):
        """
        Process a batch of claimed manifests with concurrent Clair API calls.
        Phase 1: Filter unsupported manifests (serial)
        Phase 2: Call Clair API concurrently (parallel)
        Phase 3: Write results to DB (serial)
        """
        logger.info("Starting indexing batch of %d manifest(s)", len(claimed_manifests))
        concurrency = self.app.config.get("SECURITY_SCANNER_V4_CONCURRENCY", DEFAULT_CONCURRENCY)

        # Phase 1: Pre-process manifests (serial, local operations)
        indexable = []
        for candidate in claimed_manifests:
            manifest = ManifestDataType.for_manifest(candidate, None)

            if manifest.is_manifest_list:
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.MANIFEST_UNSUPPORTED,
                    "none",
                    {},
                )
                secscan_manifests_skipped.labels(reason="manifest_list").inc()
                continue

            layers = registry_model.list_manifest_layers(manifest, self.storage, True)

            if layers is None or len(layers) == 0:
                logger.warning(
                    "Cannot index %s/%s@%s due to manifest being invalid (manifest has no layers)",
                    candidate.repository.namespace_user,
                    candidate.repository.name,
                    manifest.digest,
                )
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.MANIFEST_UNSUPPORTED,
                    "none",
                    {},
                )
                secscan_manifests_skipped.labels(reason="no_layers").inc()
                continue

            # Check for container layers (skip artifacts)
            if manifest.media_type not in DOCKER_SCHEMA1_CONTENT_TYPES:
                if not _has_container_layers(layers):
                    logger.info(
                        "Cannot index %s/%s@%s due to manifest being invalid (manifest appears to be an artifact image)",
                        candidate.repository.namespace_user,
                        candidate.repository.name,
                        manifest.digest,
                    )
                    self._upsert_status(
                        candidate.id,
                        candidate.repository_id,
                        IndexStatus.MANIFEST_UNSUPPORTED,
                        "none",
                        {},
                    )
                    secscan_manifests_skipped.labels(reason="artifact").inc()
                    continue

            indexable.append((candidate, manifest, layers))

        if not indexable:
            return

        # Phase 2: Concurrent Clair API calls
        results = {}
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_candidate = {}
            for candidate, manifest, layers in indexable:
                logger.debug(
                    "Indexing manifest [%d] %s/%s@%s",
                    manifest._db_id,
                    candidate.repository.namespace_user,
                    candidate.repository.name,
                    manifest.digest,
                )
                future = executor.submit(self._call_clair_index, manifest, layers)
                future_to_candidate[future] = (candidate, manifest)

            for future in as_completed(future_to_candidate):
                candidate, manifest = future_to_candidate[future]
                try:
                    report, state = future.result()
                    results[candidate.id] = (candidate, manifest, report, state, None)
                except InvalidContentSent:
                    results[candidate.id] = (candidate, manifest, None, None, "invalid_content")
                    secscan_index_errors.labels(error_type="invalid_content").inc()
                except LayerTooLargeException:
                    results[candidate.id] = (candidate, manifest, None, None, "layer_too_large")
                    secscan_index_errors.labels(error_type="layer_too_large").inc()
                except APIRequestFailure:
                    results[candidate.id] = (candidate, manifest, None, None, "api_failure")
                    secscan_index_errors.labels(error_type="api_failure").inc()
                    logger.exception("Failed to index manifest %s", candidate.id)

        # Phase 3: Write results to DB (serial)
        succeeded = 0
        failed = 0
        skipped = len(claimed_manifests) - len(indexable)

        for manifest_id, result_tuple in results.items():
            candidate, manifest, report, state, error = result_tuple

            if error == "invalid_content":
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.MANIFEST_UNSUPPORTED,
                    "none",
                    {},
                )
                logger.warning("Failed to perform indexing, invalid content sent")
                failed += 1
            elif error == "layer_too_large":
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.MANIFEST_LAYER_TOO_LARGE,
                    "none",
                    {},
                )
                logger.warning("Failed to perform indexing, layer too large")
                failed += 1
            elif error == "api_failure":
                self._upsert_status(
                    candidate.id, candidate.repository_id, IndexStatus.FAILED, "", {}
                )
                logger.warning("Failed to perform indexing, security scanner API error")
                failed += 1
            elif report["state"] == IndexReportState.Index_Finished:
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.COMPLETED,
                    state,
                    report.get("err", {}),
                )
                succeeded += 1

                # Record time-to-first-scan metric
                if not manifest.has_been_scanned:
                    created_at = manifest.created_at
                    if created_at is not None:
                        dur_ms = get_epoch_timestamp_ms() - created_at
                        dur_sec = dur_ms / 1000
                        secscan_result_duration.observe(dur_sec)

                    self._handle_notification(manifest)

            elif report["state"] == IndexReportState.Index_Error:
                self._upsert_status(
                    candidate.id,
                    candidate.repository_id,
                    IndexStatus.FAILED,
                    state,
                    report.get("err", {}),
                )
                failed += 1

        logger.info(
            "Finished indexing batch: %d succeeded, %d failed, %d skipped",
            succeeded,
            failed,
            skipped,
        )

    def perform_indexing(self, start_token=None, batch_size=None):
        """
        Main indexing loop. Claims and processes manifests in priority order.
        No ScanToken needed - SELECT FOR UPDATE SKIP LOCKED handles coordination.

        batch_size is the total cap per cycle (max manifests to process in one call).
        Within that cap, manifests are claimed in smaller chunks to avoid long-running transactions.
        """
        try:
            indexer_state = self._secscan_api.state()
        except APIRequestFailure:
            return None

        # Total cap per cycle (max manifests to process)
        if not batch_size:
            batch_size = self.app.config.get("SECURITY_SCANNER_V4_BATCH_SIZE", 0)
            if not batch_size:
                batch_size = 100  # Default if config is 0

        # Claim this many at a time (smaller chunks)
        chunk_size = min(batch_size, 50)

        logger.info(
            "Starting indexing cycle: batch_size=%d, chunk_size=%d",
            batch_size,
            chunk_size,
        )

        reindex_threshold = datetime.utcnow() - timedelta(
            seconds=self.app.config.get(
                "SECURITY_SCANNER_V4_REINDEX_THRESHOLD",
                DEFAULT_SECURITY_SCANNER_V4_REINDEX_THRESHOLD,
            )
        )
        stale_threshold = datetime.utcnow() - timedelta(
            seconds=self.app.config.get(
                "SECURITY_SCANNER_V4_IN_PROGRESS_TIMEOUT", DEFAULT_IN_PROGRESS_TIMEOUT
            )
        )

        indexer_hash = indexer_state.get("state", "")
        remaining = batch_size

        # High-priority queries always run
        high_priority_queries = [
            ("not_indexed", lambda: self._not_indexed_query()),
            ("stale", lambda: self._stale_in_progress_query(stale_threshold)),
            ("failed", lambda: self._failed_query(reindex_threshold)),
        ]

        for query_type, query_fn in high_priority_queries:
            while remaining > 0:
                claim_size = min(chunk_size, remaining)
                claimed = self._claim_manifests(query_fn, claim_size)
                if not claimed:
                    break
                logger.info(
                    "Processing %s query: claimed %d manifest(s) (IDs: %d to %d)",
                    query_type,
                    len(claimed),
                    claimed[0].id,
                    claimed[-1].id,
                )
                secscan_manifests_claimed.labels(query_type=query_type).inc(len(claimed))
                remaining -= len(claimed)
                self._index_batch_concurrent(claimed, reindex_threshold)

        # Re-indexing only if enabled AND we have remaining capacity
        if remaining > 0 and self.app.config.get("SECURITY_SCANNER_V4_ENABLE_REINDEXING", True):
            # Even smaller chunks for reindex (lower priority)
            reindex_chunk = min(chunk_size // 5, remaining)
            if reindex_chunk == 0:
                reindex_chunk = 1

            query_fn = lambda: self._needs_reindex_query(indexer_hash, reindex_threshold)
            while remaining > 0:
                claim_size = min(reindex_chunk, remaining)
                claimed = self._claim_manifests(query_fn, claim_size)
                if not claimed:
                    break
                logger.info(
                    "Processing reindex query: claimed %d manifest(s) (IDs: %d to %d)",
                    len(claimed),
                    claimed[0].id,
                    claimed[-1].id,
                )
                secscan_manifests_claimed.labels(query_type="reindex").inc(len(claimed))
                remaining -= len(claimed)
                self._index_batch_concurrent(claimed, reindex_threshold)

        total_processed = batch_size - remaining
        logger.info("Indexing cycle complete: %d manifest(s) processed", total_processed)

        # No ScanToken needed
        return None

    def perform_indexing_recent_manifests(self, batch_size=None):
        """
        No-op in v2. The main perform_indexing loop handles all manifests efficiently.
        With SKIP LOCKED, new manifests are picked up immediately by the not_indexed query.
        """
        pass

    # ===== Methods copied from V4SecurityScanner (no concurrency issues) =====

    def load_security_information(
        self, manifest_or_legacy_image, include_vulnerabilities=False, model_cache=None
    ):
        if not isinstance(manifest_or_legacy_image, ManifestDataType):
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
            )

        status = None
        try:
            status = ManifestSecurityStatus.get(manifest=manifest_or_legacy_image._db_id)
        except ManifestSecurityStatus.DoesNotExist:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        if status.index_status == IndexStatus.FAILED:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.FAILED_TO_INDEX)

        if status.index_status == IndexStatus.MANIFEST_UNSUPPORTED:
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
            )

        if status.index_status == IndexStatus.MANIFEST_LAYER_TOO_LARGE:
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.MANIFEST_LAYER_TOO_LARGE
            )

        if status.index_status == IndexStatus.IN_PROGRESS:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        assert status.index_status == IndexStatus.COMPLETED

        def security_report_loader():
            return self._secscan_api.vulnerability_report(manifest_or_legacy_image.digest)

        try:
            if model_cache:
                security_report_key = cache_key.for_security_report(
                    manifest_or_legacy_image.digest, model_cache.cache_config
                )
                report = model_cache.retrieve(security_report_key, security_report_loader)
            else:
                report = security_report_loader()
        except APIRequestFailure as arf:
            return SecurityInformationLookupResult.for_request_error(str(arf))

        if report is None:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        return SecurityInformationLookupResult.for_data(
            SecurityInformation(Layer(report["manifest_hash"], "", "", 4, features_for(report)))
        )

    def lookup_notification_page(self, notification_id, page_index=None):
        try:
            notification_page_results = self._secscan_api.retrieve_notification_page(
                notification_id, page_index
            )

            if notification_page_results is None:
                return PaginatedNotificationResult(
                    PaginatedNotificationStatus.FATAL_ERROR, None, None
                )
        except APIRequestFailure:
            return PaginatedNotificationResult(
                PaginatedNotificationStatus.RETRYABLE_ERROR, None, None
            )

        return PaginatedNotificationResult(
            PaginatedNotificationStatus.SUCCESS,
            notification_page_results["notifications"],
            notification_page_results.get("page", {}).get("next"),
        )

    def mark_notification_handled(self, notification_id):
        try:
            self._secscan_api.delete_notification(notification_id)
            return True
        except APIRequestFailure:
            return False

    def process_notification_page(self, page_result):
        for notification_data in page_result:
            if notification_data["reason"] != "added":
                continue

            yield UpdatedVulnerability(
                notification_data["manifest"],
                Vulnerability(
                    Severity=notification_data["vulnerability"].get("normalized_severity"),
                    Description=notification_data["vulnerability"].get("description"),
                    NamespaceName=notification_data["vulnerability"].get("package", {}).get("name"),
                    Name=notification_data["vulnerability"].get("name"),
                    FixedBy=maybe_urlencoded(
                        notification_data["vulnerability"].get("fixed_in_version")
                    ),
                    Link=notification_data["vulnerability"].get("links"),
                    Metadata={},
                ),
            )

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    @property
    def legacy_api_handler(self):
        raise NotImplementedError("Unsupported for this security scanner version")

    def garbage_collect_manifest_report(self, manifest_digest):
        def manifest_digest_exists():
            query = Manifest.select().where(Manifest.digest == manifest_digest)
            try:
                query.get()
            except Manifest.DoesNotExist:
                return False
            return True

        with db_transaction():
            if not manifest_digest_exists():
                try:
                    self._secscan_api.delete(manifest_digest)
                    return True
                except APIRequestFailure:
                    logger.exception("Failed to delete manifest, security scanner API error")

        return None
