import os
import logging

from data.secscan_model.secscan_v2_model import V2SecurityScanner

logger = logging.getLogger(__name__)


class SecurityScannerModelProxy(object):
    def configure(self, app, instance_keys, storage):
        self._model = V2SecurityScanner(app, instance_keys, storage)

    def __getattr__(self, attr):
        return getattr(self._model, attr)


secscan_model = SecurityScannerModelProxy()
