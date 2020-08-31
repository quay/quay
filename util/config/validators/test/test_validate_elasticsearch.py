import pytest

from config import build_requests_session
from httmock import urlmatch, HTTMock

from app import instance_keys
from data.logs_model.elastic_logs import INDEX_NAME_PREFIX
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_elasticsearch import ElasticsearchValidator

from test.fixtures import *


_TEST_ELASTICSEARCH_CONFIG = {
    "host": "somehost",
    "port": 6666,
    "access_key": "somekey",
    "secret_key": "somesecret",
    "index_prefix": "logentry_",
}


@pytest.mark.parametrize(
    "unvalidated_config,expected",
    [
        ({}, ConfigValidationException),
        (
            {
                "LOGS_MODEL": "not-elasticsearch",
                "LOGS_MODEL_CONFIG": {
                    "elasticsearch_config": _TEST_ELASTICSEARCH_CONFIG,
                },
            },
            ConfigValidationException,
        ),
        (
            {
                "LOGS_MODEL": "elasticsearch",
                "LOGS_MODEL_CONFIG": {
                    "elasticsearch_config": _TEST_ELASTICSEARCH_CONFIG,
                },
            },
            None,
        ),
    ],
)
def test_validate_elasticsearch(unvalidated_config, expected, app):
    validator = ElasticsearchValidator()
    path = unvalidated_config.get("index_prefix") or INDEX_NAME_PREFIX
    path = "/" + path + "*"
    unvalidated_config = ValidatorContext(unvalidated_config)

    @urlmatch(netloc=r"", path=path)
    def handler(url, request):
        return {"status_code": 200, "content": b"{}"}

    with HTTMock(handler):
        if expected is not None:
            with pytest.raises(expected):
                validator.validate(unvalidated_config)
        else:
            validator.validate(unvalidated_config)
