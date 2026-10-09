import json

from mock import Mock, patch

from app import app as quay_app
from data import model
from endpoints.api import api
from endpoints.api.organization import Organization
from endpoints.api.team import OrganizationTeam, OrganizationTeamSyncing, TeamMemberList
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *
from test.test_ldap import mock_ldap

SYNCED_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "synced"}
UNSYNCED_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "owners"}
NEW_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "apisyncteam"}
NEW_TEAM_OIDC_PARAMS = {"orgname": "sellnsmall", "teamname": "oidcsyncteam"}
NEW_TEAM_KEYSTONE_PARAMS = {"orgname": "sellnsmall", "teamname": "keystonesyncteam"}
KEYSTONE_SYNCING_PARAMS = {"orgname": "sellnsmall", "teamname": "keystonesyncing"}
UPDATE_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "updatesyncteam"}
FAILED_LOOKUP_CREATE_PARAMS = {"orgname": "sellnsmall", "teamname": "failedsyncteam"}


def _fake_auth(service_name):
    """Return a mock federated auth backend for the given service name."""
    auth = Mock()
    auth.federated_service = service_name
    auth.check_group_lookup_args.return_value = (True, None)
    auth.service_metadata.return_value = {}
    return auth


def test_team_syncing(app):
    """Enable and disable team syncing via the dedicated /syncing endpoint."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                config = {
                    "group_dn": "cn=AwesomeFolk",
                }

                conduct_api_call(cl, OrganizationTeamSyncing, "POST", UNSYNCED_TEAM_PARAMS, config)

                # Ensure the team is now synced.
                sync_info = model.team.get_team_sync_information(
                    UNSYNCED_TEAM_PARAMS["orgname"], UNSYNCED_TEAM_PARAMS["teamname"]
                )
                assert sync_info is not None
                assert json.loads(sync_info.config) == config

                # Remove the syncing.
                conduct_api_call(cl, OrganizationTeamSyncing, "DELETE", UNSYNCED_TEAM_PARAMS, None)

                # Ensure the team is no longer synced.
                sync_info = model.team.get_team_sync_information(
                    UNSYNCED_TEAM_PARAMS["orgname"], UNSYNCED_TEAM_PARAMS["teamname"]
                )
                assert sync_info is None


def test_create_team_with_group_dn_enables_sync(app):
    """Creating a team with group_dn enables LDAP directory sync."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "description": "created with sync",
                    "group_dn": "cn=AwesomeFolk",
                }
                conduct_api_call(cl, OrganizationTeam, "PUT", NEW_TEAM_PARAMS, body)

                sync_info = model.team.get_team_sync_information(
                    NEW_TEAM_PARAMS["orgname"], NEW_TEAM_PARAMS["teamname"]
                )
                assert sync_info is not None
                assert json.loads(sync_info.config) == {"group_dn": "cn=AwesomeFolk"}


