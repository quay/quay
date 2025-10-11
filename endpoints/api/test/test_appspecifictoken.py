from datetime import datetime, timedelta
from unittest.mock import patch

from data import model
from endpoints.api.appspecifictokens import AppToken, AppTokens
from endpoints.api.superuser import SuperUserAppTokens
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def test_app_specific_tokens(app):
    with client_with_identity("devtable", app) as cl:
        # Add an app specific token.
        token_data = {"title": "Testing 123"}
        resp = conduct_api_call(cl, AppTokens, "POST", None, token_data, 200).json
        token_uuid = resp["token"]["uuid"]
        assert "token_code" in resp["token"]

        # List the tokens and ensure we have the one added.
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        assert len(resp["tokens"])
        assert token_uuid in set([token["uuid"] for token in resp["tokens"]])
        assert not set([token["token_code"] for token in resp["tokens"] if "token_code" in token])

        # List the tokens expiring soon and ensure the one added is not present.
        resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
        assert token_uuid not in set([token["uuid"] for token in resp["tokens"]])

        # Get the token and ensure we have its code (owner can see secret).
        resp = conduct_api_call(cl, AppToken, "GET", {"token_uuid": token_uuid}, None, 200).json
        assert resp["token"]["uuid"] == token_uuid
        assert "token_code" in resp["token"]

        # Delete the token.
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": token_uuid}, None, 204)

        # Ensure the token no longer exists.
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        assert len(resp["tokens"])
        assert token_uuid not in set([token["uuid"] for token in resp["tokens"]])

        conduct_api_call(cl, AppToken, "GET", {"token_uuid": token_uuid}, None, 404)


def test_delete_expired_app_token(app):
    user = model.user.get_user("devtable")
    expiration = datetime.now() - timedelta(seconds=10)
    token = model.appspecifictoken.create_token(user, "some token", expiration)

    with client_with_identity("devtable", app) as cl:
        # Delete the token.
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": token.uuid}, None, 204)


def test_list_tokens_user_scoped(app):
    """Test that all user types only see their own tokens on /v1/user/apptoken

    Tests regular users, superusers, and global readonly superusers to ensure
    proper token scoping - users should only see their own tokens on this endpoint.
    """
    # Test freshuser (regular user)
    freshuser_token_data = {"title": "Freshuser Test Token"}
    with client_with_identity("freshuser", app) as cl:
        # Create a token for this user
        resp = conduct_api_call(cl, AppTokens, "POST", None, freshuser_token_data, 200).json
        freshuser_token_uuid = resp["token"]["uuid"]

        # List tokens - freshuser should see their own token
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert freshuser_token_uuid in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": freshuser_token_uuid}, None, 204)

    # Test devtable (superuser)
    devtable_token_data = {"title": "Devtable Test Token"}
    with client_with_identity("devtable", app) as cl:
        # Create a token for this user
        resp = conduct_api_call(cl, AppTokens, "POST", None, devtable_token_data, 200).json
        devtable_token_uuid = resp["token"]["uuid"]

        # List tokens - superuser should see their own token but not freshuser's on /v1/user/apptoken
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert devtable_token_uuid in token_uuids
        assert freshuser_token_uuid not in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": devtable_token_uuid}, None, 204)

    # Test globalreadonlysuperuser (global readonly superuser)
    global_ro_token_data = {"title": "Global RO Test Token"}
    with client_with_identity("globalreadonlysuperuser", app) as cl:
        # Create a token for this user
        resp = conduct_api_call(cl, AppTokens, "POST", None, global_ro_token_data, 200).json
        global_ro_token_uuid = resp["token"]["uuid"]

        # List tokens - global readonly superuser should see their own token but not others'
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert global_ro_token_uuid in token_uuids
        assert freshuser_token_uuid not in token_uuids
        assert devtable_token_uuid not in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": global_ro_token_uuid}, None, 204)


