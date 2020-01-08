import pytest

from mock import patch
from tempfile import NamedTemporaryFile

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_ssl import SSLValidator, SSL_FILENAMES
from util.security.test.test_ssl_util import generate_test_cert
from util.bytes import Bytes

from test.fixtures import *
from app import config_provider


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"PREFERRED_URL_SCHEME": "http"}),
        ({"PREFERRED_URL_SCHEME": "https", "EXTERNAL_TLS_TERMINATION": True}),
    ],
)
def test_skip_validate_ssl(unvalidated_config, app):
    validator = SSLValidator()
    validator.validate(ValidatorContext(unvalidated_config))


@pytest.mark.parametrize(
    "cert, server_hostname, expected_error, error_message",
    [
        (
            ("invalidcert", "invalidkey"),
            "someserver",
            ConfigValidationException,
            "Could not load SSL certificate: no start line",
        ),
        (generate_test_cert(hostname="someserver"), "someserver", None, None),
        (
            generate_test_cert(hostname="invalidserver"),
            "someserver",
            ConfigValidationException,
            'Supported names "invalidserver" in SSL cert do not match server hostname "someserver"',
        ),
        (generate_test_cert(hostname="someserver"), "someserver:1234", None, None),
        (
            generate_test_cert(hostname="invalidserver"),
            "someserver:1234",
            ConfigValidationException,
            'Supported names "invalidserver" in SSL cert do not match server hostname "someserver"',
        ),
        (
            generate_test_cert(hostname="someserver:1234"),
            "someserver:1234",
            ConfigValidationException,
            'Supported names "someserver:1234" in SSL cert do not match server hostname "someserver"',
        ),
        (generate_test_cert(hostname="someserver:more"), "someserver:more", None, None),
        (generate_test_cert(hostname="someserver:more"), "someserver:more:1234", None, None),
    ],
)
def test_validate_ssl(cert, server_hostname, expected_error, error_message, app):
    with NamedTemporaryFile(delete=False) as cert_file:
        cert_file.write(Bytes.for_string_or_unicode(cert[0]).as_encoded_str())
        cert_file.seek(0)

        with NamedTemporaryFile(delete=False) as key_file:
            key_file.write(Bytes.for_string_or_unicode(cert[1]).as_encoded_str())
            key_file.seek(0)

        def return_true(filename):
            return True

        def get_volume_file(filename, mode="r"):
            if filename == SSL_FILENAMES[0]:
                return open(cert_file.name, mode=mode)

            if filename == SSL_FILENAMES[1]:
                return open(key_file.name, mode=mode)

            return None

        config = {
            "PREFERRED_URL_SCHEME": "https",
            "SERVER_HOSTNAME": server_hostname,
        }

        with patch("app.config_provider.volume_file_exists", return_true):
            with patch("app.config_provider.get_volume_file", get_volume_file):
                validator = SSLValidator()
                config = ValidatorContext(config)
                config.config_provider = config_provider

                if expected_error is not None:
                    with pytest.raises(expected_error) as ipe:
                        validator.validate(config)

                    assert str(ipe.value) == error_message
                else:
                    validator.validate(config)
