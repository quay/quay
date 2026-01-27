from test.fixtures import *

import pytest
from flask import url_for
from mock import patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import User
from endpoints.test.shared import client_with_identity, conduct_call
from features import FeatureNameValue
from util.useremails import CannotSendEmailException


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


def test_email_exception_error_format(app, client):
    """
    Test that CannotSendEmailException returns standard error format.

    This test verifies the fix for PROJQUAY-10418, ensuring that email
    sending failures return a properly formatted error response that the
    new UI can parse correctly.

    Verifies:
    - HTTP 400 status code
    - error_message field (for new UI)
    - detail field (standard ApiException format)
    - message field (backward compatibility with old UI)
    - status field
    """
    with patch("features.MAILING", FeatureNameValue("MAILING", True)):
        with patch(
            "features.INVITE_ONLY_USER_CREATION",
            FeatureNameValue("INVITE_ONLY_USER_CREATION", False),
        ):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with patch("util.useremails.send_confirmation_email") as mock_send_email:
                    # Mock send_confirmation_email to raise CannotSendEmailException
                    mock_send_email.side_effect = CannotSendEmailException(
                        "SMTP connection failed"
                    )

                    # Attempt to create a new user via API (will trigger email sending)
                    metadata = {
                        "username": "emailfailtest",
                        "password": "password",
                        "email": "test@example.com",
                    }

                    response = conduct_api_call(
                        client,
                        User,
                        "POST",
                        None,
                        body=metadata,
                        expected_code=400,
                    )

                # Verify the error response format
                expected_message = "Could not send email. Please contact an administrator and report this problem."

                # Verify all required fields exist
                assert (
                    "error_message" in response.json
                ), "Should have error_message field for new UI"
                assert (
                    "detail" in response.json
                ), "Should have detail field matching ApiException format"
                assert (
                    "message" in response.json
                ), "Should have message field for backward compatibility"
                assert "status" in response.json, "Should have status field"

                # Verify field values
                assert (
                    response.json["error_message"] == expected_message
                ), "error_message should match expected text"
                assert (
                    response.json["detail"] == expected_message
                ), "detail should match expected text"
                assert (
                    response.json["message"] == expected_message
                ), "message should match expected text"
                assert response.json["status"] == 400, "status field should be 400"

                # Verify new UI can extract the error (won't fall back to generic message)
                error_message = response.json.get("error_message")
                assert (
                    error_message is not None
                ), "New UI should be able to extract error_message"
                assert (
                    error_message != "unable to make request"
                ), "Should not fall back to generic message"
