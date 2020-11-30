import pytest

from config import build_requests_session
from util.config import URLSchemeAndHostname
from util.config.validator import ValidatorContext
from util.config.validators.validate_secscan import SecurityScannerValidator
from util.secscan.fake import fake_security_scanner

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"DISTRIBUTED_STORAGE_PREFERENCE": []}),
    ],
)
def test_validate_noop(unvalidated_config, app):

    unvalidated_config = ValidatorContext(
        unvalidated_config,
        feature_sec_scanner=False,
        is_testing=True,
        http_client=build_requests_session(),
        url_scheme_and_hostname=URLSchemeAndHostname("http", "localhost:5000"),
    )

    SecurityScannerValidator.validate(unvalidated_config)


@pytest.mark.parametrize(
    "unvalidated_config, expected_error",
    [
        (
            {
                "TESTING": True,
                "DISTRIBUTED_STORAGE_PREFERENCE": [],
                "FEATURE_SECURITY_SCANNER": True,
                "SECURITY_SCANNER_ENDPOINT": "http://invalidhost",
            },
            Exception,
        ),
        (
            {
                "TESTING": True,
                "DISTRIBUTED_STORAGE_PREFERENCE": [],
                "FEATURE_SECURITY_SCANNER": True,
                "SECURITY_SCANNER_ENDPOINT": "http://fakesecurityscanner",
            },
            None,
        ),
    ],
)
def test_validate(unvalidated_config, expected_error, app):
    unvalidated_config = ValidatorContext(
        unvalidated_config,
        feature_sec_scanner=True,
        is_testing=True,
        http_client=build_requests_session(),
        url_scheme_and_hostname=URLSchemeAndHostname("http", "localhost:5000"),
    )

    with fake_security_scanner(hostname="fakesecurityscanner"):
        if expected_error is not None:
            with pytest.raises(expected_error):
                SecurityScannerValidator.validate(unvalidated_config)
        else:
            SecurityScannerValidator.validate(unvalidated_config)
