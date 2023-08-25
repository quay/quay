import logging
import os
from collections import namedtuple

from data.database import Manifest
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.secscan_model.datatypes import (
    ScanLookupStatus,
    SecurityInformationLookupResult,
)
from data.secscan_model.interface import (
    InvalidConfigurationException,
    SecurityScannerInterface,
)
from data.secscan_model.secscan_v4_model import NoopV4SecurityScanner
from data.secscan_model.secscan_v4_model import ScanToken as V4ScanToken
from data.secscan_model.secscan_v4_model import V4SecurityScanner

logger = logging.getLogger(__name__)


class SecurityScannerModelProxy(SecurityScannerInterface):
    def configure(self, app, instance_keys, storage):
        try:
            self._model = V4SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._model = NoopV4SecurityScanner()

        logger.info("===============================")
        logger.info("Using split secscan model: `%s`", [self._model])
        logger.info("===============================")

        return self

    def perform_indexing(self, next_token=None, batch_size=None):
        if next_token is not None:
            assert isinstance(next_token, V4ScanToken)
            assert isinstance(next_token.min_id, int)

        return self._model.perform_indexing(next_token, batch_size)

    def perform_indexing_recent_manifests(self, batch_size=None):
        self._model.perform_indexing_recent_manifests(batch_size)

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities):
        manifest = manifest_or_legacy_image.as_manifest()

        info = self._model.load_security_information(manifest, include_vulnerabilities)
        if info.status != ScanLookupStatus.NOT_YET_INDEXED:
            return info

        return SecurityInformationLookupResult.with_status(ScanLookupStatus.NOT_YET_INDEXED)

    def register_model_cleanup_callbacks(self, data_model_config):
        return self._model.register_model_cleanup_callbacks(data_model_config)

    @property
    def legacy_api_handler(self):
        raise NotImplementedError

    def lookup_notification_page(self, notification_id, page_index=None):
        return self._model.lookup_notification_page(notification_id, page_index)

    def process_notification_page(self, page_result):
        return self._model.process_notification_page(page_result)

    def mark_notification_handled(self, notification_id):
        return self._model.mark_notification_handled(notification_id)

    def garbage_collect_manifest_report(self, manifest_digest):
        return self._model.garbage_collect_manifest_report(manifest_digest)


secscan_model = SecurityScannerModelProxy()
