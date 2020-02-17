import json

from mock import patch

from data import model
from endpoints.api import api
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.team import OrganizationTeamSyncing, TeamMemberList
from endpoints.api.organization import Organization
from endpoints.test.shared import client_with_identity

from test.test_ldap import mock_ldap

from test.fixtures import *

SYNCED_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "synced"}
UNSYNCED_TEAM_PARAMS = {"orgname": "sellnsmall", "teamname": "owners"}


def test_team_syncing(client):
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            with client_with_identity("devtable", client) as cl:
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


def test_team_member_sync_info(client):
    with mock_ldap() as ldap:
        with patch("endpoints.api.team.authentication", ldap):
            # Check for an unsynced team, with superuser.
            with client_with_identity("devtable", client) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", UNSYNCED_TEAM_PARAMS)
                assert "can_sync" in resp.json
                assert resp.json["can_sync"]["service"] == "ldap"

                assert "synced" not in resp.json

            # Check for an unsynced team, with non-superuser.
            with client_with_identity("randomuser", client) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", UNSYNCED_TEAM_PARAMS)
                assert "can_sync" not in resp.json
                assert "synced" not in resp.json

            # Check for a synced team, with superuser.
            with client_with_identity("devtable", client) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", SYNCED_TEAM_PARAMS)
                assert "can_sync" in resp.json
                assert resp.json["can_sync"]["service"] == "ldap"

                assert "synced" in resp.json
                assert "last_updated" in resp.json["synced"]
                assert "group_dn" in resp.json["synced"]["config"]

            # Check for a synced team, with non-superuser.
            with client_with_identity("randomuser", client) as cl:
                resp = conduct_api_call(cl, TeamMemberList, "GET", SYNCED_TEAM_PARAMS)
                assert "can_sync" not in resp.json

                assert "synced" in resp.json
                assert "last_updated" not in resp.json["synced"]
                assert "config" not in resp.json["synced"]


def test_organization_teams_sync_bool(client):
    with mock_ldap() as ldap:
        with patch("endpoints.api.organization.authentication", ldap):
            # Ensure synced teams are marked as such in the organization teams list.
            with client_with_identity("devtable", client) as cl:
                resp = conduct_api_call(cl, Organization, "GET", {"orgname": "sellnsmall"})

                assert not resp.json["teams"]["owners"]["is_synced"]

                assert resp.json["teams"]["synced"]["is_synced"]
