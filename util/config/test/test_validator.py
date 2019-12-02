import pytest

from util.config.validator import is_valid_config_upload_filename
from util.config.validator import CONFIG_FILENAMES, CONFIG_FILE_SUFFIXES


def test_valid_config_upload_filenames():
    for filename in CONFIG_FILENAMES:
        assert is_valid_config_upload_filename(filename)

    for suffix in CONFIG_FILE_SUFFIXES:
        assert is_valid_config_upload_filename("foo" + suffix)
        assert not is_valid_config_upload_filename(suffix + "foo")


@pytest.mark.parametrize(
    "filename, expect_valid",
    [
        ("", False),
        ("foo", False),
        ("config.yaml", False),
        ("ssl.cert", True),
        ("ssl.key", True),
        ("ssl.crt", False),
        ("foobar-cloudfront-signing-key.pem", True),
        ("foobaz-cloudfront-signing-key.pem", True),
        ("barbaz-cloudfront-signing-key.pem", True),
        ("barbaz-cloudfront-signing-key.pem.bak", False),
    ],
)
def test_is_valid_config_upload_filename(filename, expect_valid):
    assert is_valid_config_upload_filename(filename) == expect_valid
