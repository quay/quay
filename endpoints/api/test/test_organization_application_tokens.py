from datetime import datetime, timedelta
from unittest.mock import patch

from data import model
from data.model import oauth as oauth_model
from endpoints.api.organization_application_tokens import (
    OrganizationApplicationToken,
    OrganizationApplicationTokens,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _setup_app(orgname="buynlarge", app_name="test-token-app"):
    org = model.organization.get_organization(orgname)
    application = oauth_model.get_or_create_application(app_name, org)
    return org, application


def test_create_token(app):
    org, application = _setup_app()
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "repo:read repo:write"}
        resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            200,
        ).json

        assert "token" in resp
        assert resp["scope"] == "repo:read repo:write"
        assert resp["uuid"]
        assert resp["expires_at"]


def test_create_token_comma_scope(app):
    org, application = _setup_app()
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "repo:read,repo:write"}
        resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            200,
        ).json

        assert resp["scope"] == "repo:read repo:write"


def test_create_token_missing_scope(app):
    org, application = _setup_app()
    with client_with_identity("devtable", app) as cl:
        body = {}
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            400,
        )


def test_create_token_invalid_scope(app):
    org, application = _setup_app()
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "invalid:nonexistent"}
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            400,
        )


def test_create_token_non_admin_rejected(app):
    org, application = _setup_app()
    with client_with_identity("freshuser", app) as cl:
        body = {"scope": "repo:read"}
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            403,
        )


def test_create_token_nonexistent_org(app):
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "repo:read"}
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "nonexistent-org", "client_id": "fakeid"},
            body,
            404,
        )


def test_create_token_nonexistent_app(app):
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "repo:read"}
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": "nonexistent-client-id"},
            body,
            404,
        )


def test_list_tokens(app):
    org, application = _setup_app()
    user = model.user.get_user("devtable")

    oauth_model.create_oauth_api_token(application, user, "repo:read")
    oauth_model.create_oauth_api_token(application, user, "repo:write")

    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

        assert "tokens" in resp
        assert len(resp["tokens"]) >= 2

        for t in resp["tokens"]:
            assert "uuid" in t
            assert "scope" in t
            assert "scope" in t
            assert "expires_at" in t
            assert "created" in t
            assert "last_accessed" in t
            assert "token" not in t
            assert "token_code" not in t
            assert "token_name" not in t


def test_list_tokens_non_admin_rejected(app):
    org, application = _setup_app()
    with client_with_identity("freshuser", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            403,
        )


def test_delete_token(app):
    org, application = _setup_app()
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

    validated = oauth_model.validate_access_token(access_token)
    assert validated is None


def test_delete_nonexistent_token(app):
    org, application = _setup_app()
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


def test_delete_token_non_admin_rejected(app):
    org, application = _setup_app()
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


def test_token_limit_enforcement(app):
    org, application = _setup_app(app_name="limit-test-app")
    user = model.user.get_user("devtable")

    with patch("endpoints.api.organization_application_tokens.MAX_TOKENS_PER_APPLICATION", 2):
        oauth_model.create_oauth_api_token(application, user, "repo:read")
        oauth_model.create_oauth_api_token(application, user, "repo:read")

        with client_with_identity("devtable", app) as cl:
            body = {"scope": "repo:read"}
            conduct_api_call(
                cl,
                OrganizationApplicationTokens,
                "POST",
                {"orgname": "buynlarge", "client_id": application.client_id},
                body,
                400,
            )


def test_create_token_returns_secret_only_once(app):
    org, application = _setup_app()
    with client_with_identity("devtable", app) as cl:
        body = {"scope": "repo:read"}
        resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": application.client_id},
            body,
            200,
        ).json

        assert "token" in resp
        token_uuid = resp["uuid"]

        list_resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

        found = False
        for t in list_resp["tokens"]:
            if t["uuid"] == token_uuid:
                assert "token" not in t
                found = True
                break
        assert found, "Created token not found in list response"


def test_last_accessed_starts_null(app):
    org, application = _setup_app()
    user = model.user.get_user("devtable")
    token_record, _ = oauth_model.create_oauth_api_token(application, user, "repo:read")

    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl,
            OrganizationApplicationTokens,
            "GET",
            {"orgname": "buynlarge", "client_id": application.client_id},
            None,
            200,
        ).json

        found = False
        for t in resp["tokens"]:
            if t["uuid"] == token_record.uuid:
                assert t["last_accessed"] is None
                found = True
                break
        assert found, "Created token not found in list response"
