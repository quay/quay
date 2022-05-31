import time

# from boot import setup_jwt_proxy
from util.secscan.v4.api import ClairSecurityScannerAPI
from util.config.validators import BaseValidator, ConfigValidationException


class SecurityScannerValidator(BaseValidator):
    name = "security-scanner"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the configuration for talking to a Quay Security Scanner.
        """
        config = validator_context.config
        client = validator_context.http_client
        feature_sec_scanner = validator_context.feature_sec_scanner
        is_testing = validator_context.is_testing

        server_hostname = validator_context.url_scheme_and_hostname.hostname
        uri_creator = validator_context.uri_creator

        if not feature_sec_scanner:
            return

        api = ClairSecurityScannerAPI(
            config.get("SECURITY_SCANNER_V4_ENDPOINT"),
            client,
            None,
            jwt_psk=config.get("SECURITY_SCANNER_V4_PSK"),
        )

        # if not is_testing:
        # Generate a temporary Quay key to use for signing the outgoing requests.
        # setup_jwt_proxy()

        # We have to wait for JWT proxy to restart with the newly generated key.
        max_tries = 5
        response = None
        last_exception = None

        while max_tries > 0:
            try:
                response = api.state()
                last_exception = None
            except Exception as ex:
                last_exception = ex

            time.sleep(1)
            max_tries = max_tries - 1

        if last_exception is not None:
            message = str(last_exception)
            raise ConfigValidationException("Could not ping security scanner: %s" % message)
        elif not response.get("state"):
            message = "Invalid indexer state" % (response.status_code, response.text)
            raise ConfigValidationException("Could not ping security scanner: %s" % message)
