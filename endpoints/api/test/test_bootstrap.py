import base64
import json
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from httmock import HTTMock, urlmatch

from app import app as real_app
from data import model
from data.model.oauth import (
    BOOTSTRAP_APP_NAME,
    create_oauth_api_token,
    get_bootstrap_tokens,
    get_or_create_bootstrap_application,
    validate_bootstrap_token,
)
from endpoints.api.bootstrap import _is_loopback_remote_addr
from endpoints.test.shared import client_with_identity
from test.fixtures import *
from util.bootstrap_token import KubernetesTokenProvider


def _create_bootstrap_token(initialized_db):
    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    token_record, access_token = create_oauth_api_token(application, user, "repo:read repo:write")
    return user, application, token_record, access_token


def test_renew_valid_token(app, initialized_db, tmp_path):
    _, _, _, access_token = _create_bootstrap_token(initialized_db)

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "rotated"
    assert "access_token" not in data

    assert os.path.exists(token_path)
    with open(token_path) as f:
        file_data = json.load(f)
    assert len(file_data["access_token"]) == 40
    assert file_data["access_token"] != access_token


def test_renew_removes_stale_tokens_for_current_owner_only(app, initialized_db, tmp_path):
    user, application, _, access_token = _create_bootstrap_token(initialized_db)
    _, extra_access_token = create_oauth_api_token(application, user, "repo:read")

    other_superuser = model.user.get_user("public")
    other_application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, other_superuser)
    _, other_access_token = create_oauth_api_token(other_application, other_superuser, "repo:read")

    token_path = str(tmp_path / "token.json")
    config = {
        "PROGRAMMATIC_TOKEN_PATH": token_path,
        "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
        "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
        "SUPER_USERS": ["devtable", "public"],
        "BOOTSTRAP_TOKEN_OWNER": "devtable",
    }
    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200

    with open(token_path) as f:
        new_access_token = json.load(f)["access_token"]

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1
    assert validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    assert validate_bootstrap_token(access_token, config) is None
    assert validate_bootstrap_token(extra_access_token, config) is None
    assert validate_bootstrap_token(other_access_token, config) is None
    assert len(get_bootstrap_tokens(other_application)) == 1


def test_renew_revalidates_token_after_lock(app, initialized_db, tmp_path):
    _, _, token_record, access_token = _create_bootstrap_token(initialized_db)

    with (
        patch.dict(
            real_app.config,
            {
                "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
                "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
                "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
                "SUPER_USERS": ["devtable"],
                "BOOTSTRAP_TOKEN_OWNER": "devtable",
            },
        ),
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


def test_renew_uses_configured_bootstrap_app_name(app, initialized_db, tmp_path):
    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application("custom-bootstrap-renew", user)
    _, access_token = create_oauth_api_token(application, user, "repo:read repo:write")

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "BOOTSTRAP_APP_NAME": "custom-bootstrap-renew",
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    assert os.path.exists(token_path)


def test_renew_no_auth_header(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post("/api/v1/bootstrap/renew")

    # Without Bearer auth, CSRF protection rejects before our handler runs
    assert resp.status_code == 403


def test_renew_logged_in_session_without_bearer_returns_invalid_token(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_invalid_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer invalidtoken1234567890"},
        )

    assert resp.status_code == 401


def test_renew_non_bootstrap_token(app, initialized_db):
    user = model.user.get_user("devtable")
    application = model.oauth.create_application(user, "regular-app", "", "")
    _, access_token = create_oauth_api_token(application, user, "repo:read")

    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert resp.status_code == 403
    assert resp.get_json()["error_type"] == "insufficient_scope"


def test_renew_rejects_bootstrap_named_app_from_non_superuser_owner(app, initialized_db, tmp_path):
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, BOOTSTRAP_APP_NAME, "", "")
    _, access_token = create_oauth_api_token(application, user, "repo:read")

    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 403
    assert resp.get_json()["error_type"] == "insufficient_scope"


def test_renew_rejects_bootstrap_token_when_superusers_empty(app, initialized_db, tmp_path):
    _, _, _, access_token = _create_bootstrap_token(initialized_db)

    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": [],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 403
    assert resp.get_json()["error_type"] == "insufficient_scope"


def test_renew_file_write_fails_rolls_back(app, initialized_db):
    _, _, old_record, access_token = _create_bootstrap_token(initialized_db)

    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": "/proc/nonexistent/token.json",
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert (
        validate_bootstrap_token(
            access_token, {"SUPER_USERS": ["devtable"], "BOOTSTRAP_TOKEN_OWNER": "devtable"}
        )
        is not None
    )


def test_renew_expired_token_accepted_from_localhost(app, initialized_db, tmp_path):
    user, application, token_record, access_token = _create_bootstrap_token(initialized_db)
    token_record.expires_at = datetime.utcnow() - timedelta(days=1)
    token_record.save()

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rotated"


def test_renew_expired_token_rejected_from_remote_addr(app, initialized_db, tmp_path):
    _, _, token_record, access_token = _create_bootstrap_token(initialized_db)
    token_record.expires_at = datetime.utcnow() - timedelta(days=1)
    token_record.save()

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_expired_token_rejects_proxy_derived_loopback(app, initialized_db, tmp_path):
    _, _, token_record, access_token = _create_bootstrap_token(initialized_db)
    token_record.expires_at = datetime.utcnow() - timedelta(days=1)
    token_record.save()

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Forwarded-For": "127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_expired_token_accepted_from_ipv6_localhost(app, initialized_db, tmp_path):
    _, _, token_record, access_token = _create_bootstrap_token(initialized_db)
    token_record.expires_at = datetime.utcnow() - timedelta(days=1)
    token_record.save()

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "::1"},
            )

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rotated"


