import gzip
import json
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
def test_superuser_archived_build_logs(body, app):
    with patch(
        "endpoints.api.superuser.log_archive._storage.stream_read_file",
        return_value=BytesIO(body),
    ):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                SuperUserRepositoryBuildLogsArchive,
                "GET",
                {"build_uuid": BUILD_UUID},
                expected_code=200,
            )
            assert json.loads(resp.get_data()) == ARCHIVED_LOGS