def test_update_team_with_group_dn_enables_sync(app):
    """Updating a team with group_dn enables LDAP directory sync."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                # Create a non-owners team first — updating "owners" to role=member
                # is rejected because it would remove the caller's org admin.
                conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "PUT",
                    UPDATE_TEAM_PARAMS,
                    {"role": "member", "description": "to be synced"},
                )

                body = {
                    "role": "member",
                    "group_dn": "cn=AwesomeFolk",
                }
                conduct_api_call(cl, OrganizationTeam, "PUT", UPDATE_TEAM_PARAMS, body)

                sync_info = model.team.get_team_sync_information(
                    UPDATE_TEAM_PARAMS["orgname"], UPDATE_TEAM_PARAMS["teamname"]
                )
                assert sync_info is not None
                assert json.loads(sync_info.config) == {"group_dn": "cn=AwesomeFolk"}


def test_create_team_with_group_name_enables_sync(app):
    """Creating a team with group_name enables OIDC directory sync."""
    oidc_auth = _fake_auth("oidc")
    with patch("endpoints.api.team.authentication", oidc_auth):
        with patch.dict(quay_app.config, {"AUTHENTICATION_TYPE": "OIDC"}):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "description": "oidc synced",
                    "group_name": "external-object-id",
                }
                conduct_api_call(cl, OrganizationTeam, "PUT", NEW_TEAM_OIDC_PARAMS, body)

                sync_info = model.team.get_team_sync_information(
                    NEW_TEAM_OIDC_PARAMS["orgname"], NEW_TEAM_OIDC_PARAMS["teamname"]
                )
                assert sync_info is not None
                assert json.loads(sync_info.config) == {"group_name": "external-object-id"}
                oidc_auth.check_group_lookup_args.assert_called_once_with(
                    {"group_name": "external-object-id"}
                )


def test_create_team_with_group_id_enables_sync(app):
    """Creating a team with group_id enables Keystone directory sync."""
    keystone_auth = _fake_auth("keystone")
    with patch("endpoints.api.team.authentication", keystone_auth):
        with client_with_identity("devtable", app) as cl:
            body = {
                "role": "member",
                "description": "keystone synced",
                "group_id": "keystone-group-123",
            }
            conduct_api_call(cl, OrganizationTeam, "PUT", NEW_TEAM_KEYSTONE_PARAMS, body)

            sync_info = model.team.get_team_sync_information(
                NEW_TEAM_KEYSTONE_PARAMS["orgname"], NEW_TEAM_KEYSTONE_PARAMS["teamname"]
            )
            assert sync_info is not None
            assert json.loads(sync_info.config) == {"group_id": "keystone-group-123"}
            keystone_auth.check_group_lookup_args.assert_called_once_with(
                {"group_id": "keystone-group-123"}
            )


def test_enable_team_syncing_endpoint_with_group_id(app):
    """Cover POST .../syncing with Keystone group_id (Playwright has no Keystone auth env)."""
    keystone_auth = _fake_auth("keystone")
    with patch("endpoints.api.team.authentication", keystone_auth):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrganizationTeam,
                "PUT",
                KEYSTONE_SYNCING_PARAMS,
                {"role": "member", "description": "to sync via endpoint"},
            )

            config = {"group_id": "keystone-group-456"}
            conduct_api_call(cl, OrganizationTeamSyncing, "POST", KEYSTONE_SYNCING_PARAMS, config)

            sync_info = model.team.get_team_sync_information(
                KEYSTONE_SYNCING_PARAMS["orgname"], KEYSTONE_SYNCING_PARAMS["teamname"]
            )
            assert sync_info is not None
            assert json.loads(sync_info.config) == config
            keystone_auth.check_group_lookup_args.assert_called_with(config)


def test_oidc_sync_removes_existing_team_members(app):
    """Enabling OIDC sync clears existing team members before sync takes over."""
    oidc_auth = _fake_auth("oidc")
    org = model.organization.get_organization("sellnsmall")
    team = model.team.create_team("oidcmemberclear", org, "member", "has members")
    member = model.user.get_user("freshuser")
    model.team.add_user_to_team(member, team)
    assert len(list(model.team.list_team_users(team))) == 1

    with patch("endpoints.api.team.authentication", oidc_auth):
        with patch.dict(quay_app.config, {"AUTHENTICATION_TYPE": "OIDC"}):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "group_name": "oidc-group",
                }
                conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "PUT",
                    {"orgname": "sellnsmall", "teamname": "oidcmemberclear"},
                    body,
                )

    assert len(list(model.team.list_team_users(team))) == 0
    sync_info = model.team.get_team_sync_information("sellnsmall", "oidcmemberclear")
    assert sync_info is not None
    assert json.loads(sync_info.config) == {"group_name": "oidc-group"}


def test_create_team_rejects_multiple_sync_fields(app):
    """Reject team create when more than one sync identifier is provided."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "group_dn": "cn=AwesomeFolk",
                    "group_name": "some-oidc-group",
                }
                conduct_api_call(
                    cl, OrganizationTeam, "PUT", NEW_TEAM_PARAMS, body, expected_code=400
                )


def test_update_already_synced_team_rejects_new_group(app):
    """Reject attaching a new sync group when the team is already synced."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "group_dn": "cn=AwesomeFolk",
                }
                conduct_api_call(
                    cl, OrganizationTeam, "PUT", SYNCED_TEAM_PARAMS, body, expected_code=400
                )


def test_create_team_without_sync_fields_unchanged(app):
    """Creating a team without sync fields leaves syncing disabled."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "description": "no sync",
                }
                conduct_api_call(cl, OrganizationTeam, "PUT", NEW_TEAM_PARAMS, body)

                sync_info = model.team.get_team_sync_information(
                    NEW_TEAM_PARAMS["orgname"], NEW_TEAM_PARAMS["teamname"]
                )
                assert sync_info is None


