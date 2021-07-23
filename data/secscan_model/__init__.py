import os
import logging
from collections import namedtuple

from data.secscan_model.secscan_v2_model import V2SecurityScanner, NoopV2SecurityScanner
from data.secscan_model.secscan_v4_model import (
    V4SecurityScanner,
    NoopV4SecurityScanner,
    ScanToken as V4ScanToken,
)
from data.secscan_model.interface import SecurityScannerInterface, InvalidConfigurationException
from data.secscan_model.datatypes import SecurityInformationLookupResult, ScanLookupStatus
from data.database import Manifest
from data.registry_model.datatypes import Manifest as ManifestDataType


logger = logging.getLogger(__name__)


class SecurityScannerModelProxy(SecurityScannerInterface):
    def configure(self, app, instance_keys, storage):
        try:
            self._model = V4SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._model = NoopV4SecurityScanner()

        try:
            self._legacy_model = V2SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._legacy_model = NoopV2SecurityScanner()

        logger.info("===============================")
        logger.info("Using split secscan model: `%s`", [self._legacy_model, self._model])
        logger.info("===============================")

        return self

    def perform_indexing(self, next_token=None):
        if next_token is not None:
            assert isinstance(next_token, V4ScanToken)
            assert isinstance(next_token.min_id, int)

        return self._model.perform_indexing(next_token)

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities):
        manifest = manifest_or_legacy_image.as_manifest()

        info = self._model.load_security_information(manifest, include_vulnerabilities)
        if info.status != ScanLookupStatus.NOT_YET_INDEXED:
            return info

        legacy_info = self._legacy_model.load_security_information(
            manifest_or_legacy_image, include_vulnerabilities
        )
        if (
            legacy_info.status != ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
            and legacy_info.status != ScanLookupStatus.COULD_NOT_LOAD
        ):
            return legacy_info

        return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

    def register_model_cleanup_callbacks(self, data_model_config):
        return self._model.register_model_cleanup_callbacks(data_model_config)

    @property
    def legacy_api_handler(self):
        return self._legacy_model.legacy_api_handler

    def lookup_notification_page(self, notification_id, page_index=None):
        return self._model.lookup_notification_page(notification_id, page_index)

    def process_notification_page(self, page_result):
        return self._model.process_notification_page(page_result)

    def mark_notification_handled(self, notification_id):
        return self._model.mark_notification_handled(notification_id)


secscan_model = SecurityScannerModelProxy()
