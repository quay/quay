import base64
import json
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httmock import HTTMock, urlmatch

from data import model
from data.model.oauth import (
    BOOTSTRAP_APP_NAME,
    create_oauth_api_token,
    get_bootstrap_tokens,
    get_or_create_bootstrap_application,
    lookup_application_by_name,
    validate_bootstrap_token,
)
from test.fixtures import *
from util.bootstrap_token import KubernetesTokenProvider


def _app_config(tmp_path, feature_enabled=True, superusers=None, k8s_secret=None, owner="devtable"):
    if superusers is None:
        superusers = ["devtable"]
    config = {
        "FEATURE_PROGRAMMATIC_BOOTSTRAP": feature_enabled,
        "SUPER_USERS": superusers,
        "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
        "PROGRAMMATIC_TOKEN_EXPIRATION": 3600,
        "PROGRAMMATIC_TOKEN_SCOPE": "repo:read repo:write",
    }
    if owner is not None:
        config["BOOTSTRAP_TOKEN_OWNER"] = owner
    if k8s_secret:
        config["PROGRAMMATIC_TOKEN_K8S_SECRET"] = k8s_secret
        config["PROGRAMMATIC_TOKEN_K8S_KEY"] = "token.json"
        config["PROGRAMMATIC_TOKEN_K8S_NAMESPACE"] = "test-ns"
    return config


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


