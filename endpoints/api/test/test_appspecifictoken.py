from datetime import datetime, timedelta
from unittest.mock import patch

from data import model
from endpoints.api.appspecifictokens import AppToken, AppTokens
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


def test_list_tokens_superuser(app):
    """Test that superusers can see all tokens"""
    # Create tokens for multiple users
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Explicitly mark as superuser for this test
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=True), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=False
        ):
            with client_with_identity("devtable", app) as cl:
                # devtable is a superuser, so should see all tokens
                resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])
                assert devtable_token.uuid in token_uuids
                assert reader_token.uuid in token_uuids  # Superuser sees all tokens

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_list_tokens_regular_user(app):
    """Test that regular users only see their own tokens"""
    # Create tokens for multiple users
    freshuser = model.user.get_user("freshuser")
    reader_user = model.user.get_user("reader")

    freshuser_token = model.appspecifictoken.create_token(freshuser, "Freshuser Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        with client_with_identity("freshuser", app) as cl:
            # Fresh user (regular user) should only see their own token
            resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])
            assert freshuser_token.uuid in token_uuids
            assert reader_token.uuid not in token_uuids
    finally:
        # Clean up
        freshuser_token.delete_instance()
        reader_token.delete_instance()


def test_list_tokens_reader_user(app):
    """Test that reader user only sees their tokens"""
    # Create tokens for multiple users
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        with client_with_identity("reader", app) as cl:
            # Reader user should only see their token
            resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])
            assert reader_token.uuid in token_uuids
            assert devtable_token.uuid not in token_uuids
    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_list_expiring_tokens_superuser_scoped(app):
    """Test expiring token filtering for superuser - should see expiring tokens from all users"""
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
        # Explicitly mark as superuser for this test
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=True), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=False
        ):
            with client_with_identity("devtable", app) as cl:
                # DevTable user (superuser) with expiring=True should see ALL expiring tokens
                resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])
                assert devtable_expiring.uuid in token_uuids
                assert reader_expiring.uuid in token_uuids  # Superuser sees all
                assert devtable_normal.uuid not in token_uuids
                assert reader_normal.uuid not in token_uuids
    finally:
        # Clean up
        devtable_expiring.delete_instance()
        devtable_normal.delete_instance()
        reader_expiring.delete_instance()
        reader_normal.delete_instance()


def test_list_expiring_tokens_reader_user_scoped(app):
    """Test expiring token filtering is properly scoped for reader user"""
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
        with client_with_identity("reader", app) as cl:
            # Reader user with expiring=True should only see their expiring token
            resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])
            assert reader_expiring.uuid in token_uuids
            assert reader_normal.uuid not in token_uuids
            assert devtable_expiring.uuid not in token_uuids
            assert devtable_normal.uuid not in token_uuids
    finally:
        # Clean up
        devtable_expiring.delete_instance()
        devtable_normal.delete_instance()
        reader_expiring.delete_instance()
        reader_normal.delete_instance()


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


def test_global_readonly_superuser_sees_all_tokens(app):
    """Test that global read-only superusers can see all tokens across users"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Mock global readonly superuser
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=False), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # Global readonly superuser should see all tokens
                resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])

                # Should see both tokens
                assert devtable_token.uuid in token_uuids
                assert reader_token.uuid in token_uuids

                # Verify no token codes are included in list
                for token in resp["tokens"]:
                    assert "token_code" not in token

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_regular_user_sees_only_own_tokens(app):
    """Test that regular users still only see their own tokens"""
    freshuser = model.user.get_user("freshuser")
    reader_user = model.user.get_user("reader")

    freshuser_token = model.appspecifictoken.create_token(freshuser, "Freshuser Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        with client_with_identity("freshuser", app) as cl:
            resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
            token_uuids = set([token["uuid"] for token in resp["tokens"]])

            # Freshuser should only see their token
            assert freshuser_token.uuid in token_uuids
            assert reader_token.uuid not in token_uuids

    finally:
        # Clean up
        freshuser_token.delete_instance()
        reader_token.delete_instance()


def test_global_readonly_superuser_expiring_tokens_all_users(app):
    """Test that global read-only superusers see expiring tokens from all users"""
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
        # Mock global readonly superuser
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=False), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # Should see expiring tokens from all users
                resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
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


def test_global_readonly_superuser_individual_token_access(app):
    """Test that global read-only superusers can access any user's individual token"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Mock global readonly superuser
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=False), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # Should be able to access devtable's token, but WITHOUT secret
                resp = conduct_api_call(
                    cl, AppToken, "GET", {"token_uuid": devtable_token.uuid}, None, 200
                ).json
                assert resp["token"]["uuid"] == devtable_token.uuid
                assert "token_code" not in resp["token"]

                # Should be able to access reader's OWN token, WITH secret
                resp = conduct_api_call(
                    cl, AppToken, "GET", {"token_uuid": reader_token.uuid}, None, 200
                ).json
                assert resp["token"]["uuid"] == reader_token.uuid
                assert "token_code" in resp["token"]

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_regular_user_individual_token_access_restrictions(app):
    """Test that regular users can only access their own tokens"""
    freshuser = model.user.get_user("freshuser")
    reader_user = model.user.get_user("reader")

    freshuser_token = model.appspecifictoken.create_token(freshuser, "Freshuser Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        with client_with_identity("freshuser", app) as cl:
            # Should be able to access own token
            resp = conduct_api_call(
                cl, AppToken, "GET", {"token_uuid": freshuser_token.uuid}, None, 200
            ).json
            assert resp["token"]["uuid"] == freshuser_token.uuid
            assert "token_code" in resp["token"]

            # Should NOT be able to access other user's token
            conduct_api_call(cl, AppToken, "GET", {"token_uuid": reader_token.uuid}, None, 404)

    finally:
        # Clean up
        freshuser_token.delete_instance()
        reader_token.delete_instance()


def test_regular_superuser_token_access(app):
    """Test that regular superusers can see all tokens"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Test regular superuser (devtable is a superuser)
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=True), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=False
        ):

            with client_with_identity("devtable", app) as cl:
                # Regular superuser should also see all tokens identifiers only
                resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])

                assert devtable_token.uuid in token_uuids
                assert reader_token.uuid in token_uuids
                for token in resp["tokens"]:
                    assert "token_code" not in token

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()


def test_global_readonly_superuser_token_access(app):
    """Test that global readonly superusers can see all tokens"""
    devtable_user = model.user.get_user("devtable")
    reader_user = model.user.get_user("reader")

    devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
    reader_token = model.appspecifictoken.create_token(reader_user, "Reader Token")

    try:
        # Test global readonly superuser
        with patch("endpoints.api.appspecifictokens.allow_if_superuser", return_value=False), patch(
            "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # Global readonly superuser should also see all tokens identifiers only
                resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
                token_uuids = set([token["uuid"] for token in resp["tokens"]])

                assert devtable_token.uuid in token_uuids
                assert reader_token.uuid in token_uuids
                for token in resp["tokens"]:
                    assert "token_code" not in token

    finally:
        # Clean up
        devtable_token.delete_instance()
        reader_token.delete_instance()
