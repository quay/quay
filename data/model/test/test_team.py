import pytest

from data.model.team import (
    add_or_invite_to_team,
    create_team,
    confirm_team_invite,
    list_team_users,
    validate_team_name,
)
from data.model.organization import create_organization
from data.model.user import get_user, create_user_noverify

from test.fixtures import *


@pytest.mark.parametrize(
    "name, is_valid",
    [
        ("", False),
        ("f", False),
        ("fo", True),
        ("f" * 255, True),
        ("f" * 256, False),
        (" ", False),
        ("helloworld", True),
        ("hello_world", True),
        ("hello-world", True),
        ("hello world", False),
        ("HelloWorld", False),
    ],
)
def test_validate_team_name(name, is_valid):
    result, _ = validate_team_name(name)
    assert result == is_valid


def is_in_team(team, user):
    return user.username in {u.username for u in list_team_users(team)}


def test_invite_to_team(initialized_db):
    first_user = get_user("devtable")
    second_user = create_user_noverify("newuser", "foo@example.com")

    def run_invite_flow(orgname):
        # Create an org owned by `devtable`.
        org = create_organization(orgname, orgname + "@example.com", first_user)

        # Create another team and add `devtable` to it. Since `devtable` is already
        # in the org, it should be done directly.
        other_team = create_team("otherteam", org, "admin")
        invite = add_or_invite_to_team(first_user, other_team, user_obj=first_user)
        assert invite is None
        assert is_in_team(other_team, first_user)

        # Try to add `newuser` to the team, which should require an invite.
        invite = add_or_invite_to_team(first_user, other_team, user_obj=second_user)
        assert invite is not None
        assert not is_in_team(other_team, second_user)

        # Accept the invite.
        confirm_team_invite(invite.invite_token, second_user)
        assert is_in_team(other_team, second_user)

    # Run for a new org.
    run_invite_flow("firstorg")

    # Create another org and repeat, ensuring the same operations perform the same way.
    run_invite_flow("secondorg")
