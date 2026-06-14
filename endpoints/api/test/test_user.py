from test.fixtures import *

import pytest
from flask import url_for
from mock import MagicMock, patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import Recovery, User
from endpoints.test.shared import client_with_identity, conduct_call
from features import FeatureNameValue


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


class TestRecoveryPost:
    @patch("endpoints.api.user.send_recovery_email")
    @patch("endpoints.api.user.send_org_recovery_email")
    @patch("endpoints.api.user.model.user.create_reset_password_email_code", return_value="code123")
    @patch("endpoints.api.user.model.organization.find_organizations_by_contact_email", return_value=[])
    @patch("endpoints.api.user.model.user.find_user_by_email")
    def test_recovery_personal_user_only(
        self, mock_find_user, mock_find_orgs, mock_create_code, mock_org_email, mock_recovery_email, app
    ):
        user = MagicMock()
        user.organization = False
        mock_find_user.return_value = user

        with patch("features.MAILING", FeatureNameValue("MAILING", True)):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with client_with_identity(None, app) as cl:
                    result = conduct_api_call(cl, Recovery, "POST", None, body={"email": "user@example.com"})

        assert result.json["status"] == "sent"
        mock_recovery_email.assert_called_once_with("user@example.com", "code123")
        mock_org_email.assert_not_called()

    @patch("endpoints.api.user.send_recovery_email")
    @patch("endpoints.api.user.send_org_recovery_email")
    @patch("endpoints.api.user.model.organization.get_admin_users")
    @patch("endpoints.api.user.model.organization.get_contact_email", return_value="org@example.com")
    @patch("endpoints.api.user.model.organization.find_organizations_by_contact_email")
    @patch("endpoints.api.user.model.user.find_user_by_email", return_value=None)
    def test_recovery_org_only(
        self, mock_find_user, mock_find_orgs, mock_get_contact, mock_get_admins,
        mock_org_email, mock_recovery_email, app
    ):
        org = MagicMock()
        org.organization = True
        mock_find_orgs.return_value = [org]
        admin = MagicMock()
        mock_get_admins.return_value = [admin]

        with patch("features.MAILING", FeatureNameValue("MAILING", True)):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with client_with_identity(None, app) as cl:
                    result = conduct_api_call(cl, Recovery, "POST", None, body={"email": "org@example.com"})

        assert result.json["status"] == "sent"
        mock_org_email.assert_called_once_with(org, [admin], contact_email="org@example.com")
        mock_recovery_email.assert_not_called()

    @patch("endpoints.api.user.send_recovery_email")
    @patch("endpoints.api.user.send_org_recovery_email")
    @patch("endpoints.api.user.model.user.create_reset_password_email_code", return_value="code456")
    @patch("endpoints.api.user.model.organization.get_admin_users")
    @patch("endpoints.api.user.model.organization.get_contact_email", return_value="shared@example.com")
    @patch("endpoints.api.user.model.organization.find_organizations_by_contact_email")
    @patch("endpoints.api.user.model.user.find_user_by_email")
    def test_recovery_both_user_and_org(
        self, mock_find_user, mock_find_orgs, mock_get_contact, mock_get_admins,
        mock_create_code, mock_org_email, mock_recovery_email, app
    ):
        user = MagicMock()
        user.organization = False
        mock_find_user.return_value = user

        org = MagicMock()
        mock_find_orgs.return_value = [org]
        admin = MagicMock()
        mock_get_admins.return_value = [admin]

        with patch("features.MAILING", FeatureNameValue("MAILING", True)):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with client_with_identity(None, app) as cl:
                    result = conduct_api_call(cl, Recovery, "POST", None, body={"email": "shared@example.com"})

        assert result.json["status"] == "sent"
        mock_org_email.assert_called_once_with(org, [admin], contact_email="shared@example.com")
        mock_recovery_email.assert_called_once_with("shared@example.com", "code456")

    @patch("endpoints.api.user.send_recovery_email")
    @patch("endpoints.api.user.send_org_recovery_email")
    @patch("endpoints.api.user.model.organization.find_organizations_by_contact_email", return_value=[])
    @patch("endpoints.api.user.model.user.find_user_by_email", return_value=None)
    def test_recovery_no_match(
        self, mock_find_user, mock_find_orgs, mock_org_email, mock_recovery_email, app
    ):
        with patch("features.MAILING", FeatureNameValue("MAILING", True)):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with client_with_identity(None, app) as cl:
                    result = conduct_api_call(cl, Recovery, "POST", None, body={"email": "nobody@example.com"})

        assert result.json["status"] == "sent"
        mock_org_email.assert_not_called()
        mock_recovery_email.assert_not_called()

    @patch("endpoints.api.user.send_recovery_email")
    @patch("endpoints.api.user.send_org_recovery_email")
    @patch("endpoints.api.user.model.organization.find_organizations_by_contact_email", return_value=[])
    @patch("endpoints.api.user.model.user.find_user_by_email")
    def test_recovery_skips_org_user_from_find_user(
        self, mock_find_user, mock_find_orgs, mock_org_email, mock_recovery_email, app
    ):
        """When find_user_by_email returns an org, it should be ignored (orgs are handled via contact_email)."""
        org_user = MagicMock()
        org_user.organization = True
        mock_find_user.return_value = org_user

        with patch("features.MAILING", FeatureNameValue("MAILING", True)):
            with patch("features.RECAPTCHA", FeatureNameValue("RECAPTCHA", False)):
                with client_with_identity(None, app) as cl:
                    result = conduct_api_call(cl, Recovery, "POST", None, body={"email": "legacy@example.com"})

        assert result.json["status"] == "sent"
        mock_recovery_email.assert_not_called()
