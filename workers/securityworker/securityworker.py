import logging.config
import time

import features

from app import app, secscan_api
from workers.worker import Worker
from workers.securityworker import index_images
from util.secscan.api import SecurityConfigValidator
from util.secscan.analyzer import LayerAnalyzer
from util.log import logfile_path
from endpoints.v2 import v2_bp


logger = logging.getLogger(__name__)


DEFAULT_INDEXING_INTERVAL = 30


class SecurityWorker(Worker):
    def __init__(self):
        super(SecurityWorker, self).__init__()
        validator = SecurityConfigValidator(
            app.config.get("FEATURE_SECURITY_SCANNER", False),
            app.config.get("SECURITY_SCANNER_ENDPOINT"),
        )
        if not validator.valid():
            logger.warning("Failed to validate security scan configuration")
            return

        self._target_version = app.config.get("SECURITY_SCANNER_ENGINE_VERSION_TARGET", 3)
        self._analyzer = LayerAnalyzer(app.config, secscan_api)
        self._next_token = None

        interval = app.config.get("SECURITY_SCANNER_INDEXING_INTERVAL", DEFAULT_INDEXING_INTERVAL)
        self.add_operation(self._index_images, interval)

    def _index_images(self):
        self._next_token = index_images(self._target_version, self._analyzer, self._next_token)


if __name__ == "__main__":
    app.register_blueprint(v2_bp, url_prefix="/v2")

    if not features.SECURITY_SCANNER:
        logger.debug("Security scanner disabled; skipping SecurityWorker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = SecurityWorker()
    worker.start()
