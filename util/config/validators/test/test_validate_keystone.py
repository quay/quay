import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_keystone import KeystoneValidator

from test.test_keystone_auth import fake_keystone

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"AUTHENTICATION_TYPE": "Database"}),
    ],
)
def test_validate_noop(unvalidated_config, app):
    KeystoneValidator.validate(ValidatorContext(unvalidated_config))


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"AUTHENTICATION_TYPE": "Keystone"}),
        ({"AUTHENTICATION_TYPE": "Keystone", "KEYSTONE_AUTH_URL": "foo"}),
        (
            {
                "AUTHENTICATION_TYPE": "Keystone",
                "KEYSTONE_AUTH_URL": "foo",
                "KEYSTONE_ADMIN_USERNAME": "bar",
            }
        ),
        (
            {
                "AUTHENTICATION_TYPE": "Keystone",
                "KEYSTONE_AUTH_URL": "foo",
                "KEYSTONE_ADMIN_USERNAME": "bar",
                "KEYSTONE_ADMIN_PASSWORD": "baz",
            }
        ),
    ],
)
def test_invalid_config(unvalidated_config, app):
    with pytest.raises(ConfigValidationException):
        KeystoneValidator.validate(ValidatorContext(unvalidated_config))


@pytest.mark.parametrize(
    "admin_tenant_id, expected_exception",
    [
        ("somegroupid", None),
        ("groupwithnousers", ConfigValidationException),
        ("somegroupid", None),
        ("groupwithnousers", ConfigValidationException),
    ],
)
def test_validated_keystone(admin_tenant_id, expected_exception, app):
    with fake_keystone(2) as keystone_auth:
        auth_url = keystone_auth.auth_url

        config = {}
        config["AUTHENTICATION_TYPE"] = "Keystone"
        config["KEYSTONE_AUTH_URL"] = auth_url
        config["KEYSTONE_ADMIN_USERNAME"] = "adminuser"
        config["KEYSTONE_ADMIN_PASSWORD"] = "adminpass"
        config["KEYSTONE_ADMIN_TENANT"] = admin_tenant_id

        unvalidated_config = ValidatorContext(config)

        if expected_exception is not None:
            with pytest.raises(ConfigValidationException):
                KeystoneValidator.validate(unvalidated_config)
        else:
            KeystoneValidator.validate(unvalidated_config)
