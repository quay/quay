import pytest

from util.useremails import render_email
from test.fixtures import *


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
        ("passwordchanged", {"username": "someusername",}),
        ("emailchanged", {"username": "someusername", "new_email": "new@example.com",}),
        ("changeemail", {"username": "someusername", "token": "sometoken",}),
        ("confirmemail", {"username": "someusername", "token": "sometoken",}),
        (
            "repoauthorizeemail",
            {"namespace": "someusername", "repository": "somerepo", "token": "sometoken",},
        ),
        (
            "orgrecovery",
            {"organization": "someusername", "admin_usernames": ["foo", "bar", "baz"],},
        ),
        ("recovery", {"email": "foo@example.com", "token": "sometoken",}),
        ("paymentfailure", {"username": "someusername",}),
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