def test_renew_valid_token_from_remote_addr(app, initialized_db, tmp_path):
    _, _, _, access_token = _create_bootstrap_token(initialized_db)

    token_path = str(tmp_path / "token.json")
    with patch.dict(
        real_app.config,
        {
            "PROGRAMMATIC_TOKEN_PATH": token_path,
            "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
            "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
            "SUPER_USERS": ["devtable"],
            "BOOTSTRAP_TOKEN_OWNER": "devtable",
        },
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rotated"


# ---------------------------------------------------------------------------
# K8s integration tests
# ---------------------------------------------------------------------------


def _setup_sa_files(tmp_path):
    sa_token_path = str(tmp_path / "sa-token")
    sa_ns_path = str(tmp_path / "sa-namespace")
    sa_ca_path = str(tmp_path / "ca.crt")
    with open(sa_token_path, "w") as f:
        f.write(str(uuid.uuid4()))
    with open(sa_ns_path, "w") as f:
        f.write("test-ns")
    with open(sa_ca_path, "w") as f:
        f.write("dummy-ca-cert")
    return sa_token_path, sa_ns_path, sa_ca_path


def test_renew_with_k8s_secret(app, initialized_db, tmp_path):
    _, _, _, access_token = _create_bootstrap_token(initialized_db)

    sa_token_path, sa_ns_path, sa_ca_path = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    secret_name = "bootstrap-token"

    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}
    put_body = {}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="put")
    def put_secret(_, request):
        put_body.update(json.loads(request.body))
        return {"status_code": 200, "content": json.dumps(put_body)}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with (
        patch.dict(
            real_app.config,
            {
                "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
                "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
                "SUPER_USERS": ["devtable"],
                "BOOTSTRAP_TOKEN_OWNER": "devtable",
                "PROGRAMMATIC_TOKEN_K8S_SECRET": secret_name,
                "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
                "PROGRAMMATIC_TOKEN_K8S_NAMESPACE": "test-ns",
            },
        ),
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200

    assert "token.json" in put_body["data"]
    decoded = base64.b64decode(put_body["data"]["token.json"]).decode("utf-8")
    new_token = json.loads(decoded)["access_token"]
    assert len(new_token) == 40
    assert new_token != access_token


def test_renew_k8s_fails_rolls_back(app, initialized_db, tmp_path):
    _, _, old_record, access_token = _create_bootstrap_token(initialized_db)

    sa_token_path, sa_ns_path, sa_ca_path = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    token_path = str(tmp_path / "token.json")

    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="put")
    def put_secret(_, __):
        return {"status_code": 500, "content": "internal server error"}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with (
        patch.dict(
            real_app.config,
            {
                "PROGRAMMATIC_TOKEN_PATH": token_path,
                "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
                "PROGRAMMATIC_TOKEN_SCOPE": "repo:read",
                "SUPER_USERS": ["devtable"],
                "BOOTSTRAP_TOKEN_OWNER": "devtable",
                "PROGRAMMATIC_TOKEN_K8S_SECRET": "bootstrap-token",
                "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
                "PROGRAMMATIC_TOKEN_K8S_NAMESPACE": "test-ns",
            },
        ),
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert (
        validate_bootstrap_token(
            access_token, {"SUPER_USERS": ["devtable"], "BOOTSTRAP_TOKEN_OWNER": "devtable"}
        )
        is not None
    )


def test_loopback_remote_addr_helper_handles_empty_invalid_and_ipv4_mapped():
    assert _is_loopback_remote_addr(None) is False
    assert _is_loopback_remote_addr("") is False
    assert _is_loopback_remote_addr("not-an-ip") is False
    assert _is_loopback_remote_addr("::ffff:127.0.0.1") is True
    assert _is_loopback_remote_addr("::ffff:203.0.113.50") is False


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


def test_renew_empty_bearer_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer    "},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"
