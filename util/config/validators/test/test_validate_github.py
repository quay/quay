import pytest

from httmock import urlmatch, HTTMock

from config import build_requests_session
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_github import GitHubLoginValidator, GitHubTriggerValidator

from test.fixtures import *


@pytest.fixture(params=[GitHubLoginValidator, GitHubTriggerValidator])
def github_validator(request):
    return request.param


@pytest.mark.parametrize(
    "github_config",
    [
        ({}),
        ({"GITHUB_ENDPOINT": "foo"}),
        ({"GITHUB_ENDPOINT": "http://github.com"}),
        ({"GITHUB_ENDPOINT": "http://github.com", "CLIENT_ID": "foo"}),
        ({"GITHUB_ENDPOINT": "http://github.com", "CLIENT_SECRET": "foo"}),
        (
            {
                "GITHUB_ENDPOINT": "http://github.com",
                "CLIENT_ID": "foo",
                "CLIENT_SECRET": "foo",
                "ORG_RESTRICT": True,
            }
        ),
        (
            {
                "GITHUB_ENDPOINT": "http://github.com",
                "CLIENT_ID": "foo",
                "CLIENT_SECRET": "foo",
                "ORG_RESTRICT": True,
                "ALLOWED_ORGANIZATIONS": [],
            }
        ),
    ],
)
def test_validate_invalid_github_config(github_config, github_validator, app):
    with pytest.raises(ConfigValidationException):
        unvalidated_config = {}
        unvalidated_config[github_validator.config_key] = github_config
        github_validator.validate(ValidatorContext(unvalidated_config))


def test_validate_github(github_validator, app):
    url_hit = [False, False]

    @urlmatch(netloc=r"somehost")
    def handler(url, request):
        url_hit[0] = True
        return {"status_code": 200, "content": "", "headers": {"X-GitHub-Request-Id": "foo"}}

    @urlmatch(netloc=r"somehost", path=r"/api/v3/applications/foo/tokens/foo")
    def app_handler(url, request):
        url_hit[1] = True
        return {"status_code": 404, "content": "", "headers": {"X-GitHub-Request-Id": "foo"}}

    with HTTMock(app_handler, handler):
        unvalidated_config = ValidatorContext(
            {
                github_validator.config_key: {
                    "GITHUB_ENDPOINT": "http://somehost",
                    "CLIENT_ID": "foo",
                    "CLIENT_SECRET": "bar",
                },
            }
        )

        unvalidated_config.http_client = build_requests_session()
        github_validator.validate(unvalidated_config)

    assert url_hit[0]
    assert url_hit[1]
