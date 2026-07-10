from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from auth import scopes
from data import model
from data.database import User
from data.model import oauth as oauth_model
from data.model.oauth import (
    DEFAULT_TOKEN_EXPIRATION_SECONDS,
    MAX_TOKEN_DISPLAY_NAME_LENGTH,
)
from endpoints.api.organization_application_tokens import (
    MINTABLE_SCOPE_PERMISSION_FACTORIES,
    OrganizationApplicationToken,
    OrganizationApplicationTokens,
    _can_mint_scope,
    token_view,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _setup_app(orgname="buynlarge", app_name=None):
    org = model.organization.get_organization(orgname)
    application = oauth_model.create_application(
        org,
        app_name or "token-lifecycle-%s" % uuid4().hex,
        "",
        "",
    )
    return org, application


def test_create_token_returns_secret_once_and_list_omits_secret(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "  Frontend token  ", "scope": "repo:read,repo:write"},
            200,
        ).json

        assert created["token"]
        assert created["name"] == "Frontend token"
        assert created["scope"] == "repo:read repo:write"
        assert created["uuid"]
        assert created["expires_at"]
        assert created["created"]

        listed = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

    listed_token = next(token for token in listed["tokens"] if token["uuid"] == created["uuid"])
    assert "token" not in listed_token
    assert "token_code" not in listed_token
    assert "token_name" not in listed_token
    assert listed_token["name"] == "Frontend token"
    assert listed_token["created_by"] == "devtable"


def test_create_token_default_expiration_is_10_years(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Default expiration token", "scope": "repo:read"},
            200,
        ).json

    expires_at = datetime.fromisoformat(created["expires_at"].rstrip("Z"))
    created_at = datetime.fromisoformat(created["created"].rstrip("Z"))
    assert abs((expires_at - created_at).total_seconds() - DEFAULT_TOKEN_EXPIRATION_SECONDS) < 5


def test_create_token_rejects_invalid_scope_and_expiration(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Invalid scope token", "scope": "invalid:scope"},
            400,
        )
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Invalid expiration token", "scope": "repo:read", "expiration": 0},
            400,
        )


def test_create_token_rejects_invalid_name(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"scope": "repo:read"},
            400,
        )
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "   ", "scope": "repo:read"},
            400,
        )
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "n" * (MAX_TOKEN_DISPLAY_NAME_LENGTH + 1), "scope": "repo:read"},
            400,
        )


def test_create_token_allows_duplicate_display_names(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        first = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Shared name", "scope": "repo:read"},
            200,
        ).json
        second = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Shared name", "scope": "repo:write"},
            200,
        ).json

    assert first["uuid"] != second["uuid"]
    assert first["name"] == "Shared name"
    assert second["name"] == "Shared name"


def test_create_token_rejects_missing_authenticated_user(app):
    _, application = _setup_app()

    with patch(
        "endpoints.api.organization_application_tokens.get_authenticated_user",
        return_value=None,
    ):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "buynlarge", "client_id": application.client_id},
                {"name": "Missing user token", "scope": "repo:read"},
                403,
            )


def test_create_token_rejects_global_readonly_superuser(app):
    _, application = _setup_app()

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Read only token", "scope": "repo:read"},
            403,
        )


def test_create_token_enforces_scope_subset_for_oauth_caller(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    _, access_token = oauth_model.create_oauth_api_token(
        application,
        user,
        "org:admin repo:read",
    )

    with app.test_client() as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Rejected subset token", "scope": "repo:write"},
            403,
            headers={"Authorization": "Bearer %s" % access_token},
        )

        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Accepted subset token", "scope": "repo:read"},
            200,
            headers={"Authorization": "Bearer %s" % access_token},
        ).json

    assert created["scope"] == "repo:read"


def test_can_mint_scope_has_explicit_mapping_for_known_scopes():
    assert set(MINTABLE_SCOPE_PERMISSION_FACTORIES) == set(scopes.ALL_SCOPES.values())


def test_can_mint_scope_denies_unmapped_valid_scope():
    new_scope = scopes.Scope(
        scope="new:scope",
        icon="fa-plus",
        dangerous=False,
        title="New Scope",
        description="New scope added without a token minting permission mapping.",
    )

    with patch.dict(scopes.ALL_SCOPES, {new_scope.scope: new_scope}):
        with patch(
            "endpoints.api.organization_application_tokens.get_validated_oauth_token",
            return_value=None,
        ):
            assert (
                _can_mint_scope(
                    "buynlarge",
                    new_scope.scope,
                    SimpleNamespace(username="devtable"),
                )
                is False
            )


