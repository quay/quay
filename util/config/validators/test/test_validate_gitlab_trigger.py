import json
import pytest

from httmock import urlmatch, HTTMock

from config import build_requests_session
from util.config import URLSchemeAndHostname
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_gitlab_trigger import GitLabTriggerValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"GITLAB_TRIGGER_CONFIG": {"GITLAB_ENDPOINT": "foo"}}),
        ({"GITLAB_TRIGGER_CONFIG": {"GITLAB_ENDPOINT": "http://someendpoint", "CLIENT_ID": "foo"}}),
        (
            {
                "GITLAB_TRIGGER_CONFIG": {
                    "GITLAB_ENDPOINT": "http://someendpoint",
                    "CLIENT_SECRET": "foo",
                }
            }
        ),
    ],
)
def test_validate_invalid_gitlab_trigger_config(unvalidated_config, app):
    validator = GitLabTriggerValidator()

    with pytest.raises(ConfigValidationException):
        validator.validate(ValidatorContext(unvalidated_config))


def test_validate_gitlab_enterprise_trigger(app):
    url_hit = [False]

    @urlmatch(netloc=r"somegitlab", path="/oauth/token")
    def handler(_, __):
        url_hit[0] = True
        return {"status_code": 400, "content": json.dumps({"error": "invalid code"})}

    with HTTMock(handler):
        validator = GitLabTriggerValidator()

        url_scheme_and_hostname = URLSchemeAndHostname("http", "localhost:5000")

        unvalidated_config = ValidatorContext(
            {
                "GITLAB_TRIGGER_CONFIG": {
                    "GITLAB_ENDPOINT": "http://somegitlab",
                    "CLIENT_ID": "foo",
                    "CLIENT_SECRET": "bar",
                },
            },
            http_client=build_requests_session(),
            url_scheme_and_hostname=url_scheme_and_hostname,
        )

        validator.validate(unvalidated_config)

    assert url_hit[0]
