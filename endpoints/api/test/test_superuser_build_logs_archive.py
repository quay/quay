import gzip
import json
import logging
from io import BytesIO

import pytest
from mock import patch

from endpoints.api.superuser import SuperUserRepositoryBuildLogsArchive
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *

BUILD_UUID = "deadpork-dead-pork-dead-porkdeadpork"
ARCHIVED_LOGS = {"logs": [{"message": "Step 1/1 : FROM scratch"}]}
PAYLOAD = json.dumps(ARCHIVED_LOGS).encode("utf-8")


@pytest.mark.parametrize(
    "body",
    [
        # Object served as stored: gzip bytes.
        pytest.param(gzip.compress(PAYLOAD), id="gzip"),
        # Object served after decompressive transcoding (e.g. Google Cloud
        # Storage decodes Content-Encoding: gzip objects unless the client asks
        # for gzip), so the stream already holds the plain JSON.
        pytest.param(PAYLOAD, id="transcoded"),
    ],
)
def test_superuser_archived_build_logs(body, app, caplog):
    with patch(
        "endpoints.api.superuser.log_archive._storage.stream_read_file",
        return_value=BytesIO(body),
    ):
        with client_with_identity("devtable", app) as cl:
            with caplog.at_level(logging.WARNING, logger="endpoints.api.superuser"):
                resp = conduct_api_call(
                    cl,
                    SuperUserRepositoryBuildLogsArchive,
                    "GET",
                    {"build_uuid": BUILD_UUID},
                    expected_code=200,
                )
            assert json.loads(resp.get_data()) == ARCHIVED_LOGS

    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "endpoints.api.superuser"
    ]
    if body == PAYLOAD:
        assert [BUILD_UUID in r.getMessage() for r in warnings] == [True]
        assert "already decoded" in warnings[0].getMessage()
    else:
        assert warnings == []


def test_superuser_archived_build_logs_unrecognized(app, caplog):
    # Neither gzip nor JSON: a controlled error before any body bytes go out,
    # with the build uuid and the leading bytes logged.
    body = b"<html>not an archive</html>"
    with patch(
        "endpoints.api.superuser.log_archive._storage.stream_read_file",
        return_value=BytesIO(body),
    ):
        with client_with_identity("devtable", app) as cl:
            with caplog.at_level(logging.ERROR, logger="endpoints.api.superuser"):
                resp = conduct_api_call(
                    cl,
                    SuperUserRepositoryBuildLogsArchive,
                    "GET",
                    {"build_uuid": BUILD_UUID},
                    expected_code=520,
                )
            assert json.loads(resp.get_data())["detail"] == "Archived logs are unreadable"

    errors = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.ERROR and r.name == "endpoints.api.superuser"
    ]
    assert len(errors) == 1
    assert BUILD_UUID in errors[0]
    assert body[:32].hex() in errors[0]
