import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_access import AccessSettingsValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config, expected_exception",
    [
        ({}, None),
        ({"FEATURE_DIRECT_LOGIN": False}, ConfigValidationException),
        ({"FEATURE_DIRECT_LOGIN": False, "SOMETHING_LOGIN_CONFIG": {}}, None),
        ({"FEATURE_DIRECT_LOGIN": False, "FEATURE_GITHUB_LOGIN": True}, None),
        ({"FEATURE_DIRECT_LOGIN": False, "FEATURE_GOOGLE_LOGIN": True}, None),
        ({"FEATURE_USER_CREATION": True, "FEATURE_INVITE_ONLY_USER_CREATION": False}, None),
        ({"FEATURE_USER_CREATION": True, "FEATURE_INVITE_ONLY_USER_CREATION": True}, None),
        ({"FEATURE_INVITE_ONLY_USER_CREATION": True}, None),
        (
            {"FEATURE_USER_CREATION": False, "FEATURE_INVITE_ONLY_USER_CREATION": True},
            ConfigValidationException,
        ),
        ({"FEATURE_USER_CREATION": False, "FEATURE_INVITE_ONLY_USER_CREATION": False}, None),
    ],
)
def test_validate_invalid_oidc_login_config(unvalidated_config, expected_exception, app):
    validator = AccessSettingsValidator()

    if expected_exception is not None:
        with pytest.raises(expected_exception):
            validator.validate(ValidatorContext(unvalidated_config))
    else:
        validator.validate(ValidatorContext(unvalidated_config))
