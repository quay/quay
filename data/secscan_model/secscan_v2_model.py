import logging

from collections import namedtuple
from math import log10

from prometheus_client import Gauge
from deprecated import deprecated

from data.database import UseThenDisconnect

from data.secscan_model.interface import SecurityScannerInterface
from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformationLookupResult

from data.registry_model import registry_model
from data.registry_model.datatypes import SecurityScanStatus

from data.model.image import (
    get_images_eligible_for_scan,
    get_image_pk_field,
    get_max_id_for_sec_scan,
    get_min_id_for_sec_scan,
)

from util.migrate.allocator import yield_random_entries
from util.config import URLSchemeAndHostname
from util.secscan.api import V2SecurityConfigValidator, SecurityScannerAPI, APIRequestFailure
from util.secscan.secscan_util import get_blob_download_uri_getter


logger = logging.getLogger(__name__)


unscanned_images = Gauge(
    "quay_security_scanning_unscanned_images_remaining",
    "number of images that are not scanned by the latest security scanner",
)


class ScanToken(namedtuple("NextScanToken", ["min_id"])):
    """
    ScanToken represents an opaque token that can be passed between runs of the security worker to
    continue scanning whereever the previous run left off. Note that the data of the token is.

    *opaque* to the security worker, and the security worker should *not* pull any data out or modify
    the token in any way.
    """


@deprecated(reason="Will be replaced by a V4 API security scanner soon")
class V2SecurityScanner(SecurityScannerInterface):
    """
    Implementation of the security scanner interface for Clair V2 API-compatible implementations.

    NOTE: This is a legacy implementation and is intended to be removed once everyone is moved to
    the more modern V4 API. (Yes, we skipped V3)
    """

    def __init__(self, app, instance_keys, storage):
        self.app = app
        self._legacy_secscan_api = None

        validator = V2SecurityConfigValidator(
            app.config.get("FEATURE_SECURITY_SCANNER", False),
            app.config.get("SECURITY_SCANNER_ENDPOINT"),
        )
        if not validator.valid():
            logger.warning("Failed to validate security scanner V2 configuration")
            return

        url_scheme_and_hostname = URLSchemeAndHostname(
            app.config["PREFERRED_URL_SCHEME"], app.config["SERVER_HOSTNAME"]
        )

        self._legacy_secscan_api = SecurityScannerAPI(
            app.config,
            storage,
            app.config["SERVER_HOSTNAME"],
            app.config["HTTPCLIENT"],
            uri_creator=get_blob_download_uri_getter(
                app.test_request_context("/"), url_scheme_and_hostname
            ),
            instance_keys=instance_keys,
        )

        # NOTE: This import is in here because otherwise this class would depend upon app.
        # Its not great, but as this is intended to be legacy until its removed, its okay.
        from util.secscan.analyzer import LayerAnalyzer

        self._target_version = app.config.get("SECURITY_SCANNER_ENGINE_VERSION_TARGET", 3)
        self._analyzer = LayerAnalyzer(app.config, self._legacy_secscan_api)

    @property
    def legacy_api_handler(self):
        """
        Exposes the legacy security scan API for legacy workers that need it.
        """
        return self._legacy_secscan_api

    def register_model_cleanup_callbacks(self, data_model_config):
        if self._legacy_secscan_api is not None:
            data_model_config.register_image_cleanup_callback(
                self._legacy_secscan_api.cleanup_layers
            )

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
        status = registry_model.get_security_status(manifest_or_legacy_image)
        if status is None:
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.UNKNOWN_MANIFEST_OR_IMAGE
            )

        if status == SecurityScanStatus.FAILED:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.FAILED_TO_INDEX)

        if status == SecurityScanStatus.UNSUPPORTED:
            return SecurityInformationLookupResult.with_status(
                ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
            )

        if status == SecurityScanStatus.QUEUED:
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        assert status == SecurityScanStatus.SCANNED

        try:
            if include_vulnerabilities:
                data = self._legacy_secscan_api.get_layer_data(
                    manifest_or_legacy_image, include_vulnerabilities=True
                )
            else:
                data = self._legacy_secscan_api.get_layer_data(
                    manifest_or_legacy_image, include_features=True
                )
        except APIRequestFailure as arf:
            return SecurityInformationLookupResult.for_request_error(str(arf))

        if data is None:
            # If no data was found but we reached this point, then it indicates we have incorrect security
            # status for the manifest or legacy image. Mark the manifest or legacy image as unindexed
            # so it automatically gets re-indexed.
            if self.app.config.get("REGISTRY_STATE", "normal") == "normal":
                registry_model.reset_security_status(manifest_or_legacy_image)

            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        return SecurityInformationLookupResult.for_data(data)

    def _candidates_to_scan(self, start_token=None):
        target_version = self._target_version

        def batch_query():
            return get_images_eligible_for_scan(target_version)

        # Find the minimum ID.
        min_id = None
        if start_token is not None:
            min_id = start_token.min_id
        else:
            min_id = self.app.config.get("SECURITY_SCANNER_INDEXING_MIN_ID")
            if min_id is None:
                min_id = get_min_id_for_sec_scan(target_version)

        # Get the ID of the last image we can analyze. Will be None if there are no images in the
        # database.
        max_id = get_max_id_for_sec_scan()
        if max_id is None:
            return (None, None)

        if min_id is None or min_id > max_id:
            return (None, None)

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        # TODO: Once we have a clean shared NamedTuple for Images, send that to the secscan analyzer
        # rather than the database Image itself.
        iterator = yield_random_entries(
            batch_query, get_image_pk_field(), batch_size, max_id, min_id,
        )

        return (iterator, ScanToken(max_id + 1))

    def perform_indexing(self, start_token=None):
        """
        Performs indexing of the next set of unindexed manifests/images.

        If start_token is given, the indexing should resume from that point. Returns a new start
        index for the next iteration of indexing. The tokens returned and given are assumed to be
        opaque outside of this implementation and should not be relied upon by the caller to conform
        to any particular format.
        """
        # NOTE: This import is in here because otherwise this class would depend upon app.
        # Its not great, but as this is intended to be legacy until its removed, its okay.
        from util.secscan.analyzer import PreemptedException

        iterator, next_token = self._candidates_to_scan(start_token)
        if iterator is None:
            logger.debug("Found no additional images to scan")
            return None

        with UseThenDisconnect(self.app.config):
            for candidate, abt, num_remaining in iterator:
                try:
                    self._analyzer.analyze_recursively(candidate)
                except PreemptedException:
                    logger.info("Another worker pre-empted us for layer: %s", candidate.id)
                    abt.set()
                except APIRequestFailure:
                    logger.exception("Security scanner service unavailable")
                    return

                unscanned_images.set(num_remaining)

        return next_token
