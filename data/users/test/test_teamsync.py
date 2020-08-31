import os

from datetime import datetime, timedelta

import pytest

from mock import patch

from data import model, database
from data.users.federated import FederatedUsers, UserInformation
from data.users.teamsync import sync_team, sync_teams_to_groups
from test.test_ldap import mock_ldap
from test.test_keystone_auth import fake_keystone
from util.names import parse_robot_username

from test.fixtures import *

_FAKE_AUTH = "fake"


class FakeUsers(FederatedUsers):
    def __init__(self, group_members):
        super(FakeUsers, self).__init__(_FAKE_AUTH, False)
        self.group_tuples = [(m, None) for m in group_members]

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        return (self.group_tuples, None)


@pytest.fixture(params=[True, False])
def user_creation(request):
    with patch("features.USER_CREATION", request.param):
        yield


@pytest.fixture(params=[True, False])
def invite_only_user_creation(request):
    with patch("features.INVITE_ONLY_USER_CREATION", request.param):
        yield


@pytest.fixture(params=[True, False])
def blacklisted_emails(request):
    mock_blacklisted_domains = {"BLACKLISTED_EMAIL_DOMAINS": ["blacklisted.com", "blacklisted.net"]}
    with patch("features.BLACKLISTED_EMAILS", request.param):
        with patch.dict("data.model.config.app_config", mock_blacklisted_domains):
            yield


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("postgres") >= 0,
    reason="Postgres fails when existing members are added under the savepoint",
)
@pytest.mark.parametrize(
    "starting_membership,group_membership,expected_membership",
    [
        # Empty team + single member in group => Single member in team.
        (
            [],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["someuser"],
        ),
        # Team with a Quay user + empty group => empty team.
        ([("someuser", None)], [], []),
        # Team with an existing external user + user is in the group => no changes.
        (
            [
                ("someuser", "someuser"),
            ],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["someuser"],
        ),
        # Team with an existing external user (with a different Quay username) + user is in the group.
        # => no changes
        (
            [
                ("anotherquayname", "someuser"),
            ],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["someuser"],
        ),
        # Team missing a few members that are in the group => members added.
        (
            [("someuser", "someuser")],
            [
                UserInformation("anotheruser", "anotheruser", "anotheruser@devtable.com"),
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
                UserInformation("thirduser", "thirduser", "thirduser@devtable.com"),
            ],
            ["anotheruser", "someuser", "thirduser"],
        ),
        # Team has a few extra members no longer in the group => members removed.
        (
            [
                ("anotheruser", "anotheruser"),
                ("someuser", "someuser"),
                ("thirduser", "thirduser"),
                ("nontestuser", None),
            ],
            [
                UserInformation("thirduser", "thirduser", "thirduser@devtable.com"),
            ],
            ["thirduser"],
        ),
        # Team has different membership than the group => members added and removed.
        (
            [
                ("anotheruser", "anotheruser"),
                ("someuser", "someuser"),
                ("nontestuser", None),
            ],
            [
                UserInformation("anotheruser", "anotheruser", "anotheruser@devtable.com"),
                UserInformation("missinguser", "missinguser", "missinguser@devtable.com"),
            ],
            ["anotheruser", "missinguser"],
        ),
        # Team has same membership but some robots => robots remain and no other changes.
        (
            [
                ("someuser", "someuser"),
                ("buynlarge+anotherbot", None),
                ("buynlarge+somerobot", None),
            ],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["someuser", "buynlarge+somerobot", "buynlarge+anotherbot"],
        ),
        # Team has an extra member and some robots => member removed and robots remain.
        (
            [
                ("someuser", "someuser"),
                ("buynlarge+anotherbot", None),
                ("buynlarge+somerobot", None),
            ],
            [
                # No members.
            ],
            ["buynlarge+somerobot", "buynlarge+anotherbot"],
        ),
        # Team has a different member and some robots => member changed and robots remain.
        (
            [
                ("someuser", "someuser"),
                ("buynlarge+anotherbot", None),
                ("buynlarge+somerobot", None),
            ],
            [
                UserInformation("anotheruser", "anotheruser", "anotheruser@devtable.com"),
            ],
            ["anotheruser", "buynlarge+somerobot", "buynlarge+anotherbot"],
        ),
        # Team with an existing external user (with a different Quay username) + user is in the group.
        # => no changes and robots remain.
        (
            [
                ("anotherquayname", "someuser"),
                ("buynlarge+anotherbot", None),
            ],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["someuser", "buynlarge+anotherbot"],
        ),
        # Team which returns the same member twice, as pagination in some engines (like LDAP) is not
        # stable.
        (
            [],
            [
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
                UserInformation("anotheruser", "anotheruser", "anotheruser@devtable.com"),
                UserInformation("someuser", "someuser", "someuser@devtable.com"),
            ],
            ["anotheruser", "someuser"],
        ),
    ],
)
def test_syncing(
    user_creation,
    invite_only_user_creation,
    starting_membership,
    group_membership,
    expected_membership,
    blacklisted_emails,
    app,
):
    org = model.organization.get_organization("buynlarge")

    # Necessary for the fake auth entries to be created in FederatedLogin.
    database.LoginService.create(name=_FAKE_AUTH)

    # Assert the team is empty, so we have a clean slate.
    sync_team_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert len(list(model.team.list_team_users(sync_team_info.team))) == 0

    # Add the existing starting members to the team.
    for starting_member in starting_membership:
        (quay_username, fakeauth_username) = starting_member
        if "+" in quay_username:
            # Add a robot.
            (_, shortname) = parse_robot_username(quay_username)
            robot, _ = model.user.create_robot(shortname, org)
            model.team.add_user_to_team(robot, sync_team_info.team)
        else:
            email = quay_username + "@devtable.com"

            if fakeauth_username is None:
                quay_user = model.user.create_user_noverify(quay_username, email)
            else:
                quay_user = model.user.create_federated_user(
                    quay_username, email, _FAKE_AUTH, fakeauth_username, False
                )

            model.team.add_user_to_team(quay_user, sync_team_info.team)

    # Call syncing on the team.
    fake_auth = FakeUsers(group_membership)
    assert sync_team(fake_auth, sync_team_info)

    # Ensure the last updated time and transaction_id's have changed.
    updated_sync_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert updated_sync_info.last_updated is not None
    assert updated_sync_info.transaction_id != sync_team_info.transaction_id

    users_expected = set([name for name in expected_membership if "+" not in name])
    robots_expected = set([name for name in expected_membership if "+" in name])
    assert len(users_expected) + len(robots_expected) == len(expected_membership)

    # Check that the team's users match those expected.
    service_user_map = model.team.get_federated_team_member_mapping(sync_team_info.team, _FAKE_AUTH)
    assert set(service_user_map.keys()) == users_expected

    quay_users = model.team.list_team_users(sync_team_info.team)
    assert len(quay_users) == len(users_expected)

    for quay_user in quay_users:
        fakeauth_record = model.user.lookup_federated_login(quay_user, _FAKE_AUTH)
        assert fakeauth_record is not None
        assert fakeauth_record.service_ident in users_expected
        assert service_user_map[fakeauth_record.service_ident] == quay_user.id

    # Check that the team's robots match those expected.
    robots_found = set([r.username for r in model.team.list_team_robots(sync_team_info.team)])
    assert robots_expected == robots_found


