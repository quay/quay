import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_ldap import LDAPValidator
from util.morecollections import AttrDict

from test.test_ldap import mock_ldap

from test.fixtures import *
from app import config_provider


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"AUTHENTICATION_TYPE": "Database"}),
    ],
)
def test_validate_noop(unvalidated_config, app):
    config = ValidatorContext(unvalidated_config, config_provider=config_provider)
    LDAPValidator.validate(config)


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"AUTHENTICATION_TYPE": "LDAP"}),
        ({"AUTHENTICATION_TYPE": "LDAP", "LDAP_ADMIN_DN": "foo"}),
    ],
)
def test_invalid_config(unvalidated_config, app):
    with pytest.raises(ConfigValidationException):
        config = ValidatorContext(unvalidated_config, config_provider=config_provider)
        LDAPValidator.validate(config)


@pytest.mark.parametrize(
    "uri",
    [
        "foo",
        "http://foo",
        "ldap:foo",
    ],
)
def test_invalid_uri(uri, app):
    config = {}
    config["AUTHENTICATION_TYPE"] = "LDAP"
    config["LDAP_BASE_DN"] = ["dc=quay", "dc=io"]
    config["LDAP_ADMIN_DN"] = "uid=testy,ou=employees,dc=quay,dc=io"
    config["LDAP_ADMIN_PASSWD"] = "password"
    config["LDAP_USER_RDN"] = ["ou=employees"]
    config["LDAP_URI"] = uri

    with pytest.raises(ConfigValidationException):
        config = ValidatorContext(config, config_provider=config_provider)
        LDAPValidator.validate(config)


@pytest.mark.parametrize(
    "admin_dn, admin_passwd, user_rdn, expected_exception",
    [
        ("uid=testy,ou=employees,dc=quay,dc=io", "password", ["ou=employees"], None),
        ("uid=invalidadmindn", "password", ["ou=employees"], ConfigValidationException),
        (
            "uid=testy,ou=employees,dc=quay,dc=io",
            "invalid_password",
            ["ou=employees"],
            ConfigValidationException,
        ),
        (
            "uid=testy,ou=employees,dc=quay,dc=io",
            "password",
            ["ou=invalidgroup"],
            ConfigValidationException,
        ),
    ],
)
def test_validated_ldap(admin_dn, admin_passwd, user_rdn, expected_exception, app):
    config = {}
    config["AUTHENTICATION_TYPE"] = "LDAP"
    config["LDAP_BASE_DN"] = ["dc=quay", "dc=io"]
    config["LDAP_ADMIN_DN"] = admin_dn
    config["LDAP_ADMIN_PASSWD"] = admin_passwd
    config["LDAP_USER_RDN"] = user_rdn

    unvalidated_config = ValidatorContext(config, config_provider=config_provider)

    if expected_exception is not None:
        with pytest.raises(ConfigValidationException):
            with mock_ldap():
                LDAPValidator.validate(unvalidated_config)
    else:
        with mock_ldap():
            LDAPValidator.validate(unvalidated_config)
