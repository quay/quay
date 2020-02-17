import pytest

from httmock import urlmatch, HTTMock

from config import build_requests_session
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_google_login import GoogleLoginValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"GOOGLE_LOGIN_CONFIG": {}}),
        ({"GOOGLE_LOGIN_CONFIG": {"CLIENT_ID": "foo"}}),
        ({"GOOGLE_LOGIN_CONFIG": {"CLIENT_SECRET": "foo"}}),
    ],
)
def test_validate_invalid_google_login_config(unvalidated_config, app):
    validator = GoogleLoginValidator()

    with pytest.raises(ConfigValidationException):
        validator.validate(ValidatorContext(unvalidated_config))


def test_validate_google_login(app):
    url_hit = [False]

    @urlmatch(netloc=r"www.googleapis.com", path="/oauth2/v3/token")
    def handler(_, __):
        url_hit[0] = True
        return {"status_code": 200, "content": ""}

    validator = GoogleLoginValidator()

    with HTTMock(handler):
        unvalidated_config = ValidatorContext(
            {"GOOGLE_LOGIN_CONFIG": {"CLIENT_ID": "foo", "CLIENT_SECRET": "bar",},}
        )

        unvalidated_config.http_client = build_requests_session()

        validator.validate(unvalidated_config)

    assert url_hit[0]
