import logging

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
from data.secscan_model.secscan_v4_model_v2 import V4SecurityScanner2

logger = logging.getLogger(__name__)


class SecurityScannerModelProxy(SecurityScannerInterface):
    def configure(self, app, instance_keys, storage):
        model_version = app.config.get("SECURITY_SCANNER_V4_MODEL_VERSION", 1)

        # V2 requires PostgreSQL 9.5+ or MySQL 8+ for SELECT FOR UPDATE SKIP LOCKED
        if model_version == 2:
            from sqlalchemy.engine.url import make_url

            db_uri = app.config.get("DB_URI", "")
            parsed_uri = make_url(db_uri)
            db_driver = parsed_uri.drivername

            # SQLite is not supported - hard block and fall back to V1
            if db_driver == "sqlite":
                logger.error(
                    "SECURITY_SCANNER_V4_MODEL_VERSION=2 requires PostgreSQL 9.5+ or MySQL 8+. "
                    "Detected database driver '%s'. Falling back to model version 1.",
                    db_driver,
                )
                model_version = 1

            # MySQL requires version 8+ for SKIP LOCKED support
            # Block unless explicitly confirmed via config flag
            elif db_driver.startswith("mysql"):
                mysql_confirmed = app.config.get(
                    "SECURITY_SCANNER_V4_MYSQL8_CONFIRMED", False
                )
                if not mysql_confirmed:
                    logger.error(
                        "SECURITY_SCANNER_V4_MODEL_VERSION=2 requires MySQL 8.0+ for SKIP LOCKED support. "
                        "MySQL 5.7 does not support SKIP LOCKED and will cause SQL errors. "
                        "Set SECURITY_SCANNER_V4_MYSQL8_CONFIRMED: true in config to confirm you are "
                        "running MySQL 8.0+. Falling back to model version 1."
                    )
                    model_version = 1
                else:
                    logger.info(
                        "MySQL 8.0+ confirmed via SECURITY_SCANNER_V4_MYSQL8_CONFIRMED. "
                        "Using V4SecurityScanner V2."
                    )

        try:
            if model_version == 2:
                self._model = V4SecurityScanner2(app, instance_keys, storage)
            else:
                self._model = V4SecurityScanner(app, instance_keys, storage)
        except InvalidConfigurationException:
            self._model = NoopV4SecurityScanner()

        logger.info("===============================")
        logger.info("Using secscan model v%s: `%s`", model_version, [self._model])
        logger.info("===============================")

        return self

    def perform_indexing(self, next_token=None, batch_size=None):
        # V4SecurityScanner2 doesn't use ScanToken (returns None)
        if next_token is not None and isinstance(self._model, V4SecurityScanner):
            assert isinstance(next_token, V4ScanToken)
            assert isinstance(next_token.min_id, int)

        return self._model.perform_indexing(next_token, batch_size)

    def perform_indexing_recent_manifests(self, batch_size=None):
        self._model.perform_indexing_recent_manifests(batch_size)

    def load_security_information(
        self, manifest_or_legacy_image, include_vulnerabilities, model_cache=None
    ):
        manifest = manifest_or_legacy_image.as_manifest()

        info = self._model.load_security_information(manifest, include_vulnerabilities, model_cache)
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
