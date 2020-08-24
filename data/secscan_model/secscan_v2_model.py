import logging

from collections import namedtuple

from prometheus_client import Gauge
from deprecated import deprecated

from data.secscan_model.interface import SecurityScannerInterface, InvalidConfigurationException
from data.secscan_model.datatypes import (
    ScanLookupStatus,
    SecurityInformationLookupResult,
    SecurityInformation,
    Layer,
    Feature,
    Vulnerability,
)

from data.registry_model import registry_model
from data.registry_model.datatypes import SecurityScanStatus

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
class NoopV2SecurityScanner(SecurityScannerInterface):
    """
    No-op implementation of the security scanner interface for Clair V2.
    """

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
        return None

    def perform_indexing(self, start_token=None):
        return None

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    def lookup_notification_page(self, notification_id, page_index=None):
        pass

    def process_notification_page(self, page_result):
        pass

    def mark_notification_handled(self, notification_id):
        pass

    @property
    def legacy_api_handler(self):
        return None


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
            msg = "Failed to validate security scanner V2 configuration"
            logger.warning(msg)
            raise InvalidConfigurationException(msg)

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

    def register_model_cleanup_callbacks(self, data_model_config):
        pass

    @property
    def legacy_api_handler(self):
        """
        Exposes the legacy security scan API for legacy workers that need it.
        """
        return self._legacy_secscan_api

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
            return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

        return SecurityInformationLookupResult.for_data(SecurityInformation.from_dict(data))

    def perform_indexing(self, start_token=None):
        """
        Performs indexing of the next set of unindexed manifests/images.
        NOTE: Raises `NotImplementedError` because indexing for v2 is not supported.
        """
        raise NotImplementedError("Unsupported for this security scanner version")

    def lookup_notification_page(self, notification_id, page_index=None):
        return None

    def process_notification_page(self, page_result):
        raise NotImplementedError("Unsupported for this security scanner version")

    def mark_notification_handled(self, notification_id):
        raise NotImplementedError("Unsupported for this security scanner version")
