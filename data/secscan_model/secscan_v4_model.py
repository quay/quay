import logging
import itertools

from collections import namedtuple
from math import log10
from peewee import fn, JOIN

from data.secscan_model.interface import SecurityScannerInterface
from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformationLookupResult
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.registry_model import registry_model
from util.migrate.allocator import yield_random_entries
from util.secscan.validator import V4SecurityConfigValidator
from util.config import URLSchemeAndHostname

from data.database import (
    Manifest,
    ManifestSecurityStatus,
    IndexerVersion,
    IndexStatus,
    Repository,
    User,
)


logger = logging.getLogger(__name__)

# TODO(alecmerdler): Retrieve `/state` from security scanner API
indexer_state = ""


class ScanToken(namedtuple("NextScanToken", ["min_id"])):
    """
    ScanToken represents an opaque token that can be passed between runs of the security worker
    to continue scanning whereever the previous run left off. Note that the data of the token is
    *opaque* to the security worker, and the security worker should *not* pull any data out or modify
    the token in any way.
    """


class V4SecurityScanner(SecurityScannerInterface):
    """
    Implementation of the security scanner interface for Clair V4 API-compatible implementations.
    """

    def __init__(self, app, instance_keys, storage):
        self.app = app

        validator = V4SecurityConfigValidator(
            app.config.get("FEATURE_SECURITY_SCANNER", False),
            app.config.get("SECURITY_SCANNER_V4_ENDPOINT"),
        )

        if not validator.valid():
            logger.warning("Failed to validate security scanner V4 configuration")
            return

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
        if not isinstance(manifest_or_legacy_image, ManifestDataType):
            return None

        status = None
        try:
            status = ManifestSecurityStatus.get(manifest=manifest_or_legacy_image._db_id)
        except ManifestSecurityStatus.DoesNotExist:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        if status.index_status == IndexStatus.FAILED:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.FAILED_TO_INDEX)

        if status.index_status == IndexStatus.UNSUPPORTED:
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
            )

        if status.index_status in [
            IndexStatus.TIMED_OUT,
            IndexStatus.WAITING,
            IndexStatus.IN_PROGRESS,
        ]:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        assert status.index_status == IndexStatus.COMPLETED

        # TODO(alecmerdler): Fetch data from Clair API
        return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

    def perform_indexing(self, start_token=None):
        whitelisted_namespaces = self.app.config.get("SECURITY_SCANNER_V4_NAMESPACE_WHITELIST", [])

        def eligible_manifests(base_query):
            if len(whitelisted_namespaces) == 0:
                return base_query

            return (
                base_query.join(Repository)
                .join(User)
                .where(User.username << whitelisted_namespaces)
            )

        min_id = (
            start_token
            if start_token is not None
            else Manifest.select(fn.Min(Manifest.id)).scalar()
        )
        max_id = Manifest.select(fn.Max(Manifest.id)).scalar()

        if max_id is None or min_id is None or min_id > max_id:
            return None

        # FIXME(alecmerdler): Filter out any `Manifests` that are still being uploaded
        def not_indexed_query():
            return (
                eligible_manifests(Manifest.select())
                .switch(Manifest)
                .join(ManifestSecurityStatus, JOIN.LEFT_OUTER)
                .where(ManifestSecurityStatus.id >> None)
            )

        def index_error_query():
            return (
                eligible_manifests(Manifest.select())
                .switch(Manifest)
                .join(ManifestSecurityStatus)
                .where(ManifestSecurityStatus.index_status == IndexStatus.FAILED)
            )

        def needs_reindexing_query(indexer_hash):
            return (
                eligible_manifests(Manifest.select())
                .switch(Manifest)
                .join(ManifestSecurityStatus)
                .where(ManifestSecurityStatus.indexer_hash != indexer_hash)
            )

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        iterator = itertools.chain(
            yield_random_entries(not_indexed_query, Manifest.id, batch_size, max_id, min_id,),
            yield_random_entries(index_error_query, Manifest.id, batch_size, max_id, min_id,),
            yield_random_entries(
                lambda: needs_reindexing_query(indexer_state),
                Manifest.id,
                batch_size,
                max_id,
                min_id,
            ),
        )

        for candidate, abt, num_remaining in iterator:
            # TODO(alecmerdler): Call out to Clair v4 to `/index` the manifest
            logger.info("Clair v4 client not yet implemented, passing for now")
            pass

        return ScanToken(max_id + 1)

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    @property
    def legacy_api_handler(self):
        raise NotImplementedError("Unsupported for this security scanner version")
