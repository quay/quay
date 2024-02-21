import json
import logging

from data.model import InvalidTeamException, UserAlreadyInTeam, team
from data.users.federated import FederatedUsers

logger = logging.getLogger(__name__)


class OIDCUsers(FederatedUsers):
    def __init__(
        self,
        client_id,
        client_secret,
        oidc_server,
        service_name,
        login_scopes,
        preferred_group_claim_name,
        requires_email=True,
    ):
        super(OIDCUsers, self).__init__("oidc", requires_email)
        self._client_id = client_id
        self._client_secret = client_secret
        self._oidc_server = oidc_server
        self._service_name = service_name
        self._login_scopes = login_scopes
        self._preferred_group_claim_name = preferred_group_claim_name
        self._requires_email = requires_email

    def is_superuser(self, username: str):
        """
        Initiated from FederatedUserManager.is_superuser(), falls back to ConfigUserManager.is_superuser()
        """
        return None

    def verify_credentials(self, username_or_email, password):
        """
        Verify the credentials with OIDC: To Implement
        """
        pass

    def check_group_lookup_args(self, group_lookup_args, disable_pagination=False):
        """
        No way to verify if the group is valid, so assuming the group is valid
        """
        return (True, None)

    def get_user(self, username_or_email):
        """
        No way to look up a username or email in OIDC so returning None
        """
        return (None, "Currently user lookup is not supported with OIDC")

    def query_users(self, query, limit):
        """
        No way to query users so returning empty list
        """
        return ([], self.federated_service, None)

    def fetch_org_team_from_oidc_group(self, oidc_group):
        """
        OIDC group name is in the format - <org_name>:<group_name>
        Extract and return org name and group name
        """
        try:
            org_name, group_name = oidc_group.split(":")
            # TODO: verify that org_name and group_name exist here
            return org_name, group_name
        except (ValueError, AttributeError):
            logger.exception(
                f'Incorrect OIDC group name: {oidc_group}. The expected format is : "<org_name>:<team_name> "'
            )

        return None, None

    def sync_oidc_groups(self, user_groups, user_obj, service_name):
        """
        Adds user to quay teams that have team sync enabled with an OIDC group
        """
        for oidc_group in user_groups:
            org_name, group_name = self.fetch_org_team_from_oidc_group(oidc_group)
            if not org_name or not group_name:
                continue

            # verify if team is in TeamSync table
            team_synced = team.get_team_sync_information(org_name, group_name)
            if not team_synced:
                logger.debug(f"OIDC group: {oidc_group} is not synced with a team in quay")
                continue

            # verify if team is synced with login service
            if team_synced.service.name != service_name:
                logger.debug(
                    f"OIDC group: {oidc_group} is not synced with the {service_name} service"
                )
                continue

            # add user to team
            try:
                team_obj = team.get_organization_team(org_name, group_name)
                team.add_user_to_team(user_obj, team_obj)
            except InvalidTeamException as err:
                logger.exception(err)
            except UserAlreadyInTeam:
                # Ignore
                pass
        return

    def resync_quay_teams(self, user_groups, user_obj, login_service_name):
        """
        Fetch quay teams that user is a member of.
        Remove user from teams that are synced with an OIDC group but group does not exist in "user_groups"
        """
        # fetch user's quay teams that have team sync enabled
        existing_user_teams = team.get_federated_user_teams(user_obj, login_service_name)
        user_groups = user_groups or []

        for user_team in existing_user_teams:
            try:
                sync_group_info = json.loads(user_team.teamsync.config)
                # remove user's membership from teams that were not returned from users OIDC groups
                if (
                    sync_group_info.get("group_name", None)
                    and sync_group_info["group_name"] not in user_groups
                ):
                    org_name, group_name = self.fetch_org_team_from_oidc_group(
                        sync_group_info["group_name"]
                    )
                    team.remove_user_from_team(org_name, user_team.name, user_obj.username, None)
                    logger.debug(
                        f"Successfully removed user: {user_obj.username} from team: {user_team.name} in organization: {org_name}"
                    )
            except Exception as err:
                logger.exception(err)
        return

    def sync_user_groups(self, user_groups, user_obj, login_service):
        if not user_obj:
            return

        service_name = login_service.service_id()
        self.sync_oidc_groups(user_groups, user_obj, service_name)
        self.resync_quay_teams(user_groups, user_obj, service_name)
        return