def test_sync_teams_to_groups(user_creation, invite_only_user_creation, blacklisted_emails, app):
    # Necessary for the fake auth entries to be created in FederatedLogin.
    database.LoginService.create(name=_FAKE_AUTH)

    # Assert the team has not yet been updated.
    sync_team_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert sync_team_info.last_updated is None

    # Call to sync all teams.
    fake_auth = FakeUsers([])
    sync_teams_to_groups(fake_auth, timedelta(seconds=1))

    # Ensure the team was synced.
    updated_sync_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert updated_sync_info.last_updated is not None
    assert updated_sync_info.transaction_id != sync_team_info.transaction_id

    # Set the stale threshold to a high amount and ensure the team is not resynced.
    current_info = model.team.get_team_sync_information("buynlarge", "synced")
    current_info.last_updated = datetime.now() - timedelta(seconds=2)
    current_info.save()

    sync_teams_to_groups(fake_auth, timedelta(seconds=120))

    third_sync_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert third_sync_info.transaction_id == updated_sync_info.transaction_id

    # Set the stale threshold to 10 seconds, and ensure the team is resynced, after making it
    # "updated" 20s ago.
    current_info = model.team.get_team_sync_information("buynlarge", "synced")
    current_info.last_updated = datetime.now() - timedelta(seconds=20)
    current_info.save()

    sync_teams_to_groups(fake_auth, timedelta(seconds=10))

    fourth_sync_info = model.team.get_team_sync_information("buynlarge", "synced")
    assert fourth_sync_info.transaction_id != updated_sync_info.transaction_id


