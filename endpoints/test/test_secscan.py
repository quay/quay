import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from flask import url_for
from freezegun import freeze_time

from app import app as realapp
from endpoints.secscan import secscan
from test.fixtures import *

FAKE_V4_PSK = base64.b64encode(b"faketoken").decode()

VALID_PAYLOAD = {
    "notification_id": "someuuid",
    "callback": "http://clair/notifier/api/v1/notification/someuuid",
}


@pytest.fixture()
def secscan_client(app):
    app.register_blueprint(secscan, url_prefix="/secscan")
    with app.test_client() as c:
        yield c


def _create_access_token_parameters():
    now = datetime.now(timezone.utc)

    with freeze_time(now):
        TOKEN_PARAMS = {
            "iss": "clair-notifier",
            "exp": int(now.timestamp()) + 300,
            "nbf": int(now.timestamp()),
            "iat": int(now.timestamp()),
        }

    return TOKEN_PARAMS


def _return_access_headers():
    token = jwt.encode(
        _create_access_token_parameters(), base64.b64decode(FAKE_V4_PSK), algorithm="HS256"
    )
    assert token

    headers = {
        "Authorization": "Bearer " + token,
    }

    return headers


def _post_notification(client, payload, headers=None):
    return client.post(
        "/secscan/notification",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers or {},
    )


class TestSecscanNotificationQueue:
    def test_has_valid_notification_enqueued(self, secscan_client):
        with patch("endpoints.secscan.secscan_notification_queue") as mock_queue:
            mock_queue.alive.return_value = False
            resp = _post_notification(
                secscan_client, VALID_PAYLOAD, headers=_return_access_headers()
            )

        assert resp.status_code == 200
        mock_queue.put.assert_called_once()

    def test_valid_notification_already_in_queue(self, secscan_client):
        with patch("endpoints.secscan.secscan_notification_queue") as mock_queue:
            mock_queue.alive.return_value = True
            resp = _post_notification(
                secscan_client, VALID_PAYLOAD, headers=_return_access_headers()
            )

        assert resp.status_code == 200
        mock_queue.put.assert_not_called()

    def test_missing_notification_id_returns_400(self, secscan_client):
        INVALID_PAYLOAD = {
            "callback": "http://clair/notifier/api/v1/notification/someuuid",
        }
        with patch("endpoints.secscan.secscan_notification_queue"):
            resp = _post_notification(
                secscan_client, INVALID_PAYLOAD, headers=_return_access_headers()
            )

        assert resp.status_code == 400

    def test_missing_callback_address_returns_400(self, secscan_client):
        INVALID_PAYLOAD = {
            "notification_id": str(uuid.uuid4()),
        }
        with patch("endpoints.secscan.secscan_notification_queue"):
            resp = _post_notification(
                secscan_client, INVALID_PAYLOAD, headers=_return_access_headers()
            )

        assert resp.status_code == 400

    def test_invalid_json_returns_400(self, secscan_client):
        INVALID_PAYLOAD = "Lorem ipsum...."
        resp = secscan_client.post(
            "/secscan/notification",
            data=INVALID_PAYLOAD,
            content_type="application/json",
            headers=_return_access_headers(),
        )

        assert resp.status_code == 400

    def test_non_object_json_returns_400(self, secscan_client):
        resp = secscan_client.post(
            "/secscan/notification",
            data="[1, 2, 3]",
            content_type="text/plain",
            headers=_return_access_headers(),
        )

        assert resp.status_code == 400


class TestSecscanJWTAuthentication:
    def test_valid_jwt_accepted(self, secscan_client):
        with patch.dict(realapp.config, {"SECURITY_SCANNER_V4_PSK": FAKE_V4_PSK}):
            with patch("endpoints.secscan.secscan_notification_queue") as mock_queue:
                mock_queue.alive.return_value = False
                resp = _post_notification(
                    secscan_client,
                    VALID_PAYLOAD,
                    headers=_return_access_headers(),
                )

            assert resp.status_code == 200

    def test_invalid_jwt_returns_401(self, secscan_client):
        WRONG_PSK = base64.b64encode(b"wrong key").decode()

        token = jwt.encode(
            _create_access_token_parameters(),
            WRONG_PSK,
            algorithm="HS256",
        )
        assert token

        headers = {
            "Authorization": "Bearer " + token,
        }

        with patch.dict(realapp.config, {"SECURITY_SCANNER_V4_PSK": FAKE_V4_PSK}):
            resp = _post_notification(
                secscan_client,
                VALID_PAYLOAD,
                headers=headers,
            )

        assert resp.status_code == 401

    def test_no_jwt_sent_to_secscan_returns_401(self, secscan_client):
        with patch.dict(realapp.config, {"SECURITY_SCANNER_V4_PSK": FAKE_V4_PSK}):
            resp = _post_notification(
                secscan_client,
                VALID_PAYLOAD,
                headers={},
            )

        assert resp.status_code == 401
