import pytest

from config import build_requests_session
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_jwt import JWTAuthValidator
from util.morecollections import AttrDict

from test.test_external_jwt_authn import fake_jwt

from test.fixtures import *
from app import config_provider


@pytest.mark.parametrize("unvalidated_config", [({}), ({"AUTHENTICATION_TYPE": "Database"}),])
def test_validate_noop(unvalidated_config, app):
    config = ValidatorContext(unvalidated_config)
    config.config_provider = config_provider
    JWTAuthValidator.validate(config)


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"AUTHENTICATION_TYPE": "JWT"}),
        ({"AUTHENTICATION_TYPE": "JWT", "JWT_AUTH_ISSUER": "foo"}),
        ({"AUTHENTICATION_TYPE": "JWT", "JWT_VERIFY_ENDPOINT": "foo"}),
    ],
)
def test_invalid_config(unvalidated_config, app):
    with pytest.raises(ConfigValidationException):
        config = ValidatorContext(unvalidated_config)
        config.config_provider = config_provider
        JWTAuthValidator.validate(config)


# TODO: fix these when re-adding jwt auth mechanism to jwt validators
@pytest.mark.skip(reason="No way of currently testing this")
@pytest.mark.parametrize(
    "username, password, expected_exception",
    [
        ("invaliduser", "invalidpass", ConfigValidationException),
        ("cool.user", "invalidpass", ConfigValidationException),
        ("invaliduser", "somepass", ConfigValidationException),
        ("cool.user", "password", None),
    ],
)
def test_validated_jwt(username, password, expected_exception, app):
    with fake_jwt() as jwt_auth:
        config = {}
        config["AUTHENTICATION_TYPE"] = "JWT"
        config["JWT_AUTH_ISSUER"] = jwt_auth.issuer
        config["JWT_VERIFY_ENDPOINT"] = jwt_auth.verify_url
        config["JWT_QUERY_ENDPOINT"] = jwt_auth.query_url
        config["JWT_GETUSER_ENDPOINT"] = jwt_auth.getuser_url

        unvalidated_config = ValidatorContext(config)
        unvalidated_config.user = AttrDict(dict(username=username))
        unvalidated_config.user_password = password
        unvalidated_config.config_provider = config_provider

        unvalidated_config.http_client = build_requests_session()

        if expected_exception is not None:
            with pytest.raises(ConfigValidationException):
                JWTAuthValidator.validate(
                    unvalidated_config, public_key_path=jwt_auth.public_key_path
                )
        else:
            JWTAuthValidator.validate(unvalidated_config, public_key_path=jwt_auth.public_key_path)
