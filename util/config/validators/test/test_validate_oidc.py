import json
import pytest

from httmock import urlmatch, HTTMock

from config import build_requests_session
from oauth.oidc import OIDC_WELLKNOWN
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_oidc import OIDCLoginValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({"SOMETHING_LOGIN_CONFIG": {}}),
        ({"SOMETHING_LOGIN_CONFIG": {"OIDC_SERVER": "foo"}}),
        ({"SOMETHING_LOGIN_CONFIG": {"OIDC_SERVER": "foo", "CLIENT_ID": "foobar"}}),
        ({"SOMETHING_LOGIN_CONFIG": {"OIDC_SERVER": "foo", "CLIENT_SECRET": "foobar"}}),
    ],
)
def test_validate_invalid_oidc_login_config(unvalidated_config, app):
    validator = OIDCLoginValidator()

    with pytest.raises(ConfigValidationException):
        validator.validate(ValidatorContext(unvalidated_config))


def test_validate_oidc_login(app):
    url_hit = [False]

    @urlmatch(netloc=r"someserver", path=r"/\.well-known/openid-configuration")
    def handler(_, __):
        url_hit[0] = True
        data = {
            "token_endpoint": "foobar",
        }
        return {"status_code": 200, "content": json.dumps(data)}

    with HTTMock(handler):
        validator = OIDCLoginValidator()
        unvalidated_config = ValidatorContext(
            {
                "SOMETHING_LOGIN_CONFIG": {
                    "CLIENT_ID": "foo",
                    "CLIENT_SECRET": "bar",
                    "OIDC_SERVER": "http://someserver",
                    "DEBUGGING": True,  # Allows for HTTP.
                },
            }
        )
        unvalidated_config.http_client = build_requests_session()

        validator.validate(unvalidated_config)

    assert url_hit[0]