def test_create_team_failed_group_lookup_does_not_create_team(app):
    """Failed group lookup during create must not persist a new team."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "description": "should not persist",
                    "group_dn": "cn=invalid",
                }
                conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "PUT",
                    FAILED_LOOKUP_CREATE_PARAMS,
                    body,
                    expected_code=400,
                )

                try:
                    model.team.get_organization_team(
                        FAILED_LOOKUP_CREATE_PARAMS["orgname"],
                        FAILED_LOOKUP_CREATE_PARAMS["teamname"],
                    )
                    assert False, "team should not have been created after failed group lookup"
                except model.InvalidTeamException:
                    pass


def test_update_team_failed_group_lookup_does_not_change_team(app):
    """Failed group lookup during update must not change the existing team."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            team = model.team.get_organization_team(
                UNSYNCED_TEAM_PARAMS["orgname"], UNSYNCED_TEAM_PARAMS["teamname"]
            )
            original_description = team.description

            with client_with_identity("devtable", app) as cl:
                body = {
                    "role": "member",
                    "description": "should-not-be-saved",
                    "group_dn": "cn=invalid",
                }
                conduct_api_call(
                    cl, OrganizationTeam, "PUT", UNSYNCED_TEAM_PARAMS, body, expected_code=400
                )

            team = model.team.get_organization_team(
                UNSYNCED_TEAM_PARAMS["orgname"], UNSYNCED_TEAM_PARAMS["teamname"]
            )
            assert team.description == original_description
            assert (
                model.team.get_team_sync_information(
                    UNSYNCED_TEAM_PARAMS["orgname"], UNSYNCED_TEAM_PARAMS["teamname"]
                )
                is None
            )


def test_team_member_sync_info_unsynced_superuser(app):
    """Superusers see can_sync for unsynced teams and no synced block."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            # Check for an unsynced team, with superuser.
            with client_with_identity("devtable", app) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", UNSYNCED_TEAM_PARAMS)
                assert "can_sync" in resp.json
                assert resp.json["can_sync"]["service"] == "ldap"
                assert "synced" not in resp.json


def test_team_member_sync_info_unsynced_nonsuperuser(app):
    """Non-superusers do not see can_sync for unsynced teams."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            # Check for an unsynced team, with non-superuser.
            with client_with_identity("randomuser", app) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", UNSYNCED_TEAM_PARAMS)
                assert "can_sync" not in resp.json
                assert "synced" not in resp.json


def test_team_member_sync_info_synced_superuser(app):
    """Superusers see full sync config details for synced teams."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            # Check for a synced team, with superuser.
            with client_with_identity("devtable", app) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", SYNCED_TEAM_PARAMS)
                assert "can_sync" in resp.json
                assert resp.json["can_sync"]["service"] == "ldap"

                assert "synced" in resp.json
                assert "last_updated" in resp.json["synced"]
                assert "group_dn" in resp.json["synced"]["config"]


def test_team_member_sync_info_synced_nonsuperuser(app):
    """Non-superusers see sync status without config details."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            # Check for a synced team, with non-superuser.
            with client_with_identity("randomuser", app) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", SYNCED_TEAM_PARAMS)
                assert "can_sync" not in resp.json

                assert "synced" in resp.json
                assert "last_updated" not in resp.json["synced"]
                assert "config" not in resp.json["synced"]


def test_organization_teams_sync_bool(app):
    """Organization team list marks synced teams with is_synced."""
    with mock_ldap() as ldap:
        with patch("endpoints.api.organization.authentication", ldap):
            # Ensure synced teams are marked as such in the organization teams list.
            with client_with_identity("devtable", app) as cl:
                resp = conduct_api_call(cl, Organization, "GET", {"orgname": "sellnsmall"})

                assert not resp.json["teams"]["owners"]["is_synced"]

                assert resp.json["teams"]["synced"]["is_synced"]
