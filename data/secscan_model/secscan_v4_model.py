import logging
import itertools

from collections import namedtuple
from datetime import datetime, timedelta
from math import log10
from peewee import fn, JOIN
from enum import Enum

from data.secscan_model.interface import SecurityScannerInterface, InvalidConfigurationException
from data.secscan_model.datatypes import (
    ScanLookupStatus,
    SecurityInformationLookupResult,
    SecurityInformation,
    Feature,
    Layer,
    Vulnerability,
    PaginatedNotificationResult,
    PaginatedNotificationStatus,
    UpdatedVulnerability,
)
from data.readreplica import ReadOnlyModeException
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.registry_model import registry_model
from util.migrate.allocator import yield_random_entries
from util.secscan.validator import V4SecurityConfigValidator
from util.secscan.v4.api import ClairSecurityScannerAPI, APIRequestFailure
from util.secscan import PRIORITY_LEVELS
from util.secscan.blob import BlobURLRetriever
from util.config import URLSchemeAndHostname

from data.database import (
    Manifest,
    ManifestSecurityStatus,
    IndexerVersion,
    IndexStatus,
    Repository,
    User,
    db_transaction,
)


logger = logging.getLogger(__name__)


IndexReportState = namedtuple("IndexReportState", ["Index_Finished", "Index_Error"])(
    "IndexFinished", "IndexError"
)


class ScanToken(namedtuple("NextScanToken", ["min_id"])):
    """
    ScanToken represents an opaque token that can be passed between runs of the security worker
    to continue scanning whereever the previous run left off. Note that the data of the token is
    *opaque* to the security worker, and the security worker should *not* pull any data out or modify
    the token in any way.
    """


class NoopV4SecurityScanner(SecurityScannerInterface):
    """
    No-op implementation of the security scanner interface for Clair V4.
    """

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
        return SecurityInformationLookupResult.for_request_error("security scanner misconfigured")

    def perform_indexing(self, start_token=None):
        return None

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    @property
    def legacy_api_handler(self):
        raise NotImplementedError("Unsupported for this security scanner version")

    def lookup_notification_page(self, notification_id, page_index=None):
        return None

    def process_notification_page(self, page_result):
        raise NotImplementedError("Unsupported for this security scanner version")

    def mark_notification_handled(self, notification_id):
        raise NotImplementedError("Unsupported for this security scanner version")


