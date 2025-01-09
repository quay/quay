import json

import pytest

from data.database import TeamMember
from data.model import DataModelException, UserAlreadyInTeam
from data.model.organization import create_organization
from data.model.team import (
    __get_user_admin_teams,
    add_or_invite_to_team,
    add_user_to_team,
    confirm_team_invite,
    create_team,
    delete_all_team_members,
    get_federated_user_teams,
    get_oidc_team_from_groupname,
    list_team_users,
    remove_team,
    remove_user_from_team,
    set_team_syncing,
    user_exists_in_team,
    validate_team_name,
)
from data.model.user import create_user_noverify, get_user
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


def test_delete_all_team_members(initialized_db):
    dev_user = get_user("devtable")
    random_user = get_user("randomuser")
    public_user = get_user("public")
    fresh_user = get_user("freshuser")
    reader_user = get_user("reader")

    new_org = create_organization("testorg", "testorg" + "@example.com", dev_user)

    team_1 = create_team("team_1", new_org, "member")
    assert add_user_to_team(dev_user, team_1)
    assert add_user_to_team(random_user, team_1)
    assert add_user_to_team(public_user, team_1)
    assert add_user_to_team(fresh_user, team_1)
    assert add_user_to_team(reader_user, team_1)

    before_deletion_count = TeamMember.select().where(TeamMember.team == team_1).count()
    assert before_deletion_count == 5
    delete_all_team_members(team_1)

    after_deletion_count = TeamMember.select().where(TeamMember.team == team_1).count()
    assert after_deletion_count == 0


@pytest.mark.parametrize("login_service_name", ["oidc", "ldap"])
def test_get_federated_user_teams(login_service_name, initialized_db):
    dev_user = get_user("devtable")
    new_org = create_organization("testorg", "testorg" + "@example.com", dev_user)

    team_1 = create_team("team_1", new_org, "member")
    assert add_user_to_team(dev_user, team_1)
    assert set_team_syncing(team_1, "oidc", None)

    team_2 = create_team("team_2", new_org, "member")
    assert add_user_to_team(dev_user, team_2)
    assert set_team_syncing(team_2, "oidc", None)

    team_3 = create_team("team_3", new_org, "member")
    assert add_user_to_team(dev_user, team_3)
    assert set_team_syncing(team_3, "ldap", None)

    user_teams = get_federated_user_teams(dev_user, login_service_name)
    if login_service_name == "oidc":
        assert len(user_teams) == 2
    elif login_service_name == "ldap":
        assert len(user_teams) == 1


def test_user_exists_in_team(initialized_db):
    dev_user = get_user("devtable")
    new_org = create_organization("testorg", "testorg" + "@example.com", dev_user)

    team_1 = create_team("team_1", new_org, "member")
    assert add_user_to_team(dev_user, team_1)
    assert user_exists_in_team(dev_user, team_1) is True

    # add user to team already part of
    with pytest.raises(UserAlreadyInTeam):
        add_user_to_team(dev_user, team_1)

    team_2 = create_team("team_2", new_org, "member")
    assert user_exists_in_team(dev_user, team_2) is False


def test_get_oidc_team_from_groupname(initialized_db):
    dev_user = get_user("devtable")
    new_org = create_organization("testorg", "testorg" + "@example.com", dev_user)

    team_1 = create_team("team_1", new_org, "member")
    assert add_user_to_team(dev_user, team_1)
    assert set_team_syncing(team_1, "oidc", {"group_name": "grp1"})
    response = get_oidc_team_from_groupname(group_name="grp1", login_service_name="oidc")
    assert len(response) == 1
    assert response[0].team.name == "team_1"
    assert json.loads(response[0].config).get("group_name") == "grp1"

    response = get_oidc_team_from_groupname(group_name="team_1", login_service_name="ldap")
    assert len(response) == 0

    response = get_oidc_team_from_groupname(group_name="team_1", login_service_name="ldap")
    assert len(response) == 0
