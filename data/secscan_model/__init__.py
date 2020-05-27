import os
import logging
from collections import namedtuple

from data.secscan_model.secscan_v2_model import V2SecurityScanner, NoopV2SecurityScanner
from data.secscan_model.secscan_v4_model import V4SecurityScanner, NoopV4SecurityScanner
from data.secscan_model.interface import SecurityScannerInterface, InvalidConfigurationException
from data.database import Manifest
from data.registry_model.datatypes import Manifest as ManifestDataType


logger = logging.getLogger(__name__)


SplitScanToken = namedtuple("NextScanToken", ["version", "token"])


class SecurityScannerModelProxy(SecurityScannerInterface):
    def configure(self, app, instance_keys, storage):
        # TODO(alecmerdler): Just use `V4SecurityScanner` once Clair V2 is removed.
        try:
            self._model = V2SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._model = NoopV2SecurityScanner()

        try:
            self._v4_model = V4SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._v4_model = NoopV4SecurityScanner()

        self._v4_namespace_whitelist = app.config.get("SECURITY_SCANNER_V4_NAMESPACE_WHITELIST", [])

        logger.info("===============================")
        logger.info("Using split secscan model: `%s`", [self._model, self._v4_model])
        logger.info("v4 whitelist `%s`", self._v4_namespace_whitelist)
        logger.info("===============================")

        return self

    def perform_indexing(self, next_token=None):
        if next_token is None:
            return SplitScanToken("v4", self._v4_model.perform_indexing(None))

        if next_token.version == "v4" and next_token.token is not None:
            return SplitScanToken("v4", self._v4_model.perform_indexing(next_token.token))

        if next_token.version == "v4" and next_token.token is None:
            return SplitScanToken("v2", self._model.perform_indexing(None))

        if next_token.version == "v2" and next_token.token is not None:
            return SplitScanToken("v2", self._model.perform_indexing(next_token.token))

        if next_token.version == "v2" and next_token.token is None:
            return None

    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities):
        if isinstance(manifest_or_legacy_image, ManifestDataType):
            namespace = Manifest.get(
                manifest_or_legacy_image._db_id
            ).repository.namespace_user.username

            if namespace in self._v4_namespace_whitelist:
                return self._v4_model.load_security_information(
                    manifest_or_legacy_image, include_vulnerabilities
                )

        return self._model.load_security_information(
            manifest_or_legacy_image, include_vulnerabilities
        )

    def register_model_cleanup_callbacks(self, data_model_config):
        return self._model.register_model_cleanup_callbacks(data_model_config)

    @property
    def legacy_api_handler(self):
        return self._model.legacy_api_handler


secscan_model = SecurityScannerModelProxy()