class V4SecurityScanner(SecurityScannerInterface):
    """
    Implementation of the security scanner interface for Clair V4 API-compatible implementations.
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
        )

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
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

        if status.index_status == IndexStatus.IN_PROGRESS:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        assert status.index_status == IndexStatus.COMPLETED

        try:
            report = self._secscan_api.vulnerability_report(manifest_or_legacy_image.digest)
        except APIRequestFailure as arf:
            try:
                status.delete_instance()
            except ReadOnlyModeException:
                pass

            return SecurityInformationLookupResult.for_request_error(str(arf))

        if report is None:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        # TODO(alecmerdler): Provide a way to indicate the current scan is outdated (`report.state != status.indexer_hash`)

        return SecurityInformationLookupResult.for_data(
            SecurityInformation(Layer(report["manifest_hash"], "", "", 4, features_for(report)))
        )

    def perform_indexing(self, start_token=None):
        try:
            indexer_state = self._secscan_api.state()
        except APIRequestFailure:
            return None

        min_id = (
            start_token.min_id
            if start_token is not None
            else Manifest.select(fn.Min(Manifest.id)).scalar()
        )
        max_id = Manifest.select(fn.Max(Manifest.id)).scalar()

        if max_id is None or min_id is None or min_id > max_id:
            return None

        reindex_threshold = lambda: datetime.utcnow() - timedelta(
            seconds=self.app.config.get("SECURITY_SCANNER_V4_REINDEX_THRESHOLD")
        )

        # TODO(alecmerdler): Filter out any `Manifests` that are still being uploaded
        def not_indexed_query():
            return (
                Manifest.select()
                .join(ManifestSecurityStatus, JOIN.LEFT_OUTER)
                .where(ManifestSecurityStatus.id >> None)
            )

        def index_error_query():
            return (
                Manifest.select()
                .join(ManifestSecurityStatus)
                .where(
                    ManifestSecurityStatus.index_status == IndexStatus.FAILED,
                    ManifestSecurityStatus.last_indexed < reindex_threshold(),
                )
            )

        def needs_reindexing_query(indexer_hash):
            return (
                Manifest.select()
                .join(ManifestSecurityStatus)
                .where(
                    ManifestSecurityStatus.indexer_hash != indexer_hash,
                    ManifestSecurityStatus.last_indexed < reindex_threshold(),
                )
            )

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        # TODO(alecmerdler): We want to index newer manifests first, while backfilling older manifests...
        iterator = itertools.chain(
            yield_random_entries(not_indexed_query, Manifest.id, batch_size, max_id, min_id,),
            yield_random_entries(index_error_query, Manifest.id, batch_size, max_id, min_id,),
            yield_random_entries(
                lambda: needs_reindexing_query(indexer_state.get("state", "")),
                Manifest.id,
                batch_size,
                max_id,
                min_id,
            ),
        )

        for candidate, abt, num_remaining in iterator:
            manifest = ManifestDataType.for_manifest(candidate, None)
            layers = registry_model.list_manifest_layers(manifest, self.storage, True)
            if layers is None:
                logger.warning(
                    "Cannot index %s/%s@%s due to manifest being invalid"
                    % (
                        candidate.repository.namespace_user,
                        candidate.repository.name,
                        manifest.digest,
                    )
                )
                with db_transaction():
                    ManifestSecurityStatus.delete().where(
                        ManifestSecurityStatus.manifest == candidate
                    ).execute()
                    ManifestSecurityStatus.create(
                        manifest=candidate,
                        repository=candidate.repository,
                        index_status=IndexStatus.MANIFEST_UNSUPPORTED,
                        indexer_hash="none",
                        indexer_version=IndexerVersion.V4,
                        metadata_json={},
                    )
                continue

            logger.debug(
                "Indexing %s/%s@%s"
                % (candidate.repository.namespace_user, candidate.repository.name, manifest.digest)
            )

            try:
                (report, state) = self._secscan_api.index(manifest, layers)
            except APIRequestFailure:
                logger.exception("Failed to perform indexing, security scanner API error")
                return None

            with db_transaction():
                ManifestSecurityStatus.delete().where(
                    ManifestSecurityStatus.manifest == candidate
                ).execute()
                ManifestSecurityStatus.create(
                    manifest=candidate,
                    repository=candidate.repository,
                    error_json=report["err"],
                    index_status=(
                        IndexStatus.FAILED
                        if report["state"] == IndexReportState.Index_Error
                        else IndexStatus.COMPLETED
                    ),
                    indexer_hash=state,
                    indexer_version=IndexerVersion.V4,
                    metadata_json={},
                )

        return ScanToken(max_id + 1)

    def lookup_notification_page(self, notification_id, page_index=None):
        try:
            notification_page_results = self._secscan_api.retrieve_notification_page(
                notification_id, page_index
            )

            # If we get back None, then the notification no longer exists.
            if notification_page_results is None:
                return PaginatedNotificationResult(
                    PaginatedNotificationStatus.FATAL_ERROR, None, None
                )
        except APIRequestFailure:
            return PaginatedNotificationResult(
                PaginatedNotificationStatus.RETRYABLE_ERROR, None, None
            )

        # FIXME(alecmerdler): Debugging tests failing in CI
        print(notification_page_results)
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
                    FixedBy=notification_data["vulnerability"].get("fixed_in_version"),
                    Link=notification_data["vulnerability"].get("links"),
                    Metadata={},
                ),
            )

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    @property
    def legacy_api_handler(self):
        raise NotImplementedError("Unsupported for this security scanner version")


def features_for(report):
    """
    Transforms a Clair v4 `VulnerabilityReport` dict into the standard shape of a 
    Quay Security scanner response.
    """

    features = []
    for pkg_id, pkg in report["packages"].items():
        pkg_env = report["environments"][pkg_id][0]
        pkg_vulns = [
            report["vulnerabilities"][vuln_id]
            for vuln_id in report["package_vulnerabilities"].get(pkg_id, [])
        ]

        features.append(
            Feature(
                pkg["name"],
                "",
                "",
                pkg_env["introduced_in"],
                pkg["version"],
                [
                    Vulnerability(
                        vuln["normalized_severity"]
                        if vuln["normalized_severity"]
                        else PRIORITY_LEVELS["Unknown"]["value"],
                        "",
                        vuln["links"],
                        vuln["fixed_in_version"] if vuln["fixed_in_version"] != "0" else "",
                        vuln["description"],
                        vuln["name"],
                        None,
                    )
                    for vuln in pkg_vulns
                ],
            )
        )

    return features