def test_create_token_non_admin_rejected(app):
    _, application = _setup_app()

    with client_with_identity("freshuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Non admin token", "scope": "repo:read"},
            403,
        )


def test_list_tokens_supports_pagination(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    token_one, _ = oauth_model.create_oauth_api_token(application, user, "repo:read")
    token_two, _ = oauth_model.create_oauth_api_token(application, user, "repo:write")

    with patch(
        "endpoints.api.organization_application_tokens.oauth_model.list_application_tokens"
    ) as list_tokens:
        list_tokens.side_effect = [([token_two], {"id": token_one.id}), ([token_one], None)]

        with client_with_identity("devtable", app) as cl:
            first_page = conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "GET",
                {"orgname": "buynlarge", "client_id": application.client_id},
                None,
                200,
            ).json
            second_page = conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "GET",
                {
                    "orgname": "buynlarge",
                    "client_id": application.client_id,
                    "next_page": first_page["next_page"],
                },
                None,
                200,
            ).json

    assert [token["uuid"] for token in first_page["tokens"]] == [token_two.uuid]
    assert [token["uuid"] for token in second_page["tokens"]] == [token_one.uuid]
    assert "next_page" not in second_page


def test_list_tokens_returns_active_tokens_and_supports_legacy_unnamed_tokens(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    legacy_token, _ = oauth_model.create_oauth_api_token(application, user, "repo:read")
    expired_token, _ = oauth_model.create_oauth_api_token(
        application,
        user,
        "repo:write",
        display_name="Expired token",
    )
    expired_token.expires_at = datetime.utcnow() - timedelta(seconds=10)
    expired_token.save()

    with client_with_identity("devtable", app) as cl:
        listed = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

    listed_by_uuid = {token["uuid"]: token for token in listed["tokens"]}
    assert listed_by_uuid[legacy_token.uuid]["name"] is None
    assert expired_token.uuid not in listed_by_uuid


def test_create_list_use_revoke_flow_for_named_token(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"name": "Frontend flow token", "scope": "org:admin"},
            200,
        ).json

        listed = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json
        listed_token = next(token for token in listed["tokens"] if token["uuid"] == created["uuid"])
        assert listed_token["name"] == "Frontend flow token"
        assert listed_token["last_accessed"] is None

    with app.test_client() as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
            headers={"Authorization": "Bearer %s" % created["token"]},
        )

    with client_with_identity("devtable", app) as cl:
        listed = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json
        listed_token = next(token for token in listed["tokens"] if token["uuid"] == created["uuid"])
        assert listed_token["last_accessed"] is not None

        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": application.client_id,
                "token_uuid": created["uuid"],
            },
            None,
            204,
        )
        listed = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

    assert oauth_model.validate_access_token(created["token"]) is None
    assert created["uuid"] not in {token["uuid"] for token in listed["tokens"]}


def test_list_tokens_allows_global_readonly_superuser(app):
    _, application = _setup_app()

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        )


def test_list_tokens_non_admin_rejected(app):
    _, application = _setup_app()

    with client_with_identity("freshuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            403,
        )


def test_list_tokens_invalid_organization_returns_not_found(app):
    with patch(
        "endpoints.api.organization_application_tokens.allow_if_superuser_with_full_access",
        return_value=True,
    ):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "GET",
                {"orgname": "missingorg", "client_id": "missing-client"},
                None,
                404,
            )


def test_create_token_invalid_organization_returns_not_found(app):
    with patch(
        "endpoints.api.organization_application_tokens.allow_if_superuser_with_full_access",
        return_value=True,
    ):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "missingorg", "client_id": "missing-client"},
                {"name": "Missing org token", "scope": "repo:read"},
                404,
            )


def test_create_token_missing_application_returns_not_found(app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": "missing-client"},
            {"name": "Missing app token", "scope": "repo:read"},
            404,
        )


def test_revoke_token_invalidates_token(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    token_record, access_token = oauth_model.create_oauth_api_token(application, user, "repo:read")

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": application.client_id,
                "token_uuid": token_record.uuid,
            },
            None,
            204,
        )

    assert oauth_model.validate_access_token(access_token) is None


def test_revoke_missing_token_returns_not_found(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": application.client_id,
                "token_uuid": "00000000-0000-0000-0000-000000000000",
            },
            None,
            404,
        )


