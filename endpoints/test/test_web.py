import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import patch

from flask import url_for
from freezegun import freeze_time

from app import app as realapp
from endpoints.web import exportedlogs
from test.fixtures import *
from util.security.crypto import decrypt_string, encrypt_string


def test_exported_logs_are_served(app):
    """
    Verifies that we can serve the log file if proper token is provided.
    """
    payload = b'{"logs": []}'
    logfile = f"{uuid.uuid4()}-{uuid.uuid4()}"

    # create token
    secret_key = realapp.config["SECRET_KEY"]
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())

    token = encrypt_string(logfile, fernet_key)
    storage_config = {"local": ("LocalStorage", {"storage_path": "/tmp"})}

    # mutate storage configuration
    original = realapp.config.get("DISTRIBUTED_STORAGE_CONFIG")
    realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = storage_config

    try:
        with app.test_client() as cl:
            with patch("endpoints.web.storage") as mock_storage:
                mock_storage.preferred_locations = "local"
                mock_storage.exists.return_value = True
                mock_storage.stream_read_file.return_value = BytesIO(payload)

                resp = cl.get(f"/exportedlogs/{logfile}?token={token}")

        assert resp.status_code == 200
        assert resp.data == payload
    finally:
        realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = original


def test_exported_logs_should_fail_without_token(app):
    """
    Verifies that fetching of exported logs fail if there is no token provided.
    """
    payload = b'{"logs":[]}'
    logfile = f"{uuid.uuid4()}-{uuid.uuid4()}"

    storage_config = {"local": ("LocalStorage", {"storage_path": "/tmp"})}

    # mutate storage configuration
    original = realapp.config.get("DISTRIBUTED_STORAGE_CONFIG")
    realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = storage_config

    try:
        with app.test_client() as cl:
            with patch("endpoints.web.storage") as mock_storage:
                mock_storage.preferred_locations = "local"
                mock_storage.exists.return_value = True
                mock_storage.stream_read_file.return_value = BytesIO(payload)

                resp = cl.get(f"/exportedlogs/{logfile}")

        assert resp.status_code == 403
    finally:
        realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = original


# to do (potentially): Check path where a proper token has been provided but the file is no longer present.
# This path should never be hit and currently cannot be easily tested due to abort(404) handler which calls
# the rendering of the UI template when this the API is hit.


def test_exported_logs_properly_return_403_on_tampered_token(app):
    """
    Verifies that fetching of exported logs fail if a wrong or tampered token is provided.
    """

    payload = b'{"logs": []}'
    logfile = f"{uuid.uuid4()}-{uuid.uuid4()}"

    # create token
    secret_key = realapp.config["SECRET_KEY"]
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())

    real_token = encrypt_string(logfile, fernet_key)

    # create token with just one letter difference
    temp_secret_key = realapp.config["SECRET_KEY"] + "!"
    new_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(temp_secret_key.encode()).digest())
    fake_token = encrypt_string(logfile, new_fernet_key)

    # explicitly assert those are different
    assert real_token != fake_token

    storage_config = {"local": ("LocalStorage", {"storage_path": "/tmp"})}

    # mutate storage configuration
    original = realapp.config.get("DISTRIBUTED_STORAGE_CONFIG")
    realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = storage_config

    try:
        with app.test_client() as cl:
            with patch("endpoints.web.storage") as mock_storage:
                mock_storage.preferred_locations = "local"
                mock_storage.exists.return_value = True
                mock_storage.stream_read_file.return_value = BytesIO(payload)

                resp = cl.get(f"/exportedlogs/{logfile}?token={fake_token}")

        assert resp.status_code == 403

    finally:
        realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = original


def test_exported_logs_return_403_if_too_much_time_has_passed(app):
    """
    Verifies that serving of exported logs is invalid if the token has expired.
    """
    payload = b'{"logs": []}'
    logfile = f"{uuid.uuid4()}-{uuid.uuid4()}"

    # create token
    secret_key = realapp.config["SECRET_KEY"]
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())

    current_time = datetime.now(timezone.utc)
    with freeze_time(current_time):
        token = encrypt_string(logfile, fernet_key)

    storage_config = {"local": ("LocalStorage", {"storage_path": "/tmp"})}

    # mutate storage configuration
    original = realapp.config.get("DISTRIBUTED_STORAGE_CONFIG")
    realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = storage_config

    try:
        # forward time by 1 hour and 1 minute (default token expiration is 60 minutes)
        with freeze_time(current_time + timedelta(minutes=61)):
            with app.test_client() as cl:
                with patch("endpoints.web.storage") as mock_storage:
                    mock_storage.preferred_locations = "local"
                    mock_storage.exists.return_value = True
                    mock_storage.stream_read_file.return_value = BytesIO(payload)

                    resp = cl.get(f"/exportedlogs/{logfile}?token={token}")

        assert resp.status_code == 403

    finally:
        realapp.config["DISTRIBUTED_STORAGE_CONFIG"] = original
