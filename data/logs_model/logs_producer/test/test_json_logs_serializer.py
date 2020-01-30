# -*- coding: utf-8 -*-

import logging
import json
from datetime import datetime
import pytest

from data.logs_model.logs_producer.util import logs_json_serializer
from data.logs_model.elastic_logs import LogEntry


logger = logging.getLogger(__name__)


TEST_DATETIME = datetime.utcnow()

TEST_JSON_STRING = '{"a": "b", "c": "d"}'
TEST_JSON_STRING_WITH_UNICODE = '{"éëê": "îôû"}'

VALID_LOGENTRY = LogEntry(
    random_id="123-45", ip="0.0.0.0", metadata_json=TEST_JSON_STRING, datetime=TEST_DATETIME
)
VALID_LOGENTRY_WITH_UNICODE = LogEntry(
    random_id="123-45",
    ip="0.0.0.0",
    metadata_json=TEST_JSON_STRING_WITH_UNICODE,
    datetime=TEST_DATETIME,
)

VALID_LOGENTRY_EXPECTED_OUTPUT = (
    '{"datetime": "%s", "ip": "0.0.0.0", "metadata_json": "{\\"a\\": \\"b\\", \\"c\\": \\"d\\"}", "random_id": "123-45"}'
    % TEST_DATETIME.isoformat()
).encode("ascii")
VALID_LOGENTRY_WITH_UNICODE_EXPECTED_OUTPUT = (
    '{"datetime": "%s", "ip": "0.0.0.0", "metadata_json": "{\\"\\u00e9\\u00eb\\u00ea\\": \\"\\u00ee\\u00f4\\u00fb\\"}", "random_id": "123-45"}'
    % TEST_DATETIME.isoformat()
).encode("ascii")


@pytest.mark.parametrize(
    "is_valid, given_input, expected_output",
    [
        # Valid inputs
        pytest.param(True, VALID_LOGENTRY, VALID_LOGENTRY_EXPECTED_OUTPUT),
        # With unicode
        pytest.param(
            True, VALID_LOGENTRY_WITH_UNICODE, VALID_LOGENTRY_WITH_UNICODE_EXPECTED_OUTPUT
        ),
    ],
)
def test_logs_json_serializer(is_valid, given_input, expected_output):
    if not is_valid:
        with pytest.raises(ValueError) as ve:
            data = logs_json_serializer(given_input)
    else:
        data = logs_json_serializer(given_input, sort_keys=True)
        assert data == expected_output

    # Make sure the datetime was serialized in the correct ISO8601
    datetime_str = json.loads(data)["datetime"]
    assert datetime_str == TEST_DATETIME.isoformat()
