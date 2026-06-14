import mock
import pytest

from test.fixtures import *
from util.useremails import (
    render_email,
    send_combined_recovery_email,
    send_org_recovery_email,
    send_recovery_email,
)


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
            "combinedrecovery",
            {
                "organizations": [
                    {"org_name": "myorg", "admin_usernames": ["admin1", "admin2"]},
                ],
                "reset_token": "sometoken",
            },
        ),
        (
            "combinedrecovery",
            {
                "organizations": [
                    {"org_name": "myorg", "admin_usernames": ["admin1"]},
                ],
                "reset_token": None,
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
def test_send_org_recovery_with_contact_email(mock_send_email, initialized_db):
    org = mock.MagicMock()
    org.username = "myorg"
    admin1 = mock.MagicMock()
    admin1.username = "admin1"
    admin1.email = "admin1@example.com"

    send_org_recovery_email(org, [admin1], contact_email="org@example.com")

    mock_send_email.assert_called_once_with(
        "org@example.com",
        "Organization myorg recovery",
        "orgrecovery",
        {"organization": "myorg", "admin_usernames": ["admin1"]},
    )


@mock.patch("util.useremails.send_email")
def test_send_org_recovery_without_contact_email(mock_send_email, initialized_db):
    org = mock.MagicMock()
    org.username = "myorg"
    admin1 = mock.MagicMock()
    admin1.username = "admin1"
    admin1.email = "admin1@example.com"
    admin2 = mock.MagicMock()
    admin2.username = "admin2"
    admin2.email = "admin2@example.com"

    send_org_recovery_email(org, [admin1, admin2])

    assert mock_send_email.call_count == 2
    expected_params = {"organization": "myorg", "admin_usernames": ["admin1", "admin2"]}
    mock_send_email.assert_any_call(
        "admin1@example.com", "Organization myorg recovery", "orgrecovery", expected_params
    )
    mock_send_email.assert_any_call(
        "admin2@example.com", "Organization myorg recovery", "orgrecovery", expected_params
    )


@mock.patch("util.useremails.send_email")
def test_send_org_recovery_no_admins_no_email(mock_send_email, initialized_db):
    org = mock.MagicMock()
    org.username = "myorg"

    send_org_recovery_email(org, [])

    mock_send_email.assert_not_called()


@mock.patch("util.useremails.send_email")
def test_send_combined_recovery_with_user_and_orgs(mock_send_email, initialized_db):
    orgs_with_admins = [
        {"org_name": "org1", "admin_usernames": ["admin1"]},
        {"org_name": "org2", "admin_usernames": ["admin2", "admin3"]},
    ]

    send_combined_recovery_email("shared@example.com", orgs_with_admins, reset_token="token123")

    mock_send_email.assert_called_once_with(
        "shared@example.com",
        "Account recovery",
        "combinedrecovery",
        {"organizations": orgs_with_admins, "reset_token": "token123"},
        action=mock.ANY,
    )


@mock.patch("util.useremails.send_email")
def test_send_combined_recovery_orgs_only(mock_send_email, initialized_db):
    orgs_with_admins = [
        {"org_name": "org1", "admin_usernames": ["admin1"]},
    ]

    send_combined_recovery_email("org@example.com", orgs_with_admins)

    mock_send_email.assert_called_once_with(
        "org@example.com",
        "Account recovery",
        "combinedrecovery",
        {"organizations": orgs_with_admins, "reset_token": None},
        action=None,
    )


def test_render_combined_recovery_template(initialized_db):
    orgs_with_admins = [
        {"org_name": "org1", "admin_usernames": ["admin1", "admin2"]},
        {"org_name": "org2", "admin_usernames": ["admin3"]},
    ]

    html, plain = render_email(
        "Test App",
        "test.quay",
        "foo@example.com",
        "Account recovery",
        "combinedrecovery",
        {"organizations": orgs_with_admins, "reset_token": "testtoken"},
    )

    assert "org1" in html
    assert "org2" in html
    assert "admin1" in html
    assert "admin3" in html
    assert "testtoken" in html
    assert "Recover Account" in html
    assert "Login to Recover" in html


def test_render_combined_recovery_template_no_reset(initialized_db):
    orgs_with_admins = [
        {"org_name": "myorg", "admin_usernames": ["admin1"]},
    ]

    html, plain = render_email(
        "Test App",
        "test.quay",
        "foo@example.com",
        "Account recovery",
        "combinedrecovery",
        {"organizations": orgs_with_admins, "reset_token": None},
    )

    assert "myorg" in html
    assert "admin1" in html
    assert "Login to Recover" in html
    assert "Recover Account" not in html
