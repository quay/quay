import os
import time

from mock import patch

from app import export_action_logs_queue
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.logs import ExportOrgLogs
from endpoints.test.shared import client_with_identity

from test.fixtures import *


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0,
    reason="Queue code is very sensitive to times on MySQL, making this flaky",
)
def test_export_logs(client):
    with client_with_identity("devtable", client) as cl:
        assert export_action_logs_queue.get() is None

        timecode = time.time()

        def get_time():
            return timecode - 2

        with patch("time.time", get_time):
            # Call to export logs.
            body = {
                "callback_url": "http://some/url",
                "callback_email": "a@b.com",
            }

            conduct_api_call(
                cl, ExportOrgLogs, "POST", {"orgname": "buynlarge"}, body, expected_code=200
            )

            # Ensure the request was queued.
            assert export_action_logs_queue.get() is not None
