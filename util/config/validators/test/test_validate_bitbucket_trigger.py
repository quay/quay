import pytest

from httmock import urlmatch, HTTMock

from util.config import URLSchemeAndHostname
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_bitbucket_trigger import BitbucketTriggerValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        (ValidatorContext({})),
        (ValidatorContext({"BITBUCKET_TRIGGER_CONFIG": {}})),
        (ValidatorContext({"BITBUCKET_TRIGGER_CONFIG": {"CONSUMER_KEY": "foo"}})),
        (ValidatorContext({"BITBUCKET_TRIGGER_CONFIG": {"CONSUMER_SECRET": "foo"}})),
    ],
)
def test_validate_invalid_bitbucket_trigger_config(unvalidated_config, app):
    validator = BitbucketTriggerValidator()

    with pytest.raises(ConfigValidationException):
        validator.validate(unvalidated_config)


def test_validate_bitbucket_trigger(app):
    url_hit = [False]

    @urlmatch(netloc=r"bitbucket.org")
    def handler(url, request):
        url_hit[0] = True
        return {
            "status_code": 200,
            "content": "oauth_token=foo&oauth_token_secret=bar",
        }

    with HTTMock(handler):
        validator = BitbucketTriggerValidator()

        url_scheme_and_hostname = URLSchemeAndHostname("http", "localhost:5000")
        unvalidated_config = ValidatorContext(
            {"BITBUCKET_TRIGGER_CONFIG": {"CONSUMER_KEY": "foo", "CONSUMER_SECRET": "bar",},},
            url_scheme_and_hostname=url_scheme_and_hostname,
        )

        validator.validate(unvalidated_config)

        assert url_hit[0]