def test_list_expiring_tokens_user_scoped(app):
    """Test that expiring token filtering is properly scoped for all user types

    Tests that the expiring=True parameter only returns expiring tokens belonging
    to the authenticated user, regardless of user type (regular, superuser, global readonly).
    """
    soon_expiration = datetime.now() + timedelta(minutes=1)
    far_expiration = datetime.now() + timedelta(days=30)

    # Test freshuser (regular user)
    with client_with_identity("freshuser", app) as cl:
        # Create expiring and non-expiring tokens via API
        expiring_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Freshuser Expiring"}, 200
        ).json
        expiring_uuid = expiring_resp["token"]["uuid"]

        normal_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Freshuser Normal"}, 200
        ).json
        normal_uuid = normal_resp["token"]["uuid"]

        # Update expiration times directly on the tokens
        expiring_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == expiring_uuid
        )
        expiring_token.expiration = soon_expiration
        expiring_token.save()

        normal_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == normal_uuid
        )
        normal_token.expiration = far_expiration
        normal_token.save()

        # Query with expiring=True - should only see expiring token
        resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert expiring_uuid in token_uuids
        assert normal_uuid not in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": expiring_uuid}, None, 204)
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": normal_uuid}, None, 204)

    # Test devtable (superuser)
    with client_with_identity("devtable", app) as cl:
        # Create expiring and non-expiring tokens via API
        expiring_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Devtable Expiring"}, 200
        ).json
        expiring_uuid = expiring_resp["token"]["uuid"]

        normal_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Devtable Normal"}, 200
        ).json
        normal_uuid = normal_resp["token"]["uuid"]

        # Update expiration times
        expiring_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == expiring_uuid
        )
        expiring_token.expiration = soon_expiration
        expiring_token.save()

        normal_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == normal_uuid
        )
        normal_token.expiration = far_expiration
        normal_token.save()

        # Query with expiring=True - superuser should only see their own expiring token
        resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert expiring_uuid in token_uuids
        assert normal_uuid not in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": expiring_uuid}, None, 204)
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": normal_uuid}, None, 204)

    # Test globalreadonlysuperuser (global readonly superuser)
    with client_with_identity("globalreadonlysuperuser", app) as cl:
        # Create expiring and non-expiring tokens via API
        expiring_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Global RO Expiring"}, 200
        ).json
        expiring_uuid = expiring_resp["token"]["uuid"]

        normal_resp = conduct_api_call(
            cl, AppTokens, "POST", None, {"title": "Global RO Normal"}, 200
        ).json
        normal_uuid = normal_resp["token"]["uuid"]

        # Update expiration times
        expiring_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == expiring_uuid
        )
        expiring_token.expiration = soon_expiration
        expiring_token.save()

        normal_token = model.appspecifictoken.AppSpecificAuthToken.get(
            model.appspecifictoken.AppSpecificAuthToken.uuid == normal_uuid
        )
        normal_token.expiration = far_expiration
        normal_token.save()

        # Query with expiring=True - global RO superuser should only see their own expiring token
        resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
        token_uuids = set([token["uuid"] for token in resp["tokens"]])
        assert expiring_uuid in token_uuids
        assert normal_uuid not in token_uuids

        # Clean up
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": expiring_uuid}, None, 204)
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": normal_uuid}, None, 204)


def test_list_tokens_no_token_codes(app):
    """Test that token codes are never included in list responses"""
    devtable_user = model.user.get_user("devtable")
    token = model.appspecifictoken.create_token(devtable_user, "Test Token")

    try:
        with client_with_identity("devtable", app) as cl:
            # List tokens should never include token codes
            resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
            for token_data in resp["tokens"]:
                assert "token_code" not in token_data
                assert "uuid" in token_data
                assert "title" in token_data
                assert "last_accessed" in token_data
                assert "created" in token_data
                assert "expiration" in token_data
    finally:
        # Clean up
        token.delete_instance()