@pytest.mark.parametrize(
    "auth_system_builder,config",
    [
        (mock_ldap, {"group_dn": "cn=AwesomeFolk"}),
        (fake_keystone, {"group_id": "somegroupid"}),
    ],
)
def test_teamsync_end_to_end(
    user_creation, invite_only_user_creation, auth_system_builder, config, blacklisted_emails, app
):
    with auth_system_builder() as auth:
        # Create an new team to sync.
        org = model.organization.get_organization("buynlarge")
        new_synced_team = model.team.create_team("synced2", org, "member", "Some synced team.")
        sync_team_info = model.team.set_team_syncing(
            new_synced_team, auth.federated_service, config
        )

        # Sync the team.
        assert sync_team(auth, sync_team_info)

        # Ensure we now have members.
        msg = "Auth system: %s" % auth.federated_service
        sync_team_info = model.team.get_team_sync_information("buynlarge", "synced2")
        team_members = list(model.team.list_team_users(sync_team_info.team))
        assert len(team_members) > 1, msg

        it, _ = auth.iterate_group_members(config)
        assert len(team_members) == len(list(it)), msg

        sync_team_info.last_updated = datetime.now() - timedelta(hours=6)
        sync_team_info.save()

        # Remove one of the members and force a sync again to ensure we re-link the correct users.
        first_member = team_members[0]
        model.team.remove_user_from_team("buynlarge", "synced2", first_member.username, "devtable")

        team_members2 = list(model.team.list_team_users(sync_team_info.team))
        assert len(team_members2) == 1, msg
        assert sync_team(auth, sync_team_info)

        team_members3 = list(model.team.list_team_users(sync_team_info.team))
        assert len(team_members3) > 1, msg
        assert set([m.id for m in team_members]) == set([m.id for m in team_members3])


@pytest.mark.parametrize(
    "auth_system_builder,config",
    [
        (mock_ldap, {"group_dn": "cn=AwesomeFolk"}),
        (fake_keystone, {"group_id": "somegroupid"}),
    ],
)
def test_teamsync_existing_email(
    user_creation, invite_only_user_creation, auth_system_builder, blacklisted_emails, config, app
):
    with auth_system_builder() as auth:
        # Create an new team to sync.
        org = model.organization.get_organization("buynlarge")
        new_synced_team = model.team.create_team("synced2", org, "member", "Some synced team.")
        sync_team_info = model.team.set_team_syncing(
            new_synced_team, auth.federated_service, config
        )

        # Add a new *unlinked* user with the same email address as one of the team members.
        it, _ = auth.iterate_group_members(config)
        members = list(it)
        model.user.create_user_noverify("someusername", members[0][0].email)

        # Sync the team and ensure it doesn't fail.
        assert sync_team(auth, sync_team_info)

        team_members = list(model.team.list_team_users(sync_team_info.team))
        assert len(team_members) > 0
