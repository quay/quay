from test.fixtures import *

import pytest

from data.model import DataModelException
from data.model.organization import create_organization
from data.model.team import (
    __get_user_admin_teams,
    add_or_invite_to_team,
    add_user_to_team,
    confirm_team_invite,
    create_team,
    list_team_users,
    remove_team,
    remove_user_from_team,
    validate_team_name,
)
from data.model.user import create_user_noverify, get_user


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


def test_remove_team(initialized_db):
    first_user = get_user("devtable")

    # Create new org: devtable should be in the admin owners team
    new_org = create_organization("testorg", "testorg" + "@example.com", first_user)
    admin_teams = list(__get_user_admin_teams("testorg", "devtable"))

    assert len(admin_teams) == 1 and admin_teams[0].name == "owners"

    # Create new admin team without adding the devtable to the team:
    # devtable should be able to delete the new admin team
    new_team = create_team("testteam", new_org, "admin", description="test second admin team")
    admin_teams = list(__get_user_admin_teams("testorg", "devtable"))
    assert len(admin_teams) == 1 and admin_teams[0].name != "testteam"

    # Removing the only team which devtable is the admin to should fail
    with pytest.raises(DataModelException):
        remove_team("testorg", "owners", "devtable")

    # Removing the other admin team should succeed, since devtable is already admin in another team
    remove_team("testorg", "testteam", "devtable")


def test_remove_user_from_team(initialized_db):
    first_user = get_user("devtable")
    second_user = get_user("randomuser")

    # Create new org: devtable should be in the admin owners team
    new_org = create_organization("testorg", "testorg" + "@example.com", first_user)
    admin_teams = list(__get_user_admin_teams("testorg", "devtable"))

    # Add user to another admin team
    new_team = create_team("testteam", new_org, "admin", description="test another admin team")
    assert add_user_to_team(second_user, new_team)

    # Cannot remove themselves from their only admin team
    with pytest.raises(DataModelException):
        remove_user_from_team("testorg", "testteam", "randomuser", "randomuser")

    # Another admin should be able to
    remove_user_from_team("testorg", "testteam", "randomuser", "devtable")
