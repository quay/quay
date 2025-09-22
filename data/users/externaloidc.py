import json
import logging
from urllib.parse import urlparse

import app
from data.model import InvalidTeamException, UserAlreadyInTeam, team
from data.users.federated import FederatedUsers, UserInformation
from oauth.login_utils import get_username_from_userinfo
from oauth.oidc import OIDCLoginService

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

    def service_metadata(self):
        for service in app.oauth_login.services:
            if isinstance(service, OIDCLoginService):
                return {"issuer_domain": urlparse(service.get_issuer()).netloc}
        return {}

    def is_superuser(self, username: str):
        """
        Initiated from FederatedUserManager.is_superuser(), falls back to ConfigUserManager.is_superuser()
        """
        return None

    def is_global_readonly_superuser(self, username: str):
        """
        Initiated from FederatedUserManager.is_global_readonly_superuser(), falls back to ConfigUserManager.is_global_readonly_superuser()
        """
        return None

    def is_restricted_user(self, username):
        """
        Checks whether the currently logged in user is restricted.
        """
        return None

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Used by teamSync worker, unsupported for oidc team sync
        """
        return (None, "Not supported")

    def verify_credentials(self, username_or_email, password):
        """
        Intelligent OIDC authentication that chooses the appropriate flow.

        For CLI clients (like Docker): Uses device code flow for broader account support
        For compatible accounts: Falls back to ROPC flow when device code isn't available
        """
        if not password:
            return (None, "Anonymous binding not allowed.")

        if not username_or_email:
            return (None, "Missing username or email.")

        for service in app.oauth_login.services:
            if isinstance(service, OIDCLoginService):

                # Step 1: Check if device code flow should be used
                if self._should_use_device_code_flow(username_or_email, password):
                    logger.info(f"Device code flow recommended for {username_or_email}")
                    # For Docker CLI, return immediate guidance instead of blocking
                    return (None, self._get_device_code_instructions(username_or_email))

                # Step 2: Fallback to ROPC flow for compatible accounts
                try:
                    logger.debug("Attempting ROPC flow for OIDC authentication")
                    response = service.password_grant_for_login(username_or_email, password)

                    if response is None:
                        return (None, "OIDC authentication failed: No response from provider")

                    user_info = service.get_user_info(
                        service._http_client, response["access_token"]
                    )

                    return (
                        UserInformation(
                            username=get_username_from_userinfo(user_info, service.config),
                            email=user_info.get("email"),
                            id=user_info.get("sub"),
                        ),
                        None,
                    )
                except Exception as err:
                    logger.exception(f"OIDC authentication failed: {err}")

                    # Provide specific guidance for known ROPC limitations
                    if self._is_ropc_limitation_error(err):
                        return (None, self._get_ropc_error_message(username_or_email))

                    return (None, f"OIDC authentication failed: {str(err)}")

        return (None, "No OIDC service configured")

    def _should_use_device_code_flow(self, username_or_email, password):
        """
        Determine if device code flow should be used instead of ROPC.

        Device code flow is preferred for:
        - Personal Microsoft accounts (@gmail.com, @outlook.com, etc.)
        - When explicitly requested via special password format
        - CLI clients (detected via user agent or other indicators)
        - Any Azure AD tenant (since ROPC often fails due to policies)
        """
        # Check for personal Microsoft account domains
        personal_domains = [
            "@gmail.com",
            "@googlemail.com",
            "@yahoo.com",
            "@outlook.com",
            "@hotmail.com",
            "@live.com",
            "@msn.com",
        ]

        if any(username_or_email.lower().endswith(domain) for domain in personal_domains):
            logger.info(f"Detected personal account: {username_or_email}, using device code flow")
            return True

        # Check for device code flow request indicator
        if password == "DEVICE_CODE_FLOW":
            logger.info("Device code flow explicitly requested")
            return True

        # Check for CLI user agent (if available in context)
        try:
            from flask import request

            if hasattr(request, "user_agent") and request.user_agent:
                user_agent = request.user_agent.string.lower()
                cli_indicators = ["docker", "curl", "wget", "python-requests", "go-http-client"]
                if any(indicator in user_agent for indicator in cli_indicators):
                    logger.info(
                        f"Detected CLI user agent: {user_agent}, preferring device code flow"
                    )
                    return True
        except:
            # Request context not available, ignore
            pass

        # For Azure AD, always prefer device code flow for Docker/CLI clients
        # This helps avoid ROPC limitations and policy restrictions
        try:
            from flask import request

            if hasattr(request, "user_agent") and request.user_agent:
                user_agent = request.user_agent.string.lower()
                if "docker" in user_agent:
                    logger.info(
                        f"Docker client detected for Azure AD account, using device code flow"
                    )
                    return True
        except:
            pass

        return False

    def _get_device_code_instructions(self, username_or_email):
        """
        Provide immediate instructions for device code flow authentication.
        This is Docker CLI friendly - provides guidance without blocking.
        """
        return (
            f"Authentication required for {username_or_email}. "
            f"This account requires browser-based authentication. "
            f"For CLI authentication, use the device code flow endpoint "
            f"to get a Docker token."
        )

    def _is_ropc_limitation_error(self, error):
        """
        Check if the error is due to ROPC flow limitations.
        """
        error_str = str(error).lower()
        ropc_error_indicators = [
            "aadsts700056",  # User account does not exist in organization
            "aadsts50126",  # Invalid username or password
            "aadsts50034",  # User account not found
            "user account does not exist",
            "invalid username or password",
            "ropc is not supported",
            "resource owner password credentials",
        ]

        return any(indicator in error_str for indicator in ropc_error_indicators)

    def _get_ropc_error_message(self, username_or_email):
        """
        Provide helpful error message for ROPC limitations.
        """
        return (
            f"Authentication failed for {username_or_email}. "
            f"This account requires browser-based authentication. "
            f"For CLI authentication, use the device code flow endpoint "
            f"to get a Docker token."
        )

    def check_group_lookup_args(self, group_lookup_args, disable_pagination=False):
        """
        No way to verify if the group is valid, so assuming the group is valid
        """
        return (True, None)  # type: ignore

    def get_user(self, username_or_email):
        """
        No way to look up a username or email in OIDC so returning None
        """
        return (None, "Currently user lookup is not supported with OIDC")

    def query_users(self, query, limit=20):
        """
        No way to query users so returning empty list
        """
        return ([], self._federated_service, "Not supported")  # type: ignore

    def sync_oidc_groups(self, user_groups, user_obj):
        """
        Adds user to quay teams that have team sync enabled with an OIDC group
        """
        if user_groups is None:
            logger.debug(
                f"External OIDC Group Sync: Found no oidc groups for user: {user_obj.username}"
            )
            return

        for oidc_group in user_groups:
            # fetch TeamSync row if exists, for the oidc_group synced with the login service
            synced_teams = team.get_oidc_team_from_groupname(oidc_group, self._federated_service)
            if len(synced_teams) == 0:
                logger.debug(
                    f"External OIDC Group Sync: OIDC group: {oidc_group} is either not synced with a team in quay or is not synced with the {self._federated_service} service"
                )
                continue

            # fetch team name and organization name for the Teamsync row
            for team_synced in synced_teams:
                team_name = team_synced.team.name
                org_name = team_synced.team.organization.username
                if not team_name or not org_name:
                    logger.debug(
                        f"External OIDC Group Sync: Cannot retrieve quay team synced with the oidc group: {oidc_group}"
                    )

                # add user to team
                try:
                    team.add_user_to_team(user_obj, team_synced.team)
                except InvalidTeamException as err:
                    logger.exception(
                        f"External OIDC Group Sync: Exception occurred when adding user: {user_obj.username} to quay team: {team_synced.team} as {err}"
                    )
                except UserAlreadyInTeam:
                    # Ignore
                    pass
        return

    def ping(self):
        """
        TODO: get the OIDC connection here
        """
        return (True, None)

    def resync_quay_teams(self, user_groups, user_obj):
        """
        Fetch quay teams that user is a member of.
        Remove user from teams that are synced with an OIDC group but group does not exist in "user_groups"
        """
        # fetch user's quay teams that have team sync enabled
        existing_user_teams = team.get_federated_user_teams(user_obj, self._federated_service)
        logger.debug(
            f"External OIDC Group Sync: For user {user_obj.username} re-syncing {len(existing_user_teams)} quay teams"
        )
        user_groups = user_groups or []
        for user_team in existing_user_teams:
            try:
                sync_group_info = json.loads(user_team.teamsync.config)
                # remove user's membership from teams that were not returned from users OIDC groups
                if (
                    sync_group_info.get("group_name", None)
                    and sync_group_info["group_name"] not in user_groups
                ):
                    org_name = user_team.teamsync.team.organization.username
                    team.remove_user_from_team(org_name, user_team.name, user_obj.username, None)
                    logger.debug(
                        f"External OIDC Group Sync: Successfully removed user: {user_obj.username} from team: {user_team.name} in organization: {org_name}"
                    )
            except Exception as err:
                logger.exception(
                    f"External OIDC Group Sync: Exception occurred for user {user_obj.username} when removing membership from quay team: {user_team.name} as {err}"
                )
        return

    def sync_user_groups(self, user_groups, user_obj, login_service):
        if not user_obj:
            return

        self.sync_oidc_groups(user_groups, user_obj)
        self.resync_quay_teams(user_groups, user_obj)
        return
