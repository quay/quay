from test.fixtures import *

import mock
import pytest

from util.useremails import render_email, send_org_recovery_email, send_recovery_email


def test_render_email():
    params = {
        "username": "someusername",
        "new_email": "new@example.com",
    }

    html, plain = render_email(
        "Test App", "test.quay", "foo@example.com", "Hello There!", "emailchanged", params
    )
    assert "https://quay.io/contact/" in html
    assert "https://quay.io/contact/" in plain


@pytest.mark.parametrize(
    "template_name, params",
    [
        (
            "passwordchanged",
            {
                "username": "someusername",
            },
        ),
        (
            "emailchanged",
            {
                "username": "someusername",
                "new_email": "new@example.com",
            },
        ),
        (
            "changeemail",
            {
                "username": "someusername",
                "token": "sometoken",
            },
        ),
        (
            "confirmemail",
            {
                "username": "someusername",
                "token": "sometoken",
            },
        ),
        (
            "repoauthorizeemail",
            {
                "namespace": "someusername",
                "repository": "somerepo",
                "token": "sometoken",
            },
        ),
        (
            "orgrecovery",
            {
                "organization": "someusername",
                "admin_usernames": ["foo", "bar", "baz"],
            },
        ),
        (
            "recovery",
            {
                "email": "foo@example.com",
                "token": "sometoken",
            },
        ),
        (
            "paymentfailure",
            {
                "username": "someusername",
            },
        ),
        (
            "teaminvite",
            {
                "inviter": "someusername",
                "token": "sometoken",
                "organization": "someorg",
                "teamname": "someteam",
            },
        ),
    ],
)
def test_emails(template_name, params, initialized_db):
    render_email("Test App", "test.quay", "foo@example.com", "Hello There!", template_name, params)


@mock.patch("util.useremails.send_email")
def test_send_recovery_email(mock_send_email, initialized_db):

    email = "quay_user@example.com"
    token = "fake_token"

    send_recovery_email(email, token)

    # Expected call arguments
    subject = "Account recovery"
    template_file = "recovery"
    parameters = {"email": email, "token": token}
    action = mock.ANY  # TODO: assert GmailAction.view() is called

    mock_send_email.assert_called_once_with(
        email, subject, template_file, parameters, action=action
    )


@mock.patch("util.useremails.send_email")
def test_send_org_recovery_email_with_contact_email(mock_send_email, initialized_db):
    """Test that send_org_recovery_email sends to contact_email when provided."""
    org = mock.MagicMock()
    org.username = "testorg"
    admin1 = mock.MagicMock()
    admin1.username = "admin1"
    admin1.email = "admin1@example.com"

    send_org_recovery_email(org, [admin1], contact_email="contact@example.com")

    mock_send_email.assert_called_once_with(
        "contact@example.com",
        "Organization testorg recovery",
        "orgrecovery",
        {"organization": "testorg", "admin_usernames": ["admin1"]},
    )


@mock.patch("util.useremails.send_email")
def test_send_org_recovery_email_fallback_to_admins(mock_send_email, initialized_db):
    """Test that send_org_recovery_email falls back to admin emails when no contact_email."""
    org = mock.MagicMock()
    org.username = "testorg"
    admin1 = mock.MagicMock()
    admin1.username = "admin1"
    admin1.email = "admin1@example.com"
    admin2 = mock.MagicMock()
    admin2.username = "admin2"
    admin2.email = "admin2@example.com"

    send_org_recovery_email(org, [admin1, admin2])

    assert mock_send_email.call_count == 2
    calls = mock_send_email.call_args_list
    assert calls[0][0][0] == "admin1@example.com"
    assert calls[1][0][0] == "admin2@example.com"


@mock.patch("util.useremails.send_email")
def test_send_org_recovery_email_no_contact_no_admins(mock_send_email, initialized_db):
    """Test that no emails are sent when no contact_email and no admin emails."""
    org = mock.MagicMock()
    org.username = "testorg"
    admin = mock.MagicMock()
    admin.username = "admin1"
    admin.email = None

    send_org_recovery_email(org, [admin])

    mock_send_email.assert_not_called()