def test_readonly_registry_skips_bootstrap_token(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    config["REGISTRY_STATE"] = "readonly"
    with (
        patch("boot.app") as mock_app,
        patch("boot._provision_bootstrap_token") as mock_prov,
        patch("boot._revoke_bootstrap_tokens") as mock_revoke,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_prov.assert_not_called()
    mock_revoke.assert_not_called()


def test_provision_creates_token_and_file(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model"),
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_lock.assert_called_once_with()

    token_path = str(tmp_path / "token.json")
    assert os.path.exists(token_path)
    with open(token_path) as f:
        data = json.load(f)
    assert "access_token" in data
    assert len(data["access_token"]) == 40


def test_provision_uses_bootstrap_token_owner_independent_of_superuser_order(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    first_superuser = model.user.get_user("public")
    owner = model.user.get_user("devtable")
    config = _app_config(tmp_path, superusers=["public", "devtable"], owner="devtable")

    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model") as mock_logs,
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    application = lookup_application_by_name(owner, BOOTSTRAP_APP_NAME)
    assert application is not None
    assert lookup_application_by_name(first_superuser, BOOTSTRAP_APP_NAME) is None

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1
    token = tokens[0]
    assert token.authorized_user.username == "devtable"
    assert token.scope == config["PROGRAMMATIC_TOKEN_SCOPE"]

    with open(config["PROGRAMMATIC_TOKEN_PATH"]) as f:
        access_token = json.load(f)["access_token"]

    assert validate_bootstrap_token(access_token, config).id == token.id

    mock_logs.log_action.assert_called_once()
    args, kwargs = mock_logs.log_action.call_args
    assert args == ("create_oauth_api_token", "devtable")
    assert kwargs["metadata"] == {
        "auth_method": "system_startup",
        "oauth_token_uuid": token.uuid,
        "scope": config["PROGRAMMATIC_TOKEN_SCOPE"],
        "application_name": BOOTSTRAP_APP_NAME,
    }
    mock_logger.info.assert_called_with("Bootstrap token provisioned")


def test_provision_idempotent(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)

    with patch("boot.app") as mock_app, patch("boot.logs_model"):
        mock_app.config = config
        setup_bootstrap_token()

    with open(str(tmp_path / "token.json")) as f:
        first_token = json.load(f)["access_token"]

    with patch("boot.app") as mock_app, patch("boot.logs_model"):
        mock_app.config = config
        setup_bootstrap_token()

    with open(str(tmp_path / "token.json")) as f:
        second_token = json.load(f)["access_token"]

    assert first_token == second_token


def test_provision_replaces_stored_token_from_different_superuser(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    owner = model.user.get_user("devtable")
    other_superuser = model.user.get_user("public")
    other_application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, other_superuser)
    _, existing_access_token = create_oauth_api_token(
        other_application, other_superuser, "repo:read"
    )

    config = _app_config(tmp_path, superusers=["devtable", "public"], owner="devtable")
    with open(config["PROGRAMMATIC_TOKEN_PATH"], "w") as f:
        json.dump({"access_token": existing_access_token}, f)

    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    owner_application = lookup_application_by_name(owner, BOOTSTRAP_APP_NAME)
    assert owner_application is not None
    assert len(get_bootstrap_tokens(owner_application)) == 1
    assert len(get_bootstrap_tokens(other_application)) == 1
    assert validate_bootstrap_token(existing_access_token, config) is None

    with open(config["PROGRAMMATIC_TOKEN_PATH"]) as f:
        new_access_token = json.load(f)["access_token"]

    assert validate_bootstrap_token(new_access_token, config) is not None
    mock_logs.log_action.assert_called_once()


def test_provision_uses_configured_bootstrap_app_name(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    config = _app_config(tmp_path)
    config["BOOTSTRAP_APP_NAME"] = "custom-bootstrap-startup"

    with patch("boot.app") as mock_app, patch("boot.logs_model"):
        mock_app.config = config
        setup_bootstrap_token()

    application = lookup_application_by_name(user, "custom-bootstrap-startup")
    assert application is not None
    assert lookup_application_by_name(user, BOOTSTRAP_APP_NAME) is None

    with open(str(tmp_path / "token.json")) as f:
        access_token = json.load(f)["access_token"]

    assert validate_bootstrap_token(access_token, config) is not None

    with patch("boot.app") as mock_app, patch("boot.logs_model"):
        mock_app.config = config
        setup_bootstrap_token()

    with open(str(tmp_path / "token.json")) as f:
        second_access_token = json.load(f)["access_token"]

    assert second_access_token == access_token


def test_provision_recreates_missing_token_file(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, old_access_token = create_oauth_api_token(application, user, "repo:read")

    config = _app_config(tmp_path)
    with patch("boot.app") as mock_app, patch("boot.logs_model"):
        mock_app.config = config
        setup_bootstrap_token()

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1

    with open(str(tmp_path / "token.json")) as f:
        new_access_token = json.load(f)["access_token"]

    assert new_access_token != old_access_token
    assert validate_bootstrap_token(new_access_token, config) is not None


def test_provision_rewrites_invalid_stored_token(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, first_access_token = create_oauth_api_token(application, user, "repo:read")
    _, second_access_token = create_oauth_api_token(application, user, "repo:read")

    config = _app_config(tmp_path)
    with open(config["PROGRAMMATIC_TOKEN_PATH"], "w") as f:
        json.dump({"access_token": "not-a-valid-bootstrap-token"}, f)

    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model"),
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1

    with open(config["PROGRAMMATIC_TOKEN_PATH"]) as f:
        new_access_token = json.load(f)["access_token"]

    assert new_access_token not in {first_access_token, second_access_token}
    assert validate_bootstrap_token(first_access_token, config) is None
    assert validate_bootstrap_token(second_access_token, config) is None
    assert validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    mock_logger.warning.assert_any_call("Stored bootstrap token is invalid; rewriting it")
    mock_logger.info.assert_any_call(
        "Stored bootstrap token missing or invalid; replacing stale DB tokens"
    )


def test_provision_rewrites_when_stored_token_read_fails(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, old_access_token = create_oauth_api_token(application, user, "repo:read")

    config = _app_config(tmp_path)
    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model"),
        patch("boot.logger") as mock_logger,
        patch("boot.read_bootstrap_token", side_effect=OSError("unreadable")),
    ):
        mock_app.config = config
        setup_bootstrap_token()

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1

    with open(config["PROGRAMMATIC_TOKEN_PATH"]) as f:
        new_access_token = json.load(f)["access_token"]

    assert new_access_token != old_access_token
    assert validate_bootstrap_token(old_access_token, config) is None
    assert validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    mock_logger.exception.assert_any_call(
        "Could not read stored bootstrap token; attempting to rewrite it"
    )
    mock_logger.info.assert_any_call(
        "Stored bootstrap token missing or invalid; replacing stale DB tokens"
    )


def test_provision_removes_duplicate_tokens_when_stored_token_is_valid(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, access_token = create_oauth_api_token(application, user, "repo:read")
    create_oauth_api_token(application, user, "repo:read")

    config = _app_config(tmp_path)
    with open(config["PROGRAMMATIC_TOKEN_PATH"], "w") as f:
        json.dump({"access_token": access_token}, f)

    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1
    assert validate_bootstrap_token(access_token, config) is not None
    mock_logs.log_action.assert_not_called()


def test_provision_missing_bootstrap_token_owner_fails(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, owner=None)
    with patch("boot.app") as mock_app:
        mock_app.config = config
        with pytest.raises(Exception, match="BOOTSTRAP_TOKEN_OWNER must be set"):
            setup_bootstrap_token()

    assert not os.path.exists(str(tmp_path / "token.json"))


def test_provision_bootstrap_token_owner_must_be_superuser(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, superusers=[], owner="devtable")
    with patch("boot.app") as mock_app:
        mock_app.config = config
        with pytest.raises(Exception, match="BOOTSTRAP_TOKEN_OWNER must be listed in SUPER_USERS"):
            setup_bootstrap_token()

    assert not os.path.exists(str(tmp_path / "token.json"))


def test_provision_missing_bootstrap_token_owner_user_skips_provisioning(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, superusers=["nonexistentuser"], owner="nonexistentuser")
    with (
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
        patch("boot.logs_model") as mock_logs,
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert not os.path.exists(str(tmp_path / "token.json"))
    mock_lock.assert_not_called()
    mock_logs.log_action.assert_not_called()
    mock_logger.error.assert_called_once_with(
        "Bootstrap token owner '%s' was not found in the database; "
        "skipping bootstrap token provisioning",
        "nonexistentuser",
    )


def test_provision_file_write_fails_rolls_back(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    config["PROGRAMMATIC_TOKEN_PATH"] = "/proc/nonexistent/token.json"

    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model") as mock_logs,
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    tokens = get_bootstrap_tokens(app)
    assert len(tokens) == 0
    mock_logs.log_action.assert_not_called()
    mock_logger.exception.assert_any_call("Failed to write bootstrap token, rolled back")


def test_revoke_deletes_owner_tokens_only(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    create_oauth_api_token(app, user, "repo:read")
    assert len(get_bootstrap_tokens(app)) == 1

    other_user = model.user.get_user("public")
    other_app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, other_user)
    create_oauth_api_token(other_app, other_user, "repo:read")
    assert len(get_bootstrap_tokens(other_app)) == 1

    config = _app_config(
        tmp_path, feature_enabled=False, superusers=["devtable", "public"], owner="devtable"
    )
    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model") as mock_logs,
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert len(get_bootstrap_tokens(app)) == 0
    assert len(get_bootstrap_tokens(other_app)) == 1
    mock_logs.log_action.assert_called_once_with(
        "revoke_oauth_api_token",
        "devtable",
        metadata={
            "auth_method": "system_startup",
            "application_name": BOOTSTRAP_APP_NAME,
        },
    )
    mock_logger.info.assert_called_once_with("Bootstrap tokens revoked (feature disabled)")


def test_revoke_existing_application_without_tokens_noop(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    assert len(get_bootstrap_tokens(app)) == 0

    config = _app_config(tmp_path, feature_enabled=False)
    with (
        patch("boot.app") as mock_app,
        patch("boot.logs_model") as mock_logs,
        patch("boot.logger") as mock_logger,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert len(get_bootstrap_tokens(app)) == 0
    mock_logs.log_action.assert_not_called()
    mock_logger.info.assert_not_called()


def test_revoke_no_tokens_noop(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    mock_logs.log_action.assert_not_called()


def test_revoke_missing_bootstrap_token_owner_noop(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False, owner=None)
    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    mock_logs.log_action.assert_not_called()


def test_revoke_bootstrap_token_owner_not_superuser_noop(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False, superusers=[], owner="devtable")
    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    mock_logs.log_action.assert_not_called()


def test_revoke_missing_bootstrap_token_owner_user_noop(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path, feature_enabled=False, superusers=["missing-user"], owner="missing-user"
    )
    with patch("boot.app") as mock_app, patch("boot.logs_model") as mock_logs:
        mock_app.config = config
        setup_bootstrap_token()

    mock_logs.log_action.assert_not_called()


# ---------------------------------------------------------------------------
# K8s integration tests
# ---------------------------------------------------------------------------


def test_provision_with_k8s_secret(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    sa_token_path, sa_ns_path, sa_ca_path = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    secret_name = "bootstrap-token"
    config = _app_config(tmp_path, k8s_secret=secret_name)

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
        patch("boot.app") as mock_app,
        patch("boot.logs_model"),
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert "token.json" in put_body["data"]
    decoded = base64.b64decode(put_body["data"]["token.json"]).decode("utf-8")
    token_data = json.loads(decoded)
    assert "access_token" in token_data
    assert len(token_data["access_token"]) == 40

    token_path = str(tmp_path / "token.json")
    assert not os.path.exists(token_path)

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 1


def test_provision_k8s_fails_rolls_back_everything(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    sa_token_path, sa_ns_path, sa_ca_path = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    config = _app_config(tmp_path, k8s_secret="bootstrap-token")

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
        patch("boot.app") as mock_app,
        patch("boot.logs_model"),
        patch("boot.logger"),
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        mock_app.config = config
        setup_bootstrap_token()

    user = model.user.get_user("devtable")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    tokens = get_bootstrap_tokens(application)
    assert len(tokens) == 0
