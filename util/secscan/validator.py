import logging


logger = logging.getLogger(__name__)


class SecurityConfigValidator(object):
    """ Helper class for validating the security scanner configuration. """

    def __init__(self, feature_sec_scan, sec_scan_endpoint):
        if not feature_sec_scan:
            return

        self._feature_sec_scan = feature_sec_scan
        self._sec_scan_endpoint = sec_scan_endpoint

    def valid(self):
        if not self._feature_sec_scan:
            return False

        if self._sec_scan_endpoint is None:
            logger.debug("Missing SECURITY_SCANNER_ENDPOINT configuration")
            return False

        endpoint = self._sec_scan_endpoint
        if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            logger.debug("SECURITY_SCANNER_ENDPOINT configuration must start with http or https")
            return False

        return True
