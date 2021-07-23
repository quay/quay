import pytest

from mock import patch

from flask import url_for
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import User
from endpoints.test.shared import client_with_identity, conduct_call
from features import FeatureNameValue

from test.fixtures import *


def test_user_metadata_update(client):
    with patch("features.USER_METADATA", FeatureNameValue("USER_METADATA", True)):
        with client_with_identity("devtable", client) as cl:
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