def test_individual_token_access_regular_user(app):
    """Test that regular users can only access their own tokens on /v1/user/apptoken"""
    freshuser = model.user.get_user("freshuser")
    reader_user = model.user.get_user("reader")
    freshuser_token = model.appspecifictoken.create_token(freshuser, "Freshuser Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        with client_with_identity("freshuser", app) as cl:
            # Should be able to access own token with secret
            resp = conduct_api_call(
                cl, AppToken, "GET", {"token_uuid": freshuser_token.uuid}, None, 200
            ).json
            assert resp["token"]["uuid"] == freshuser_token.uuid
            assert "token_code" in resp["token"]

            # Should NOT be able to access other user's token
            conduct_api_call(cl, AppToken, "GET", {"token_uuid": reader_token.uuid}, None, 404)
    finally:
        freshuser_token.delete_instance()
        reader_token.delete_instance()


def test_individual_token_access_superuser(app):
    """Test that superusers can only access their own tokens on /v1/user/apptoken"""
    devtable_user = model.user.get_user("devtable")
    freshuser = model.user.get_user("freshuser")
    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    freshuser_token = model.appspecifictoken.create_token(freshuser, "Freshuser Token")

    try:
        with client_with_identity("devtable", app) as cl:
            # Superuser should be able to access own token with secret on /v1/user/apptoken
            resp = conduct_api_call(
                cl, AppToken, "GET", {"token_uuid": devtable_token.uuid}, None, 200
            ).json
            assert resp["token"]["uuid"] == devtable_token.uuid
            assert "token_code" in resp["token"]

            # Superuser should NOT be able to access other user's token on /v1/user/apptoken
            conduct_api_call(cl, AppToken, "GET", {"token_uuid": freshuser_token.uuid}, None, 404)
    finally:
        devtable_token.delete_instance()
        freshuser_token.delete_instance()


def test_individual_token_access_global_readonly_superuser(app):
    """Test that global readonly superusers can only access their own tokens on /v1/user/apptoken"""
    devtable_user = model.user.get_user("devtable")
    global_ro_user = model.user.get_user("globalreadonlysuperuser")
    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    global_ro_token = model.appspecifictoken.create_token(global_ro_user, "Global RO Token")

    try:
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Global RO superuser should be able to access own token with secret
            resp = conduct_api_call(
                cl, AppToken, "GET", {"token_uuid": global_ro_token.uuid}, None, 200
            ).json
            assert resp["token"]["uuid"] == global_ro_token.uuid
            assert "token_code" in resp["token"]

            # Global RO superuser should NOT be able to access other user's token on /v1/user/apptoken
            conduct_api_call(cl, AppToken, "GET", {"token_uuid": devtable_token.uuid}, None, 404)
    finally:
        devtable_token.delete_instance()
        global_ro_token.delete_instance()


def test_superuser_endpoint_sees_all_tokens(app):
    """Test that superusers and global readonly superusers can see all tokens on /v1/superuser/apptokens"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Test superuser
        with client_with_identity("devtable", app) as cl:
            # On /v1/superuser/apptokens, superuser should see all tokens
            resp = conduct_api_call(cl, SuperUserAppTokens, "GET", None, None, 200).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])

            assert devtable_token.uuid in token_uuids
            assert reader_token.uuid in token_uuids
            for token in resp["tokens"]:
                assert "token_code" not in token

        # Test global readonly superuser
        # Mock global readonly superuser by mocking the permission classes
        with patch("endpoints.api.SuperUserPermission") as mock_super_perm, patch(
            "endpoints.api.GlobalReadOnlySuperUserPermission"
        ) as mock_global_ro_perm, patch(
            "endpoints.api.superuser.allow_if_any_superuser", return_value=True
        ):
            # Not a regular superuser, but is a global readonly superuser
            mock_super_perm.return_value.can.return_value = False
            mock_global_ro_perm.return_value.can.return_value = True

            with client_with_identity("reader", app) as cl:
                # On /v1/superuser/apptokens, global readonly superuser should see all tokens
                resp = conduct_api_call(cl, SuperUserAppTokens, "GET", None, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])

                assert devtable_token.uuid in token_uuids
                assert reader_token.uuid in token_uuids
                for token in resp["tokens"]:
                    assert "token_code" not in token

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_superuser_endpoint_expiring_tokens(app):
    """Test expiring token filtering on /v1/superuser/apptokens"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    # Create expiring and non-expiring tokens for both users
    soon_expiration = datetime.now() + timedelta(minutes=1)
    far_expiration = datetime.now() + timedelta(days=30)

    devtable_expiring = model.appspecifictoken.create_token(
        devtable_user, "DevTable Expiring", soon_expiration
    )
    devtable_normal = model.appspecifictoken.create_token(
        devtable_user, "DevTable Normal", far_expiration
    )
    reader_expiring = model.appspecifictoken.create_token(
        reader_user, "Reader Expiring", soon_expiration
    )
    reader_normal = model.appspecifictoken.create_token(
        reader_user, "Reader Normal", far_expiration
    )

    try:
        with client_with_identity("devtable", app) as cl:
            # On /v1/superuser/apptokens with expiring=True, should see all expiring tokens
            resp = conduct_api_call(
                cl, SuperUserAppTokens, "GET", {"expiring": True}, None, 200
            ).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])

            # Should see expiring tokens from both users
            assert devtable_expiring.uuid in token_uuids
            assert reader_expiring.uuid in token_uuids
            # Should not see non-expiring tokens
            assert devtable_normal.uuid not in token_uuids
            assert reader_normal.uuid not in token_uuids

    finally:
        # Clean up
        devtable_expiring.delete_instance()
        devtable_normal.delete_instance()
        reader_expiring.delete_instance()
        reader_normal.delete_instance()
