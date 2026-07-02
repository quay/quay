import json
import os
from unittest.mock import patch

from data import model
from data.database import db
from test.fixtures import *


def _app_config(tmp_path, feature_enabled=True, superusers=None, owner="devtable", app_name=None):
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
    if app_name is not None:
        config["BOOTSTRAP_APP_NAME"] = app_name
    return config


def _stored_access_token(config):
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        return json.load(f)["access_token"]


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
        model.oauth.get_bootstrap_app_name(config),
    )
    tokens = model.oauth.get_bootstrap_tokens(application)
    assert len(tokens) == 1

    access_token = _stored_access_token(config)
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
        model.oauth.get_bootstrap_app_name(config),
    )
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1


def test_provision_selects_most_recent_duplicate_bootstrap_app(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, app_name="custom-bootstrap")
    owner = model.user.get_user("devtable")
    default_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    older_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    newer_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    default_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        default_application,
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
    assert [token.uuid for token in model.oauth.get_bootstrap_tokens(default_application)] == [
        default_token.uuid
    ]
    assert model.oauth.get_bootstrap_tokens(older_application) == []
    assert [token.uuid for token in newer_tokens] == [keep_token.uuid]
    assert model.oauth.lookup_access_token_by_uuid(default_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(old_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(keep_token.uuid) is not None
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        assert f.read() == "not-json"


def test_validate_bootstrap_token_accepts_only_canonical_bootstrap_application(
    initialized_db, tmp_path
):
    config = _app_config(tmp_path, app_name="custom-bootstrap")
    owner = model.user.get_user("devtable")
    other_owner = model.user.get_user("freshuser")

    older_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    older_token, older_access_token = model.oauth.create_bootstrap_oauth_api_token(
        older_application,
        owner,
        "repo:read",
    )

    other_owner_application = model.oauth.create_application(
        other_owner,
        "custom-bootstrap",
        "",
        "",
    )
    other_owner_token, other_owner_access_token = model.oauth.create_bootstrap_oauth_api_token(
        other_owner_application,
        other_owner,
        "repo:read",
    )

    newer_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
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

    config = _app_config(tmp_path, app_name="custom-bootstrap")
    owner = model.user.get_user("devtable")
    older_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    newer_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
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

    config = _app_config(tmp_path, app_name="custom-bootstrap")
    owner = model.user.get_user("devtable")
    safe_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    unsafe_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
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

    config = _app_config(tmp_path, app_name="custom-bootstrap")
    owner = model.user.get_user("devtable")
    existing_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
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

    applications = model.oauth.lookup_applications_by_name(owner, "custom-bootstrap")
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
        model.oauth.get_bootstrap_app_name(config),
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


def test_provision_skips_file_write_when_existing_bootstrap_token_is_expired(
    initialized_db, tmp_path
):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
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
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
        owner,
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
        model.oauth.get_bootstrap_app_name(config),
    )
    assert [existing_application.id for existing_application in applications] == [application.id]
    assert model.oauth.get_bootstrap_tokens(application) == []
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


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


def test_feature_disabled_revokes_owner_bootstrap_applications(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(tmp_path, feature_enabled=False)
    owner = model.user.get_user("devtable")
    other_user = model.user.get_user("freshuser")
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
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
            model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
            model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
        model.oauth.get_bootstrap_app_name(config),
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
            model.oauth.get_bootstrap_app_name(config),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(token.uuid) is None
    mock_lock.assert_called_once_with()


def test_feature_disabled_uses_configured_owner_when_present(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path,
        feature_enabled=False,
        superusers=["devtable", "freshuser"],
        owner="devtable",
    )
    owner = model.user.get_user("devtable")
    other_super_user = model.user.get_user("freshuser")
    owner_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
        owner,
    )
    other_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
        other_super_user,
    )
    owner_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        owner_application,
        owner,
        "repo:read",
    )
    other_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        other_application,
        other_super_user,
        "repo:read",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            owner,
            model.oauth.get_bootstrap_app_name(config),
        )
        == []
    )
    other_super_user_application_ids = []
    other_super_user_applications = model.oauth.lookup_applications_by_name(
        other_super_user,
        model.oauth.get_bootstrap_app_name(config),
    )
    for existing_application in other_super_user_applications:
        other_super_user_application_ids.append(existing_application.id)

    assert other_super_user_application_ids == [other_application.id]
    assert model.oauth.lookup_access_token_by_uuid(owner_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(other_token.uuid) is not None


def test_feature_disabled_falls_back_to_superusers_when_owner_is_missing(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path,
        feature_enabled=False,
        superusers=["devtable", "freshuser", "missingowner"],
        owner="missingowner",
    )
    first_super_user = model.user.get_user("devtable")
    second_super_user = model.user.get_user("freshuser")
    first_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
        first_super_user,
    )
    second_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(config),
        second_super_user,
    )
    first_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        first_application,
        first_super_user,
        "repo:read",
    )
    second_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        second_application,
        second_super_user,
        "repo:read",
    )

    with patch("boot.app") as mock_app:
        mock_app.config = config
        setup_bootstrap_token()

    assert (
        model.oauth.lookup_applications_by_name(
            first_super_user,
            model.oauth.get_bootstrap_app_name(config),
        )
        == []
    )
    assert (
        model.oauth.lookup_applications_by_name(
            second_super_user,
            model.oauth.get_bootstrap_app_name(config),
        )
        == []
    )
    assert model.oauth.lookup_access_token_by_uuid(first_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(second_token.uuid) is None


def test_feature_disabled_revokes_duplicate_bootstrap_applications(initialized_db, tmp_path):
    from boot import setup_bootstrap_token

    config = _app_config(
        tmp_path,
        feature_enabled=False,
        app_name="custom-bootstrap",
    )
    owner = model.user.get_user("devtable")
    default_application = model.oauth.create_application(
        owner, model.oauth.BOOTSTRAP_APP_NAME, "", ""
    )
    older_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    newer_application = model.oauth.create_application(owner, "custom-bootstrap", "", "")
    default_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        default_application,
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

    default_bootstrap_token_uuids = []
    for token in model.oauth.get_bootstrap_tokens(default_application):
        default_bootstrap_token_uuids.append(token.uuid)

    assert default_bootstrap_token_uuids == [default_token.uuid]
    assert model.oauth.lookup_applications_by_name(owner, "custom-bootstrap") == []
    assert model.oauth.lookup_access_token_by_uuid(default_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(older_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(newer_token.uuid) is None
