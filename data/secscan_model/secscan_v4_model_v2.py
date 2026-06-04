import logging
import time
import urllib
from collections import namedtuple
from datetime import datetime, timedelta

from peewee import JOIN, IntegrityError, fn

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
)
from util.secscan.validator import V4SecurityConfigValidator

logger = logging.getLogger(__name__)

DEFAULT_REINDEX_THRESHOLD = 86400
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

        claimed_new = self._claim_unindexed_manifests(batch_size)

        remaining = batch_size - len(claimed_new)
        claimed_mss = []
        if remaining > 0:
            claimed_mss = self._find_and_claim_batch(
                remaining, reindex_threshold, stale_threshold, indexer_hash
            )

        total_claimed = len(claimed_new) + len(claimed_mss)
        secscan_v2_manifests_claimed.observe(total_claimed)

        if total_claimed == 0:
            logger.debug("No manifests to index this cycle")
            return

        for candidate in claimed_new:
            self._index_manifest_by_id(candidate.id, candidate.repository_id)

        for mss_row in claimed_mss:
            self._index_manifest_by_id(mss_row.manifest_id, mss_row.repository_id)

        cycle_duration = time.monotonic() - cycle_start
        secscan_v2_cycle_duration.observe(cycle_duration)
        logger.debug(
            "Indexing cycle complete: %d manifests in %.1fs", total_claimed, cycle_duration
        )

    def _find_and_claim_batch(self, batch_size, reindex_threshold, stale_threshold, indexer_hash):
        with db_transaction():
            query = (
                ManifestSecurityStatus.select()
                .where(
                    (
                        (ManifestSecurityStatus.index_status == IndexStatus.FAILED)
                        & (ManifestSecurityStatus.last_indexed < reindex_threshold)
                    )
                    | (
                        (ManifestSecurityStatus.index_status == IndexStatus.IN_PROGRESS)
                        & (ManifestSecurityStatus.last_indexed < stale_threshold)
                    )
                    | (
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
                )
                .order_by(ManifestSecurityStatus.last_indexed.asc())
                .limit(batch_size)
            )

            rows = list(db_for_update(query, skip_locked=True))

            if not rows:
                return []

            row_ids = [r.id for r in rows]
            now = datetime.utcnow()
            ManifestSecurityStatus.update(
                index_status=IndexStatus.IN_PROGRESS,
                indexer_hash="in_progress_v2",
                last_indexed=now,
            ).where(ManifestSecurityStatus.id.in_(row_ids)).execute()

            return rows

    def _claim_unindexed_manifests(self, batch_size):
        candidates = list(
            Manifest.select(Manifest.id, Manifest.repository, can_use_read_replica=True)
            .join(ManifestSecurityStatus, JOIN.LEFT_OUTER)
            .where(ManifestSecurityStatus.id >> None)
            .order_by(Manifest.id.desc())
            .limit(batch_size * 2)
        )

        if not candidates:
            return []

        claimed = []
        now = datetime.utcnow()
        for candidate in candidates:
            try:
                ManifestSecurityStatus.create(
                    manifest=candidate.id,
                    repository=candidate.repository_id,
                    index_status=IndexStatus.IN_PROGRESS,
                    indexer_hash="in_progress_v2",
                    indexer_version=IndexerVersion.V4,
                    last_indexed=now,
                    metadata_json={},
                )
                claimed.append(candidate)
                if len(claimed) >= batch_size:
                    break
            except IntegrityError:
                continue

        return claimed

    def _index_manifest_by_id(self, manifest_id, repository_id):
        try:
            candidate = Manifest.get(Manifest.id == manifest_id)
        except Manifest.DoesNotExist:
            logger.warning("Manifest %d no longer exists, skipping", manifest_id)
            self._mark_failed(manifest_id, "manifest_deleted", {"error": "manifest not found"})
            return

        manifest = ManifestDataType.for_manifest(candidate, None)

        if manifest.is_manifest_list:
            self._mark_unsupported(manifest)
            secscan_v2_scan_result.labels(result="unsupported").inc()
            return

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
            return

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
                return

        scan_start = time.monotonic()
        try:
            (report, state) = self._secscan_api.index(manifest, layers)
        except InvalidContentSent:
            self._mark_unsupported(manifest)
            secscan_v2_scan_result.labels(result="unsupported").inc()
            logger.exception("Failed to index: invalid content sent")
            return
        except APIRequestFailure as ex:
            self._mark_failed(candidate.id, "api_failure", {"error": str(ex)})
            secscan_v2_scan_result.labels(result="api_error").inc()
            logger.exception("Failed to index: security scanner API error")
            return
        except LayerTooLargeException:
            self._mark_layer_too_large(manifest)
            secscan_v2_scan_result.labels(result="layer_too_large").inc()
            logger.exception("Failed to index: layer too large")
            return

        scan_duration = time.monotonic() - scan_start
        secscan_v2_scan_duration.observe(scan_duration)

        if report["state"] == IndexReportState.Index_Finished:
            index_status = IndexStatus.COMPLETED
            self._handle_scan_success(manifest, candidate)
        elif report["state"] == IndexReportState.Index_Error:
            index_status = IndexStatus.FAILED
        else:
            self._mark_failed(
                candidate.id,
                "unknown_state",
                {"error": "unknown_state", "state": report.get("state")},
            )
            secscan_v2_scan_result.labels(result="failed").inc()
            logger.warning(
                "Unknown index state '%s' for manifest %d",
                report.get("state"),
                candidate.id,
            )
            return

        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == candidate
            ).execute()
            ManifestSecurityStatus.create(
                manifest=candidate,
                repository=candidate.repository,
                error_json=report["err"],
                index_status=index_status,
                indexer_hash=state,
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

        result_label = "completed" if index_status == IndexStatus.COMPLETED else "failed"
        secscan_v2_scan_result.labels(result=result_label).inc()

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

    def _mark_failed(self, manifest_id, indexer_hash, error_json):
        ManifestSecurityStatus.update(
            index_status=IndexStatus.FAILED,
            indexer_hash=indexer_hash,
            error_json=error_json,
            last_indexed=datetime.utcnow(),
        ).where(
            ManifestSecurityStatus.manifest == manifest_id,
            ManifestSecurityStatus.index_status == IndexStatus.IN_PROGRESS,
        ).execute()
