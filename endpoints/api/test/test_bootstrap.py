import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app import app as real_app
from data import model
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _bootstrap_config(tmp_path, owner="devtable"):
    return {
        "FEATURE_PROGRAMMATIC_BOOTSTRAP": True,
        "SUPER_USERS": [owner],
        "BOOTSTRAP_TOKEN_OWNER": owner,
        "BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json"),
        "BOOTSTRAP_TOKEN_EXPIRATION": 3600,
        "BOOTSTRAP_TOKEN_SCOPE": "repo:read",
    }


def _create_bootstrap_token(config):
    owner = model.user.get_user(config["BOOTSTRAP_TOKEN_OWNER"])
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token_record, access_token = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read repo:write",
    )
    return owner, application, token_record, access_token


def _stored_access_token(config):
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        return json.load(f)["access_token"]


def _expired_time():
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)


def _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token):
    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_valid_token(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, _, access_token = _create_bootstrap_token(config)

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "rotated"}
    assert os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    new_access_token = _stored_access_token(config)
    assert new_access_token != access_token
    assert model.oauth.validate_bootstrap_token(new_access_token, config) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is None


def test_renew_removes_stale_bootstrap_tokens_for_canonical_app_only(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    owner, application, _, access_token = _create_bootstrap_token(config)
    stale_token, stale_access_token = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read",
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    other_owner = model.user.get_user("freshuser")
    other_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        other_owner,
    )
    other_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        other_application,
        other_owner,
        "repo:read",
    )

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200

    new_access_token = _stored_access_token(config)
    tokens = model.oauth.get_bootstrap_tokens(application)
    assert len(tokens) == 1
    assert model.oauth.validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    assert model.oauth.lookup_access_token_by_uuid(stale_token.uuid) is None
    assert model.oauth.validate_bootstrap_token(stale_access_token, config) is None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(other_token.uuid) is not None


def test_renew_file_write_fails_rolls_back_db_token_changes(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, old_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.db_transaction", lambda: model.db.atomic()),
        patch("endpoints.api.bootstrap.write_bootstrap_token", side_effect=OSError("boom")),
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert resp.get_json()["error_type"] == "token_rotation_failed"
    assert resp.get_json()["error_message"] == "Token rotation failed: could not write token"
    assert model.oauth.lookup_access_token_by_uuid(old_record.uuid) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_db_cleanup_failure_happens_before_file_write(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, old_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.db_transaction", lambda: model.db.atomic()),
        patch(
            "endpoints.api.bootstrap.delete_bootstrap_tokens",
            side_effect=RuntimeError("cleanup failed"),
        ),
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert resp.get_json()["error_type"] == "token_rotation_failed"
    assert resp.get_json()["error_message"] == "Token rotation failed: could not clean up tokens"
    mock_write_token.assert_not_called()
    assert model.oauth.lookup_access_token_by_uuid(old_record.uuid) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_revalidates_token_after_lock(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, token_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch(
            "endpoints.api.bootstrap.validate_bootstrap_token",
            side_effect=[token_record, None],
        ),
        patch("endpoints.api.bootstrap.lock_bootstrap_token_operation") as mock_lock,
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"
    mock_lock.assert_called_once_with()
    mock_write_token.assert_not_called()


def test_renew_expired_token_rejected_before_lock(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.lock_bootstrap_token_operation") as mock_lock,
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)
    mock_lock.assert_not_called()
    mock_write_token.assert_not_called()


def test_renew_without_bearer_reaches_handler_with_valid_csrf(app, initialized_db):
    with app.test_client() as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_without_auth_header_requires_csrf(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post("/api/v1/bootstrap/renew")

    assert resp.status_code == 403


def test_renew_basic_auth_requires_csrf(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )

    assert resp.status_code == 403


def test_renew_basic_auth_reaches_handler_with_valid_csrf(app, initialized_db):
    with app.test_client() as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={
                "Authorization": "Basic dGVzdDp0ZXN0",
                "X-CSRF-Token": "csrf-token",
            },
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_logged_in_session_without_bearer_uses_normal_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        resp = cl.post("/api/v1/bootstrap/renew")

    assert resp.status_code == 403


def test_renew_logged_in_session_without_bearer_reaches_handler_with_valid_csrf(
    app, initialized_db
):
    with client_with_identity("devtable", app) as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_logged_in_session_with_bearer_uses_normal_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer invalidtoken1234567890"},
        )

    assert resp.status_code == 403


def test_renew_logged_in_session_with_bearer_reaches_handler_with_valid_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={
                "Authorization": "Bearer invalidtoken1234567890",
                "X-CSRF-Token": "csrf-token",
            },
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_invalid_bearer_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer invalidtoken1234567890"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_empty_bearer_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer    "},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_non_bootstrap_bearer_token(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_application(owner, "regular-app", "", "")
    _, access_token = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 403
    assert resp.get_json()["error_type"] == "insufficient_scope"


def test_renew_expired_token_rejected_from_loopback(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_ipv6_loopback(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "::1"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_remote_addr(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejects_proxy_derived_loopback(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Forwarded-For": "127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_forwarded_loopback_unix_socket(
    app, initialized_db, tmp_path
):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Forwarded-For": "127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": ""},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejects_other_forwarding_headers(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Real-IP": "127.0.0.1",
                    "Forwarded": "for=127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_valid_token_from_remote_addr(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, _, access_token = _create_bootstrap_token(config)

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 200