def test_revoke_token_non_admin_rejected(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    token_record, _ = oauth_model.create_oauth_api_token(application, user, "repo:read")

    with client_with_identity("freshuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": application.client_id,
                "token_uuid": token_record.uuid,
            },
            None,
            403,
        )


def test_revoke_token_rejects_global_readonly_superuser(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    token_record, _ = oauth_model.create_oauth_api_token(application, user, "repo:read")

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": application.client_id,
                "token_uuid": token_record.uuid,
            },
            None,
            403,
        )


def test_revoke_token_invalid_organization_returns_not_found(app):
    with patch(
        "endpoints.api.organization_application_tokens.allow_if_superuser_with_full_access",
        return_value=True,
    ):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplicationToken,
                "DELETE",
                {
                    "orgname": "missingorg",
                    "client_id": "missing-client",
                    "token_uuid": "00000000-0000-0000-0000-000000000000",
                },
                None,
                404,
            )


def test_revoke_token_missing_application_returns_not_found(app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationToken,
            "DELETE",
            {
                "orgname": "buynlarge",
                "client_id": "missing-client",
                "token_uuid": "00000000-0000-0000-0000-000000000000",
            },
            None,
            404,
        )


def test_cross_org_application_rejected(app):
    _, application = _setup_app("sellnsmall")

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            404,
        )


def test_token_limit_enforced(app):
    _, application = _setup_app()
    user = model.user.get_user("devtable")
    oauth_model.create_oauth_api_token(application, user, "repo:read")

    with patch.dict(
        oauth_model.config.app_config,
        {"OAUTH_APPLICATION_MAXIMUM_TOKEN_COUNT": 1},
        clear=False,
    ):
        with client_with_identity("devtable", app) as cl:
            response = conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "buynlarge", "client_id": application.client_id},
                {"name": "Limited token", "scope": "repo:read"},
                400,
            )

    assert response.json["message"] == (
        "Token limit reached: maximum 1 non-expired tokens per application"
    )


def test_create_and_revoke_audit_logs(app):
    _, application = _setup_app()

    with patch("endpoints.api.organization_application_tokens.log_action") as log_action:
        with client_with_identity("devtable", app) as cl:
            created = conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "buynlarge", "client_id": application.client_id},
                {"name": "Audit token", "scope": "repo:read"},
                200,
            ).json
            conduct_api_call(
                cl,
                OrganizationApplicationToken,
                "DELETE",
                {
                    "orgname": "buynlarge",
                    "client_id": application.client_id,
                    "token_uuid": created["uuid"],
                },
                None,
                204,
            )

    create_call, revoke_call = log_action.call_args_list
    assert create_call.args[:2] == ("create_oauth_api_token", "buynlarge")
    assert create_call.kwargs["metadata"]["oauth_token_uuid"] == created["uuid"]
    assert create_call.kwargs["metadata"]["scope"] == "repo:read"
    assert create_call.kwargs["metadata"]["token_display_name"] == "Audit token"
    assert create_call.kwargs["metadata"]["application_name"] == application.name
    assert create_call.kwargs["metadata"]["auth_method"] == "OAuth"
    assert create_call.kwargs["metadata"]["client_id"] == application.client_id
    assert revoke_call.args[:2] == ("revoke_oauth_api_token", "buynlarge")
    assert revoke_call.kwargs["metadata"]["oauth_token_uuid"] == created["uuid"]
    assert revoke_call.kwargs["metadata"]["application_name"] == application.name
    assert revoke_call.kwargs["metadata"]["client_id"] == application.client_id


class _DeletedAuthorizedUser:
    @property
    def username(self):
        raise User.DoesNotExist()


def test_token_view_handles_missing_authorized_user():
    token_without_user = SimpleNamespace(
        uuid="token-uuid-no-user",
        scope="repo:read",
        display_name=None,
        expires_at=None,
        created=None,
        authorized_user=None,
        last_accessed=None,
    )
    token_with_deleted_user = SimpleNamespace(
        uuid="token-uuid-deleted-user",
        scope="repo:read",
        display_name=None,
        expires_at=None,
        created=None,
        authorized_user=_DeletedAuthorizedUser(),
        last_accessed=None,
    )

    assert token_view(token_without_user)["name"] is None
    assert token_view(token_without_user)["created_by"] is None
    assert token_view(token_with_deleted_user)["created_by"] is None
