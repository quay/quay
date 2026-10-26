import base64
import json
import os
from unittest.mock import patch

import pytest
from httmock import HTTMock, urlmatch

from data import model
from data.database import db
from test.fixtures import *
from util.bootstrap_token import KubernetesTokenProvider


def _app_config(tmp_path, feature_enabled=True, superusers=None, owner="devtable"):
    if superusers is None:
        superusers = [owner] if owner is not None else []

    config = {
        "FEATURE_PROGRAMMATIC_BOOTSTRAP": feature_enabled,
        "SUPER_USERS": superusers,
        "BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json"),
        "BOOTSTRAP_TOKEN_EXPIRATION": 3600,
        "BOOTSTRAP_TOKEN_SCOPE": "repo:read repo:write",
        "REGISTRY_STATE": "normal",
    }
    if owner is not None:
        config["BOOTSTRAP_TOKEN_OWNER"] = owner
    return config


def _stored_access_token(config):
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        return json.load(f)["access_token"]


def _k8s_app_config(tmp_path, feature_enabled=True):
    config = _app_config(tmp_path, feature_enabled=feature_enabled)
    config.update(
        {
            "PROGRAMMATIC_TOKEN_K8S_SECRET": "bootstrap-token",
            "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
        }
    )
    return config


def _patch_k8s_service_account(tmp_path, monkeypatch):
    service_account_dir = tmp_path / "serviceaccount"
    service_account_dir.mkdir()
    token_path = service_account_dir / "token"
    namespace_path = service_account_dir / "namespace"
    ca_path = service_account_dir / "ca.crt"

    token_path.write_text("service-account-token\n")
    namespace_path.write_text("quay-enterprise\n")
    ca_path.write_text("ca")

    monkeypatch.setattr(KubernetesTokenProvider, "SA_TOKEN_PATH", str(token_path))
    monkeypatch.setattr(KubernetesTokenProvider, "SA_NAMESPACE_PATH", str(namespace_path))
    monkeypatch.setattr(KubernetesTokenProvider, "SA_CA_CERT_PATH", str(ca_path))
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    monkeypatch.setattr("util.bootstrap_token.KUBERNETES_API_HOST", "kubernetes.default.svc:443")


def _k8s_secret_handlers(secret):
    @urlmatch(
        netloc="kubernetes.default.svc:443",
        path="/api/v1/namespaces/quay-enterprise/secrets/bootstrap-token$",
        method="get",
    )
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(secret)}

    @urlmatch(
        netloc="kubernetes.default.svc:443",
        path="/api/v1/namespaces/quay-enterprise/secrets/bootstrap-token$",
        method="put",
    )
    def put_secret(_, request):
        body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
        secret.clear()
        secret.update(json.loads(body))
        return {"status_code": 200, "content": json.dumps(secret)}

    return get_secret, put_secret


def _k8s_secret_access_token(secret, key="token.json"):
    token_json = base64.b64decode(secret["data"][key]).decode("utf-8")
    return json.loads(token_json)["access_token"]


