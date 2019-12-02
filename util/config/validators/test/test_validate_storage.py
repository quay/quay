import pytest

from moto import mock_s3_deprecated as mock_s3

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_storage import StorageValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config, expected",
    [
        ({}, ConfigValidationException),
        ({"DISTRIBUTED_STORAGE_CONFIG": {}}, ConfigValidationException),
        ({"DISTRIBUTED_STORAGE_CONFIG": {"local": None}}, ConfigValidationException),
        ({"DISTRIBUTED_STORAGE_CONFIG": {"local": ["FakeStorage", {}]}}, None),
    ],
)
def test_validate_storage(unvalidated_config, expected, app):
    validator = StorageValidator()
    if expected is not None:
        with pytest.raises(expected):
            validator.validate(ValidatorContext(unvalidated_config))
    else:
        validator.validate(ValidatorContext(unvalidated_config))


def test_validate_s3_storage(app):
    validator = StorageValidator()
    with mock_s3():
        with pytest.raises(ConfigValidationException) as ipe:
            validator.validate(
                ValidatorContext(
                    {
                        "DISTRIBUTED_STORAGE_CONFIG": {
                            "default": (
                                "S3Storage",
                                {
                                    "s3_access_key": "invalid",
                                    "s3_secret_key": "invalid",
                                    "s3_bucket": "somebucket",
                                    "storage_path": "",
                                },
                            ),
                        }
                    }
                )
            )

        assert (
            str(ipe.value)
            == "Invalid storage configuration: default: S3ResponseError: 404 Not Found"
        )
