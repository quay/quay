import pytest
from flask import url_for
from mock import patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import User
from endpoints.test.shared import client_with_identity, conduct_call
from features import FeatureNameValue
from test.fixtures import *


def test_user_metadata_update(app):
    with patch("features.USER_METADATA", FeatureNameValue("USER_METADATA", True)):
        with client_with_identity("devtable", app) as cl:
            metadata = {
                "given_name": "Quay",
                "family_name": "User",
                "location": "NYC",
                "company": "Red Hat",
            }

            # Update all user metadata fields.
            conduct_api_call(cl, User, "PUT", None, body=metadata)

            # Test that they were successfully updated.
            user = conduct_api_call(cl, User, "GET", None).json
            for field in metadata:
                assert user.get(field) == metadata.get(field)

            # Now nullify one of the fields, and remove another.
            metadata["company"] = None
            location = metadata.pop("location")

            conduct_api_call(cl, User, "PUT", None, body=metadata)

            user = conduct_api_call(cl, User, "GET", None).json
            for field in metadata:
                assert user.get(field) == metadata.get(field)

            # The location field should be unchanged.
            assert user.get("location") == location


@pytest.mark.parametrize(
    "user_count, expected_code, feature_mailing, feature_user_initialize, metadata",
    [
        # Non-empty database fails
        (
            1,
            400,
            True,
            True,
            {
                "username": "nonemptydb",
                "password": "password",
                "email": "someone@somewhere.com",
            },
        ),
        # Empty database with mailing succeeds
        (
            0,
            200,
            True,
            True,
            {
                "username": "emptydbemail",
                "password": "password",
                "email": "someone@somewhere.com",
            },
        ),
        # Empty database without mailing succeeds
        (
            0,
            200,
            False,
            True,
            {
                "username": "emptydbnoemail",
                "password": "password",
            },
        ),
        # Empty database with mailing missing email fails
        (
            0,
            400,
            True,
            True,
            {
                "username": "emptydbbademail",
                "password": "password",
            },
        ),
        # Empty database with access token
        (
            0,
            200,
            False,
            True,
            {"username": "emptydbtoken", "password": "password", "access_token": "true"},
        ),
    ],
)
def test_initialize_user(
    user_count, expected_code, feature_mailing, feature_user_initialize, metadata, client
):
    with patch("endpoints.web.has_users") as mock_user_count:
        with patch("features.MAILING", FeatureNameValue("MAILING", feature_mailing)):
            with patch(
                "features.USER_INITIALIZE",
                FeatureNameValue("USER_INITIALIZE", feature_user_initialize),
            ):
                mock_user_count.return_value = user_count
                user = conduct_call(
                    client,
                    "web.user_initialize",
                    url_for,
                    "POST",
                    {},
                    body=metadata,
                    expected_code=expected_code,
                    headers={"Content-Type": "application/json"},
                )

                if expected_code == 200:
                    assert user.json["username"] == metadata["username"]
                    if feature_mailing:
                        assert user.json["email"] == metadata["email"]
                    else:
                        assert user.json["email"] is None
                    assert user.json.get("encrypted_password", None)
                    if metadata.get("access_token"):
                        assert 40 == len(user.json.get("access_token", ""))
                    else:
                        assert not user.json.get("access_token")


def test_user_response_includes_super_user_field_for_regular_superuser(app):
    """Test that regular superusers get super_user=True in the response."""
    with patch("endpoints.api.user.SuperUserPermission") as mock_super_perm, patch(
        "endpoints.api.user.allow_if_global_readonly_superuser", return_value=False
    ):
        mock_super_perm.return_value.can.return_value = True

        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(cl, User, "GET", None, None, 200)

            # Verify the super_user field is present and True
            assert "super_user" in resp.json
            assert resp.json["super_user"] is True

            # Verify is_global_readonly_superuser is not True
            assert resp.json.get("is_global_readonly_superuser", False) is False


def test_user_response_includes_is_global_readonly_superuser_field(app):
    """Test that global readonly superusers get the is_global_readonly_superuser field."""
    with patch("endpoints.api.user.SuperUserPermission") as mock_super_perm, patch(
        "endpoints.api.user.allow_if_global_readonly_superuser", return_value=True
    ):
        mock_super_perm.return_value.can.return_value = False

        with client_with_identity("freshuser", app) as cl:
            resp = conduct_api_call(cl, User, "GET", None, None, 200)

            # Verify the field is present and True
            assert "is_global_readonly_superuser" in resp.json
            assert resp.json["is_global_readonly_superuser"] is True

            # Verify super_user is not True for global readonly users
            assert resp.json.get("super_user", False) is False


def test_user_response_for_regular_user_has_no_superuser_fields(app):
    """Test that regular users don't get superuser fields set to True in the response."""
    with patch("endpoints.api.user.SuperUserPermission") as mock_super_perm, patch(
        "endpoints.api.user.allow_if_global_readonly_superuser", return_value=False
    ):
        mock_super_perm.return_value.can.return_value = False

        with client_with_identity("freshuser", app) as cl:
            resp = conduct_api_call(cl, User, "GET", None, None, 200)

            # Verify superuser fields are not True
            assert resp.json.get("super_user", False) is False
            assert resp.json.get("is_global_readonly_superuser", False) is False