def test_readonly_registry_skips_bootstrap_token_setup(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    config["REGISTRY_STATE"] = "readonly"
    with (
        patch("boot.app") as mock_app,
        patch("boot._provision_bootstrap_token") as mock_provision,
        patch("boot._revoke_bootstrap_tokens") as mock_revoke,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_provision.assert_not_called()
    mock_revoke.assert_not_called()


def test_missing_bootstrap_feature_config_skips_bootstrap_token_setup(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    del config["FEATURE_PROGRAMMATIC_BOOTSTRAP"]
    with (
        patch("boot.app") as mock_app,
        patch("boot._provision_bootstrap_token") as mock_provision,
        patch("boot._revoke_bootstrap_tokens") as mock_revoke,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_provision.assert_not_called()
    mock_revoke.assert_not_called()


def test_provision_creates_bootstrap_token_and_file(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    with (
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_lock.assert_called_once_with()
    assert os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    owner = model.user.get_user("devtable")
    application = model.oauth.lookup_application_by_name(
        owner,
        model.oauth.get_bootstrap_app_name(),
    )
    tokens = model.oauth.get_bootstrap_tokens(application)
    assert len(tokens) == 1

    access_token = _stored_access_token(config)
    assert model.oauth.validate_bootstrap_token(access_token, config).id == tokens[0].id


def test_provision_creates_bootstrap_token_in_kubernetes_secret(
    initialized_db, tmp_path, monkeypatch
):
    from boot import setup_bootstrap_token

    _patch_k8s_service_account(tmp_path, monkeypatch)
    config = _k8s_app_config(tmp_path)
    secret = {"data": {}}
    get_secret, put_secret = _k8s_secret_handlers(secret)

    with (
        HTTMock(get_secret, put_secret),
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_lock.assert_called_once_with()
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    owner = model.user.get_user("devtable")
    application = model.oauth.lookup_application_by_name(
        owner, model.oauth.get_bootstrap_app_name()
    )
    tokens = model.oauth.get_bootstrap_tokens(application)
    access_token = _k8s_secret_access_token(secret)
    assert len(tokens) == 1
    assert model.oauth.validate_bootstrap_token(access_token, config).id == tokens[0].id


def test_provision_reuses_valid_stored_token(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    first_access_token = _stored_access_token(config)

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert _stored_access_token(config) == first_access_token
    owner = model.user.get_user("devtable")
    application = model.oauth.lookup_application_by_name(
        owner,
        model.oauth.get_bootstrap_app_name(),
    )
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1


def test_provision_selects_most_recent_duplicate_bootstrap_app(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    ignored_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    older_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    newer_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    ignored_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        ignored_application,
        owner,
        "repo:read",
    )
    old_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        older_application,
        owner,
        "repo:read",
    )
    keep_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        newer_application,
        owner,
        "repo:write",
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("not-json")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    newer_tokens = model.oauth.get_bootstrap_tokens(newer_application)
    assert [token.uuid for token in model.oauth.get_bootstrap_tokens(ignored_application)] == [
        ignored_token.uuid
    ]
    assert model.oauth.get_bootstrap_tokens(older_application) == []
    assert [token.uuid for token in newer_tokens] == [keep_token.uuid]
    assert model.oauth.lookup_access_token_by_uuid(ignored_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(old_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(keep_token.uuid) is not None
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        assert f.read() == "not-json"


def test_validate_bootstrap_token_accepts_only_canonical_bootstrap_application(
    initialized_db, tmp_path
):
    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    other_owner = model.user.get_user("freshuser")

    older_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    older_token, older_access_token = model.oauth.create_bootstrap_oauth_api_token(
        older_application,
        owner,
        "repo:read",
    )

    other_owner_application = model.oauth.create_application(
        other_owner,
        model.oauth.BOOTSTRAP_APP_NAME,
        "",
        "",
    )
    other_owner_token, other_owner_access_token = model.oauth.create_bootstrap_oauth_api_token(
        other_owner_application,
        other_owner,
        "repo:read",
    )

    newer_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    newer_token, newer_access_token = model.oauth.create_bootstrap_oauth_api_token(
        newer_application,
        owner,
        "repo:write",
    )

    assert model.oauth.validate_bootstrap_token(older_access_token, config) is None
    assert model.oauth.validate_bootstrap_token(other_owner_access_token, config) is None

    validated_token = model.oauth.validate_bootstrap_token(newer_access_token, config)
    assert validated_token is not None
    assert validated_token.uuid == newer_token.uuid
    assert model.oauth.lookup_access_token_by_uuid(older_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(other_owner_token.uuid) is not None


def test_provision_deletes_older_duplicate_bootstrap_apps_without_rewriting_file(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    older_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    newer_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    old_token, old_access_token = model.oauth.create_bootstrap_oauth_api_token(
        older_application,
        owner,
        "repo:read",
    )
    keep_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        newer_application,
        owner,
        "repo:write",
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        json.dump({"access_token": old_access_token}, f)

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert _stored_access_token(config) == old_access_token
    assert model.oauth.get_bootstrap_tokens(older_application) == []
    assert [token.uuid for token in model.oauth.get_bootstrap_tokens(newer_application)] == [
        keep_token.uuid
    ]
    assert model.oauth.lookup_access_token_by_uuid(old_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(keep_token.uuid) is not None


def test_provision_ignores_duplicate_app_with_non_bootstrap_tokens(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    safe_application = model.oauth.create_application(owner, model.oauth.BOOTSTRAP_APP_NAME, "", "")
    unsafe_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    old_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        safe_application,
        owner,
        "repo:read",
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        unsafe_application,
        "repo:write",
        "Bearer",
        3600,
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("not-json")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    safe_tokens = model.oauth.get_bootstrap_tokens(safe_application)
    assert [token.uuid for token in safe_tokens] == [old_token.uuid]
    assert [token.uuid for token in model.oauth.get_application_tokens(unsafe_application)] == [
        unmarked_token.uuid
    ]
    assert model.oauth.lookup_access_token_by_uuid(old_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is not None
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        assert f.read() == "not-json"


def test_provision_creates_new_bootstrap_app_when_named_apps_have_no_bootstrap_tokens(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    existing_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        existing_application,
        "repo:write",
        "Bearer",
        3600,
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    applications = model.oauth.lookup_applications_by_name(owner, model.oauth.BOOTSTRAP_APP_NAME)
    bootstrap_applications = [
        application for application in applications if model.oauth.get_bootstrap_tokens(application)
    ]
    assert len(applications) == 2
    assert len(bootstrap_applications) == 1
    assert bootstrap_applications[0].id != existing_application.id
    assert [token.uuid for token in model.oauth.get_application_tokens(existing_application)] == [
        unmarked_token.uuid
    ]
    assert model.oauth.validate_bootstrap_token(_stored_access_token(config), config) is not None


def test_provision_skips_file_write_when_bootstrap_token_exists(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    old_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    second_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:write")
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("not-json")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    tokens = model.oauth.get_bootstrap_tokens(application)
    assert {token.uuid for token in tokens} == {old_token.uuid, second_token.uuid}
    assert model.oauth.lookup_access_token_by_uuid(old_token.uuid) is not None
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        assert f.read() == "not-json"


def test_provision_deletes_previous_owner_bootstrap_application(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    previous_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    previous_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        previous_application,
        previous_owner,
        "repo:read",
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("not-json")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(previous_token.uuid) is None
    assert (
        model.oauth.lookup_applications_by_name(
            previous_owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        assert f.read() == "not-json"


def test_singleton_candidates_fetch_bootstrap_tokens_once_per_named_application(initialized_db):
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    canonical_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    stale_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    unmanaged_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    model.oauth.create_bootstrap_oauth_api_token(canonical_application, owner, "repo:read")
    model.oauth.create_bootstrap_oauth_api_token(stale_application, previous_owner, "repo:read")

    named_applications = model.oauth.lookup_bootstrap_named_applications()
    named_application_ids = {application.id for application in named_applications}

    with patch(
        "data.model.oauth.get_bootstrap_tokens",
        wraps=model.oauth.get_bootstrap_tokens,
    ) as mock_get_bootstrap_tokens:
        found_canonical, stale_applications = (
            model.oauth.get_singleton_bootstrap_application_candidates(owner)
        )

    assert found_canonical.id == canonical_application.id
    assert {application.id for application in stale_applications} == {stale_application.id}
    assert unmanaged_application.id not in {application.id for application in stale_applications}
    assert mock_get_bootstrap_tokens.call_count == len(named_applications)
    assert {
        call.args[0].id for call in mock_get_bootstrap_tokens.call_args_list
    } == named_application_ids
    assert all(call.kwargs == {} for call in mock_get_bootstrap_tokens.call_args_list)


def test_provision_creates_new_owner_token_before_deleting_previous_owner(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    previous_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    previous_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        previous_application,
        previous_owner,
        "repo:read",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert model.oauth.lookup_access_token_by_uuid(previous_token.uuid) is None
    assert (
        model.oauth.lookup_applications_by_name(
            previous_owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    new_token = model.oauth.validate_bootstrap_token(_stored_access_token(config), config)
    assert new_token is not None
    assert new_token.authorized_user_id == owner.id


def test_provision_skips_file_write_when_existing_bootstrap_token_is_expired(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    expired_token, expired_access_token = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read",
        expiration_seconds=-1,
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        json.dump({"access_token": expired_access_token}, f)

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    tokens = model.oauth.get_bootstrap_tokens(application)
    assert [token.uuid for token in tokens] == [expired_token.uuid]
    assert _stored_access_token(config) == expired_access_token
    assert model.oauth.lookup_access_token_by_uuid(expired_token.uuid) is not None


def test_provision_file_write_failure_rolls_back_new_db_token(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    previous_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    previous_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        previous_application,
        previous_owner,
        "repo:read",
    )

    with (
        patch("boot.app") as mock_app,
        # The PostgreSQL test fixture already runs each test inside a transaction.
        # Use atomic() so this rollback is scoped to the provisioning operation
        # without rolling back this test's setup rows.
        patch("boot.db_transaction", db.obj.atomic),
        patch("boot.write_bootstrap_token", side_effect=OSError("boom")),
    ):
        mock_app.config = config
        setup_bootstrap_token()

    applications = model.oauth.lookup_applications_by_name(
        owner,
        model.oauth.get_bootstrap_app_name(),
    )
    previous_owner_applications = model.oauth.lookup_applications_by_name(
        previous_owner,
        model.oauth.get_bootstrap_app_name(),
    )
    assert [existing_application.id for existing_application in applications] == [application.id]
    assert [existing_application.id for existing_application in previous_owner_applications] == [
        previous_application.id
    ]
    assert model.oauth.get_bootstrap_tokens(application) == []
    assert model.oauth.lookup_access_token_by_uuid(previous_token.uuid) is not None
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_provision_stale_cleanup_failure_skips_token_file_write(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    previous_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    previous_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        previous_application,
        previous_owner,
        "repo:read",
    )

    with (
        patch("boot.app") as mock_app,
        # The PostgreSQL test fixture already runs each test inside a transaction.
        # Use atomic() so this rollback is scoped to the provisioning operation
        # without rolling back this test's setup rows.
        patch("boot.db_transaction", db.obj.atomic),
        patch("boot.delete_applications", side_effect=RuntimeError("boom")),
        patch("boot.write_bootstrap_token") as mock_write_bootstrap_token,
        pytest.raises(RuntimeError, match="boom"),
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert mock_write_bootstrap_token.call_count == 0
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])
    assert (
        model.oauth.lookup_applications_by_name(owner, model.oauth.get_bootstrap_app_name()) == []
    )
    assert [
        application.id
        for application in model.oauth.lookup_applications_by_name(
            previous_owner,
            model.oauth.get_bootstrap_app_name(),
        )
    ] == [previous_application.id]
    assert model.oauth.lookup_access_token_by_uuid(previous_token.uuid) is not None


def test_provision_missing_owner_user_skips_provisioning(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, superusers=["missingowner"], owner="missingowner")
    with (
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])
    mock_lock.assert_not_called()


def test_provision_non_superuser_owner_skips_provisioning(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, superusers=[], owner="devtable")
    with (
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])
    mock_lock.assert_not_called()


def test_feature_disabled_deletes_kubernetes_secret_key(initialized_db, tmp_path, monkeypatch):
    from boot import setup_bootstrap_token

    _patch_k8s_service_account(tmp_path, monkeypatch)
    config = _k8s_app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    secret = {"data": {"token.json": "e30=", "other.json": "dmFsdWU="}}
    get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret), patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is None
    assert "token.json" not in secret["data"]
    assert secret["data"] == {"other.json": "dmFsdWU="}
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_feature_disabled_revokes_owner_bootstrap_applications(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    other_user = model.user.get_user("freshuser")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    owner_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    other_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        application, other_user, "repo:write"
    )
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("stale-token")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(owner_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(other_token.uuid) is None
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_feature_disabled_deletes_stale_token_file_without_bootstrap_application(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    with open(config["BOOTSTRAP_TOKEN_PATH"], "w") as f:
        f.write("stale-token")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_feature_disabled_ignores_missing_local_token_file(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])
    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is None


def test_feature_disabled_revokes_database_tokens_when_local_file_delete_fails(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")

    with (
        patch("boot.app") as mock_app,
        patch("boot.delete_bootstrap_token", side_effect=OSError("boom")) as mock_delete,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    mock_delete.assert_called_once_with(config)
    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is None


def test_feature_disabled_deletes_bootstrap_application_with_mixed_tokens(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    bootstrap_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read",
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:admin",
        "Bearer",
        3600,
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(bootstrap_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is None


def test_feature_disabled_ignores_application_without_bootstrap_tokens(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_application(
        owner,
        model.oauth.get_bootstrap_app_name(),
        "",
        "",
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:admin",
        "Bearer",
        3600,
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    existing_application_ids = []
    existing_applications = model.oauth.lookup_applications_by_name(
        owner,
        model.oauth.get_bootstrap_app_name(),
    )
    for existing_application in existing_applications:
        existing_application_ids.append(existing_application.id)

    unmarked_token_uuids = []
    for existing_token in model.oauth.get_application_tokens(application):
        unmarked_token_uuids.append(existing_token.uuid)

    assert existing_application_ids == [application.id]
    assert unmarked_token_uuids == [unmarked_token.uuid]


def test_feature_disabled_revokes_when_configured_owner_is_not_superuser(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False, superusers=[])
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")

    with (
        patch("boot.app") as mock_app,
        patch("boot.lock_bootstrap_token_operation") as mock_lock,
    ):
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is None
    mock_lock.assert_called_once_with()


def test_feature_disabled_revokes_all_bootstrap_applications_when_owner_changed(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path,
        feature_enabled=False,
        superusers=["devtable"],
        owner="devtable",
    )
    owner = model.user.get_user("devtable")
    previous_owner = model.user.get_user("freshuser")
    owner_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    previous_owner_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        previous_owner,
    )
    owner_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        owner_application,
        owner,
        "repo:read",
    )
    previous_owner_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        previous_owner_application,
        previous_owner,
        "repo:read",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert (
        model.oauth.lookup_applications_by_name(
            previous_owner,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(owner_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(previous_owner_token.uuid) is None


def test_feature_disabled_revokes_all_bootstrap_applications_when_owner_is_missing(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path,
        feature_enabled=False,
        superusers=["devtable", "missingowner"],
        owner="missingowner",
    )
    first_user = model.user.get_user("devtable")
    second_user = model.user.get_user("freshuser")
    first_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        first_user,
    )
    second_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        second_user,
    )
    first_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        first_application,
        first_user,
        "repo:read",
    )
    second_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        second_application,
        second_user,
        "repo:read",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            first_user,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert (
        model.oauth.lookup_applications_by_name(
            second_user,
            model.oauth.get_bootstrap_app_name(),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(first_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(second_token.uuid) is None


def test_feature_disabled_revokes_duplicate_bootstrap_applications(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    ignored_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    older_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    newer_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    ignored_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        ignored_application,
        owner,
        "repo:read",
    )
    older_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        older_application,
        owner,
        "repo:read",
    )
    newer_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        newer_application,
        owner,
        "repo:write",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    ignored_bootstrap_token_uuids = []
    for token in model.oauth.get_bootstrap_tokens(ignored_application):
        ignored_bootstrap_token_uuids.append(token.uuid)

    assert ignored_bootstrap_token_uuids == [ignored_token.uuid]
    assert model.oauth.lookup_applications_by_name(owner, model.oauth.BOOTSTRAP_APP_NAME) == []
    assert model.oauth.lookup_access_token_by_uuid(ignored_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(older_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(newer_token.uuid) is None
