import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_apptokenauth import AppTokenAuthValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"AUTHENTICATION_TYPE": "AppToken"}),
        ({"AUTHENTICATION_TYPE": "AppToken", "FEATURE_APP_SPECIFIC_TOKENS": False}),
        (
            {
                "AUTHENTICATION_TYPE": "AppToken",
                "FEATURE_APP_SPECIFIC_TOKENS": True,
                "FEATURE_DIRECT_LOGIN": True,
            }
        ),
    ],
)
def test_validate_invalid_auth_config(unvalidated_config, app):
    validator = AppTokenAuthValidator()

    with pytest.raises(ConfigValidationException):
        validator.validate(ValidatorContext(unvalidated_config))


def test_validate_auth(app):
    config = ValidatorContext(
        {
            "AUTHENTICATION_TYPE": "AppToken",
            "FEATURE_APP_SPECIFIC_TOKENS": True,
            "FEATURE_DIRECT_LOGIN": False,
        }
    )

    validator = AppTokenAuthValidator()
    validator.validate(config)
