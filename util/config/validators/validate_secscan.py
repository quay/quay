import time

# from boot import setup_jwt_proxy
from util.secscan.api import SecurityScannerAPI
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

        api = SecurityScannerAPI(
            config,
            None,
            server_hostname,
            client=client,
            skip_validation=True,
            uri_creator=uri_creator,
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
                response = api.ping()
                last_exception = None
                if response.status_code == 200:
                    return
            except Exception as ex:
                last_exception = ex

            time.sleep(1)
            max_tries = max_tries - 1

        if last_exception is not None:
            message = str(last_exception)
            raise ConfigValidationException("Could not ping security scanner: %s" % message)
        else:
            message = "Expected 200 status code, got %s: %s" % (response.status_code, response.text)
            raise ConfigValidationException("Could not ping security scanner: %s" % message)
