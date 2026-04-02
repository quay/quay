import os
import time

import pytest
from mock import patch

from app import export_action_logs_queue
from endpoints.api.logs import ExportOrgLogs, OrgLogs, _validate_logs_arguments
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.fixture()
def _mock_dns_for_ssrf_validation():
    """
    Mock DNS resolution in the validation module so tests with
    hostnames don't fail due to DNS lookup failures.
    """
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0,
    reason="Queue code is very sensitive to times on MySQL, making this flaky",
)
@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
def test_export_logs(app):
    timecode = time.time()

    def get_time():
        return timecode - 2

    with patch("time.time", get_time):
        with client_with_identity("devtable", app) as cl:
            assert export_action_logs_queue.get() is None
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


@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
class TestExportLogsCallbackValidation:
    """Tests for callback URL validation in export logs."""

    def _export_body(self, callback_url):
        return {
            "callback_url": callback_url,
            "callback_email": "a@b.com",
        }

    def test_localhost_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("http://localhost/callback")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "Invalid callback URL" in resp.json.get("error_message", "")

    def test_loopback_ip_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("http://127.0.0.1/callback")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "Invalid callback URL" in resp.json.get("error_message", "")

    def test_private_ip_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("http://10.0.0.1/callback")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "Invalid callback URL" in resp.json.get("error_message", "")

    def test_metadata_ip_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("http://169.254.169.254/latest/meta-data")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "Invalid callback URL" in resp.json.get("error_message", "")

    def test_kubernetes_hostname_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("https://kubernetes.default.svc/callback")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "Invalid callback URL" in resp.json.get("error_message", "")

    def test_ftp_scheme_rejected(self, app):
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            body = self._export_body("ftp://registry.example.com/logs")
            resp = conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 400)
            assert "scheme" in resp.json.get("error_message", "").lower()

    def test_valid_url_accepted(self, app):
        timecode = time.time()

        def get_time():
            return timecode - 2

        with patch("time.time", get_time):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = self._export_body("https://example.com/callback")
                conduct_api_call(cl, ExportOrgLogs, "POST", params, body, 200)


def test_invalid_date_range(app):
    starttime = "02/02/2020"
    endtime = "01/01/2020"
    parsed_starttime, parsed_endtime = _validate_logs_arguments(starttime, endtime)
    assert parsed_starttime >= parsed_endtime

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrgLogs,
            "GET",
            {"orgname": "buynlarge", "starttime": starttime, "endtime": endtime},
            {},
            expected_code=400,
        )
