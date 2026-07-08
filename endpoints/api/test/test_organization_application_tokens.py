from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from data import model
from data.database import User
from data.model import oauth as oauth_model
from data.model.oauth import DEFAULT_TOKEN_EXPIRATION_SECONDS
from endpoints.api.organization_application_tokens import (
    OrganizationApplicationToken,
    OrganizationApplicationTokens,
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
            {"scope": "repo:read,repo:write"},
            200,
        ).json

        assert created["token"]
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
    assert listed_token["created_by"] == "devtable"


def test_create_token_default_expiration_is_10_years(app):
    _, application = _setup_app()

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"scope": "repo:read"},
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
            {"scope": "invalid:scope"},
            400,
        )
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"scope": "repo:read", "expiration": 0},
            400,
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
            {"scope": "repo:write"},
            403,
            headers={"Authorization": "Bearer %s" % access_token},
        )

        created = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"scope": "repo:read"},
            200,
            headers={"Authorization": "Bearer %s" % access_token},
        ).json

    assert created["scope"] == "repo:read"


def test_create_token_non_admin_rejected(app):
    _, application = _setup_app()

    with client_with_identity("freshuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {"scope": "repo:read"},
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

    with patch("endpoints.api.organization_application_tokens.MAX_TOKENS_PER_APPLICATION", 1):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "buynlarge", "client_id": application.client_id},
                {"scope": "repo:read"},
                400,
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
                {"scope": "repo:read"},
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
    assert create_call.kwargs["metadata"]["client_id"] == application.client_id
    assert revoke_call.args[:2] == ("revoke_oauth_api_token", "buynlarge")
    assert revoke_call.kwargs["metadata"]["oauth_token_uuid"] == created["uuid"]
    assert revoke_call.kwargs["metadata"]["client_id"] == application.client_id


class _DeletedAuthorizedUser:
    @property
    def username(self):
        raise User.DoesNotExist()


def test_token_view_handles_missing_authorized_user():
    token_without_user = SimpleNamespace(
        uuid="token-uuid-no-user",
        scope="repo:read",
        expires_at=None,
        created=None,
        authorized_user=None,
        last_accessed=None,
    )
    token_with_deleted_user = SimpleNamespace(
        uuid="token-uuid-deleted-user",
        scope="repo:read",
        expires_at=None,
        created=None,
        authorized_user=_DeletedAuthorizedUser(),
        last_accessed=None,
    )

    assert token_view(token_without_user)["created_by"] is None
    assert token_view(token_with_deleted_user)["created_by"] is None
