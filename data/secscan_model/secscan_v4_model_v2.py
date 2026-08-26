import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import features
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
from data.secscan_model.interface import SecurityScannerIndexerInterface
from data.secscan_model.secscan_v4_model import IndexReportState, _has_container_layers
from image.docker.schema1 import DOCKER_SCHEMA1_CONTENT_TYPES
from util.metrics.prometheus import (
    secscan_v2_claim_status,
    secscan_v2_cycle_duration,
    secscan_v2_manifests_claimed,
    secscan_v2_scan_duration,
    secscan_v2_scan_result,
)
from util.secscan import PRIORITY_LEVELS
from util.secscan.blob import BlobURLRetriever
from util.secscan.v4.api import (
    APIRequestFailure,
    ClairSecurityScannerAPI,
    InvalidContentSent,
    LayerTooLargeException,
    Non200ResponseException,
)
from util.secscan.validator import V4SecurityConfigValidator

logger = logging.getLogger(__name__)

DEFAULT_REINDEX_THRESHOLD = 86400
DEFAULT_MAX_SCAN_RETRIES = 5
DEFAULT_INDEX_THREAD_COUNT = 3
STALE_IN_PROGRESS_HOURS = 6
TAG_LIMIT = 100


class V4SecurityScannerV2(SecurityScannerIndexerInterface):
    def __init__(self, app, instance_keys, storage):
        self.app = app
        self.storage = storage

        if app.config.get("SECURITY_SCANNER_V4_ENDPOINT", None) is None:
            raise ValueError("Missing SECURITY_SCANNER_V4_ENDPOINT configuration")

        validator = V4SecurityConfigValidator(
            app.config.get("FEATURE_SECURITY_SCANNER", False),
            app.config.get("SECURITY_SCANNER_V4_ENDPOINT", None),
        )

        if not validator.valid():
            raise ValueError("Failed to validate security scanner V4 configuration")

        self._secscan_api = ClairSecurityScannerAPI(
            endpoint=app.config.get("SECURITY_SCANNER_V4_ENDPOINT"),
            client=app.config.get("HTTPCLIENT"),
            blob_url_retriever=BlobURLRetriever(storage, instance_keys, app),
            jwt_psk=app.config.get("SECURITY_SCANNER_V4_PSK", None),
            max_layer_size=app.config.get("SECURITY_SCANNER_V4_INDEX_MAX_LAYER_SIZE", None),
        )

    def perform_indexing_recent_manifests(self, batch_size=None):
        pass

    def perform_indexing(self, start_token=None, batch_size=None):
        cycle_start = time.monotonic()

        try:
            indexer_state = self._secscan_api.state()
        except APIRequestFailure:
            logger.exception("Failed to fetch indexer state from Clair")
            return

        indexer_hash = indexer_state.get("state", "")

        reindex_threshold = datetime.utcnow() - timedelta(
            seconds=self.app.config.get(
                "SECURITY_SCANNER_V4_REINDEX_THRESHOLD", DEFAULT_REINDEX_THRESHOLD
            )
        )
        stale_threshold = datetime.utcnow() - timedelta(hours=STALE_IN_PROGRESS_HOURS)

        claimed = self._find_and_claim_batch(
            batch_size, reindex_threshold, stale_threshold, indexer_hash
        )

        secscan_v2_manifests_claimed.observe(len(claimed))

        if not claimed:
            logger.debug("No manifests to index this cycle")
            return

        indexable = []
        for mss_row in claimed:
            prepared = self._prepare_for_indexing(mss_row.manifest)
            if prepared is not None:
                manifest, layers = prepared
                indexable.append((mss_row, manifest, layers))

        if indexable:
            thread_count = self.app.config.get(
                "SECURITY_SCANNER_V2_INDEX_THREAD_COUNT", DEFAULT_INDEX_THREAD_COUNT
            )
            with ThreadPoolExecutor(
                max_workers=thread_count, thread_name_prefix="secscan-v2"
            ) as executor:
                futures = {
                    executor.submit(self._call_clair_index, manifest, layers): (
                        mss_row,
                        manifest,
                    )
                    for mss_row, manifest, layers in indexable
                }
                for future in as_completed(futures):
                    mss_row, manifest = futures[future]
                    try:
                        result = future.result()
                    except Exception:
                        logger.exception("Unexpected error indexing manifest")
                        self._mark_failed(
                            mss_row.manifest.id,
                            "unexpected_error",
                            {"error": "unexpected worker error"},
                            indexer_hash,
                        )
                        secscan_v2_scan_result.labels(result="failed").inc()
                        continue
                    self._process_index_result(mss_row.manifest, manifest, result, indexer_hash)

        cycle_duration = time.monotonic() - cycle_start
        secscan_v2_cycle_duration.observe(cycle_duration)
        logger.debug("Indexing cycle complete: %d manifests in %.1fs", len(claimed), cycle_duration)

    def _scan_conditions(self, reindex_threshold, stale_threshold, indexer_hash):
        conditions = (ManifestSecurityStatus.index_status == IndexStatus.PENDING) | (
            (ManifestSecurityStatus.index_status == IndexStatus.IN_PROGRESS)
            & (ManifestSecurityStatus.last_indexed < stale_threshold)
        )

        conditions |= (ManifestSecurityStatus.index_status == IndexStatus.FAILED) & (
            ManifestSecurityStatus.last_indexed < reindex_threshold
        )
        conditions |= (
            (
                ManifestSecurityStatus.index_status.not_in(
                    [
                        IndexStatus.MANIFEST_UNSUPPORTED,
                        IndexStatus.MANIFEST_LAYER_TOO_LARGE,
                        IndexStatus.IN_PROGRESS,
                    ]
                )
            )
            & (ManifestSecurityStatus.indexer_hash != indexer_hash)
            & (ManifestSecurityStatus.last_indexed < reindex_threshold)
        )

        return conditions

    def _find_and_claim_batch(self, batch_size, reindex_threshold, stale_threshold, indexer_hash):
        max_retries = self.app.config.get(
            "SECURITY_SCANNER_MAX_SCAN_RETRIES", DEFAULT_MAX_SCAN_RETRIES
        )
        conditions = self._scan_conditions(reindex_threshold, stale_threshold, indexer_hash)

        candidate_ids = [
            row.id
            for row in ManifestSecurityStatus.select(
                ManifestSecurityStatus.id, can_use_read_replica=True
            )
            .where(conditions)
            .order_by(ManifestSecurityStatus.last_indexed.desc())
            .limit(batch_size)
        ]

        if not candidate_ids:
            return []

        with db_transaction():
            query = (
                ManifestSecurityStatus.select(ManifestSecurityStatus, Manifest)
                .join(Manifest, on=(ManifestSecurityStatus.manifest == Manifest.id))
                .where(ManifestSecurityStatus.id.in_(candidate_ids) & conditions)
                .order_by(ManifestSecurityStatus.last_indexed.desc())
            )

            rows = list(db_for_update(query, skip_locked=True))

            if not rows:
                return []

            for row in rows:
                secscan_v2_claim_status.labels(status=row.index_status.name).inc()

            now = datetime.utcnow()

            eligible = []
            exhausted_ids = []
            for r in rows:
                metadata = r.metadata_json or {}
                retry_count = metadata.get("retry_count", 0)
                if metadata.get("last_failed_hash") != indexer_hash:
                    retry_count = 0
                if r.index_status == IndexStatus.FAILED and retry_count >= max_retries:
                    exhausted_ids.append(r.id)
                else:
                    eligible.append(r)

            if exhausted_ids:
                ManifestSecurityStatus.update(
                    index_status=IndexStatus.SCAN_RETRIES_EXHAUSTED,
                    last_indexed=now,
                ).where(ManifestSecurityStatus.id.in_(exhausted_ids)).execute()

            if not eligible:
                return []

            row_ids = [r.id for r in eligible]
            ManifestSecurityStatus.update(
                index_status=IndexStatus.IN_PROGRESS,
                indexer_hash="in_progress_v2",
                last_indexed=now,
            ).where(ManifestSecurityStatus.id.in_(row_ids)).execute()

            return eligible

    def _prepare_for_indexing(self, candidate):
        manifest = ManifestDataType.for_manifest(candidate, None)

        if manifest.is_manifest_list:
            self._mark_unsupported(manifest)
            secscan_v2_scan_result.labels(result="unsupported").inc()
            return None

        layers = registry_model.list_manifest_layers(manifest, self.storage, True)

        if layers is None or len(layers) == 0:
            logger.warning(
                "Cannot index %s/%s@%s: manifest has no layers",
                candidate.repository.namespace_user,
                candidate.repository.name,
                manifest.digest,
            )
            self._mark_unsupported(manifest)
            secscan_v2_scan_result.labels(result="unsupported").inc()
            return None

        if manifest.media_type not in DOCKER_SCHEMA1_CONTENT_TYPES:
            if not _has_container_layers(layers):
                logger.info(
                    "Cannot index %s/%s@%s: not a container image",
                    candidate.repository.namespace_user,
                    candidate.repository.name,
                    manifest.digest,
                )
                self._mark_unsupported(manifest)
                secscan_v2_scan_result.labels(result="unsupported").inc()
                return None

        return manifest, layers

    def _call_clair_index(self, manifest, layers):
        scan_start = time.monotonic()
        try:
            report, state = self._secscan_api.index(manifest, layers)
            secscan_v2_scan_duration.observe(time.monotonic() - scan_start)
            return report, state, None
        except (
            InvalidContentSent,
            Non200ResponseException,
            APIRequestFailure,
            LayerTooLargeException,
        ) as ex:
            return None, None, ex

    def _process_index_result(self, candidate, manifest, result, current_indexer_hash):
        report, state, error = result

        if error is not None:
            if isinstance(error, InvalidContentSent):
                self._mark_unsupported(manifest)
                secscan_v2_scan_result.labels(result="unsupported").inc()
                logger.warning("Failed to index: invalid content sent")
            elif isinstance(error, Non200ResponseException):
                self._mark_failed(
                    candidate.id,
                    "server_error",
                    {"error": "non-200 response", "status_code": error.response.status_code},
                    current_indexer_hash,
                )
                secscan_v2_scan_result.labels(result="api_error").inc()
                logger.error(
                    "Failed to index: security scanner returned %s", error.response.status_code
                )
            elif isinstance(error, APIRequestFailure):
                self._mark_failed(
                    candidate.id,
                    "api_failure",
                    {"error": str(error)},
                    current_indexer_hash,
                )
                secscan_v2_scan_result.labels(result="api_error").inc()
                logger.error("Failed to index: security scanner API error: %s", error)
            elif isinstance(error, LayerTooLargeException):
                self._mark_layer_too_large(manifest)
                secscan_v2_scan_result.labels(result="layer_too_large").inc()
                logger.error("Failed to index: layer too large")
            return

        if report["state"] == IndexReportState.Index_Finished:
            self._handle_scan_success(manifest, candidate)
            ManifestSecurityStatus.update(
                error_json=report["err"],
                index_status=IndexStatus.COMPLETED,
                indexer_hash=state,
                indexer_version=IndexerVersion.V4,
                metadata_json={},
                last_indexed=datetime.utcnow(),
            ).where(ManifestSecurityStatus.manifest == candidate).execute()
            secscan_v2_scan_result.labels(result="completed").inc()
        elif report["state"] == IndexReportState.Index_Error:
            self._mark_failed(candidate.id, state, report["err"], current_indexer_hash)
            secscan_v2_scan_result.labels(result="failed").inc()
        else:
            self._mark_failed(
                candidate.id,
                "unknown_state",
                {"error": "unknown_state", "state": report.get("state")},
                current_indexer_hash,
            )
            secscan_v2_scan_result.labels(result="failed").inc()
            logger.warning(
                "Unknown index state '%s' for manifest %d",
                report.get("state"),
                candidate.id,
            )

    def _handle_scan_success(self, manifest, candidate):
        if not manifest.has_been_scanned:
            created_at = manifest.created_at
            if created_at is not None:
                dur_ms = get_epoch_timestamp_ms() - created_at
                dur_sec = dur_ms / 1000
                from util.metrics.prometheus import secscan_result_duration

                secscan_result_duration.observe(dur_sec)

            if features.SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX:
                self._send_vulnerability_notifications(manifest, candidate)

    def _send_vulnerability_notifications(self, manifest, candidate):
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

        for key in list(found_vulnerabilities):
            vuln = found_vulnerabilities[key]
            found_severity = PRIORITY_LEVELS.get(
                vuln["normalized_severity"], PRIORITY_LEVELS["Unknown"]
            )

            if found_severity["score"] < lowest_severity["score"]:
                continue

            tag_names = list(registry_model.tag_names_for_manifest(manifest, TAG_LIMIT))
            tags = list(tag_names) if tag_names else [manifest.digest]

            event_data = {
                "tags": tags,
                "vulnerable_index_report_created": "true",
                "vulnerability": {
                    "id": vuln["id"],
                    "description": vuln["description"],
                    "link": vuln["links"],
                    "priority": vuln["severity"],
                    "has_fix": bool(vuln["fixed_in_version"]),
                },
            }

            notifications.spawn_notification(manifest.repository, "vulnerability_found", event_data)

    def _mark_unsupported(self, manifest):
        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == manifest._db_id,
                ManifestSecurityStatus.repository == manifest.repository._db_id,
            ).execute()
            ManifestSecurityStatus.create(
                manifest=manifest._db_id,
                repository=manifest.repository._db_id,
                index_status=IndexStatus.MANIFEST_UNSUPPORTED,
                indexer_hash="none",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

    def _mark_layer_too_large(self, manifest):
        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == manifest._db_id,
                ManifestSecurityStatus.repository == manifest.repository._db_id,
            ).execute()
            ManifestSecurityStatus.create(
                manifest=manifest._db_id,
                repository=manifest.repository._db_id,
                index_status=IndexStatus.MANIFEST_LAYER_TOO_LARGE,
                indexer_hash="none",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

    def _mark_failed(self, manifest_id, indexer_hash, error_json, current_indexer_hash):
        try:
            mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifest_id)
            metadata = mss.metadata_json or {}
            if metadata.get("last_failed_hash") != current_indexer_hash:
                metadata["retry_count"] = 1
            else:
                metadata["retry_count"] = metadata.get("retry_count", 0) + 1
        except ManifestSecurityStatus.DoesNotExist:
            metadata = {"retry_count": 1}
        metadata["last_failed_hash"] = current_indexer_hash

        ManifestSecurityStatus.update(
            index_status=IndexStatus.FAILED,
            indexer_hash=indexer_hash,
            error_json=error_json,
            metadata_json=metadata,
            last_indexed=datetime.utcnow(),
        ).where(
            ManifestSecurityStatus.manifest == manifest_id,
            ManifestSecurityStatus.index_status == IndexStatus.IN_PROGRESS,
        ).execute()
